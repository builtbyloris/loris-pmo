from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol, runtime_checkable

from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class StoredObject:
    size_bytes: int
    etag: str | None = None


@runtime_checkable
class DocumentStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> StoredObject: ...
    def open(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def metadata(self, key: str) -> StoredObject: ...


def _safe_key(key: str) -> str:
    path = PurePosixPath(key)
    if path.is_absolute() or not path.parts or ".." in path.parts or "." in path.parts:
        raise AppError(
            code="invalid_document_path", message="Invalid document path.", status_code=400
        )
    return path.as_posix()


class LocalDocumentStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / _safe_key(key)).resolve()
        if self.root not in path.parents:
            raise AppError(
                code="invalid_document_path", message="Invalid document path.", status_code=400
            )
        return path

    def put(self, key: str, data: bytes, content_type: str) -> StoredObject:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredObject(size_bytes=len(data))

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.is_file():
            raise AppError(
                code="document_file_missing",
                message="Document file is unavailable.",
                status_code=404,
            )
        return path.open("rb")

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def metadata(self, key: str) -> StoredObject:
        path = self._path(key)
        if not path.is_file():
            raise AppError(
                code="document_file_missing",
                message="Document file is unavailable.",
                status_code=404,
            )
        return StoredObject(size_bytes=path.stat().st_size)

    def path_for(self, key: str) -> Path:
        self.metadata(key)
        return self._path(key)


class S3DocumentStorage:
    def __init__(self, settings: Settings, client: object | None = None) -> None:
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required")
        self.bucket = settings.s3_bucket
        if client is not None:
            self.client = client
            return
        import boto3
        from botocore.config import Config

        options: dict[str, object] = {
            "service_name": "s3",
            "region_name": settings.s3_region,
            "endpoint_url": settings.s3_endpoint_url,
            "config": Config(
                connect_timeout=settings.s3_request_timeout_seconds,
                read_timeout=settings.s3_request_timeout_seconds,
                # One total attempt keeps storage operations deterministic: the
                # application does not hide provider failures behind retries.
                retries={"total_max_attempts": 1},
            ),
        }
        if settings.s3_access_key_id:
            options["aws_access_key_id"] = settings.s3_access_key_id
            options["aws_secret_access_key"] = settings.s3_secret_access_key
        self.client = boto3.client(**options)

    @staticmethod
    def _not_found(exc: Exception) -> bool:
        response = getattr(exc, "response", {})
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        metadata = response.get("ResponseMetadata", {}) if isinstance(response, dict) else {}
        return (
            error.get("Code") in {"404", "NoSuchKey", "NotFound"}
            or metadata.get("HTTPStatusCode") == 404
        )

    @staticmethod
    def _missing() -> AppError:
        return AppError(
            code="document_file_missing",
            message="Document file is unavailable.",
            status_code=404,
        )

    @staticmethod
    def _unavailable() -> AppError:
        return AppError(
            code="document_storage_unavailable",
            message="Document storage is temporarily unavailable.",
            status_code=503,
        )

    def put(self, key: str, data: bytes, content_type: str) -> StoredObject:
        safe_key = _safe_key(key)
        try:
            response = self.client.put_object(
                Bucket=self.bucket,
                Key=safe_key,
                Body=data,
                ContentType=content_type,
            )
        except Exception as exc:
            raise self._unavailable() from exc
        return StoredObject(size_bytes=len(data), etag=response.get("ETag"))

    def open(self, key: str) -> BinaryIO:
        safe_key = _safe_key(key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=safe_key)
            return response["Body"]
        except Exception as exc:
            if self._not_found(exc):
                raise self._missing() from exc
            raise self._unavailable() from exc

    def delete(self, key: str) -> None:
        safe_key = _safe_key(key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=safe_key)
        except Exception as exc:
            raise self._unavailable() from exc

    def exists(self, key: str) -> bool:
        safe_key = _safe_key(key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=safe_key)
            return True
        except Exception as exc:
            if self._not_found(exc):
                return False
            raise self._unavailable() from exc

    def metadata(self, key: str) -> StoredObject:
        safe_key = _safe_key(key)
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=safe_key)
        except Exception as exc:
            if self._not_found(exc):
                raise self._missing() from exc
            raise self._unavailable() from exc
        return StoredObject(
            size_bytes=int(response["ContentLength"]),
            etag=response.get("ETag"),
        )


def create_document_storage(settings: Settings) -> DocumentStorage:
    if settings.document_storage_backend == "s3":
        return S3DocumentStorage(settings)
    return LocalDocumentStorage(settings.document_storage_path)
