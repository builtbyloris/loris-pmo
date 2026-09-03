import io

import pytest
from cryptography.fernet import Fernet
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.database import database_engine_options
from app.core.errors import AppError
from app.storage import LocalDocumentStorage, S3DocumentStorage


def production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "database_url": "postgresql+asyncpg://app:r4nd0m-db-value@database.example/loris",
        "database_ssl_mode": "require",
        "secret_key": "a-production-value-with-more-than-forty-eight-random-characters-123",
        "frontend_url": "https://pmo.example.com",
        "cors_allowed_origins": "https://pmo.example.com",
        "trusted_hosts": "api.example.com",
        "document_storage_backend": "s3",
        "s3_bucket": "private-documents",
        "s3_region": "eu-west-1",
        "integration_token_encryption_key": Fernet.generate_key().decode(),
    }
    values.update(overrides)
    return Settings(**values)


def test_production_configuration_is_fail_closed() -> None:
    settings = production_settings()
    assert settings.secure_cookies is True
    assert settings.allowed_origins == ["https://pmo.example.com"]
    assert settings.allowed_hosts == ["api.example.com"]

    with pytest.raises(ValidationError) as error:
        production_settings(
            database_url="sqlite+aiosqlite://",
            database_ssl_mode="disable",
            frontend_url="http://pmo.example.com",
            cors_allowed_origins="*",
            trusted_hosts="*",
            secret_key="replace-with-a-secret-that-is-not-production-safe",
        )
    message = str(error.value)
    assert "PostgreSQL" in message
    assert "explicit HTTPS origins" in message
    assert "TRUSTED_HOSTS" in message
    assert "SECRET_KEY" in message

    with pytest.raises(ValidationError) as wildcard_error:
        production_settings(
            frontend_url="https:",
            cors_allowed_origins="https://*.example.com",
            trusted_hosts="*.example.com",
        )
    wildcard_message = str(wildcard_error.value)
    assert "FRONTEND_URL" in wildcard_message
    assert "CORS_ALLOWED_ORIGINS" in wildcard_message
    assert "TRUSTED_HOSTS" in wildcard_message


def test_production_oauth_pairs_and_local_storage_are_validated(monkeypatch) -> None:
    optional = production_settings(integration_token_encryption_key=None)
    assert optional.app_env == "production"
    assert optional.gemini_api_key is None
    assert optional.google_oauth_client_id is None
    assert optional.github_oauth_client_id is None

    values = optional.model_dump()
    values.pop("database_url")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
    with pytest.raises(ValidationError):
        production_settings(document_storage_backend="invalid")
    with pytest.raises(ValidationError):
        production_settings(s3_bucket=None)

    with pytest.raises(ValidationError):
        production_settings(google_oauth_client_id="client-only")
    with pytest.raises(ValidationError):
        production_settings(
            google_oauth_client_id="client",
            google_oauth_client_secret="credential",
            integration_token_encryption_key=None,
        )
    with pytest.raises(ValidationError):
        production_settings(
            document_storage_backend="local",
            document_storage_path="relative/documents",
        )


def test_database_pool_and_tls_options_are_centralized() -> None:
    settings = production_settings()
    options = database_engine_options(settings)
    assert options["pool_pre_ping"] is True
    assert options["pool_size"] == settings.database_pool_size
    assert options["connect_args"] == {"ssl": "require"}


def test_local_document_storage_contract_and_containment(tmp_path) -> None:
    storage = LocalDocumentStorage(str(tmp_path / "documents"))
    stored = storage.put("project/document.txt", b"safe", "text/plain")
    assert stored.size_bytes == 4
    assert storage.metadata("project/document.txt").size_bytes == 4
    with storage.open("project/document.txt") as stream:
        assert stream.read() == b"safe"
    with pytest.raises(AppError) as error:
        storage.put("../escape.txt", b"unsafe", "text/plain")
    assert error.value.code == "invalid_document_path"
    storage.delete("project/document.txt")
    with pytest.raises(AppError):
        storage.open("project/document.txt")


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    class MissingObject(Exception):
        response = {"Error": {"Code": "NoSuchKey"}, "ResponseMetadata": {"HTTPStatusCode": 404}}

    def put_object(self, *, Bucket, Key, Body, ContentType):
        assert ContentType == "text/plain"
        self.objects[(Bucket, Key)] = Body
        return {"ETag": '"test-etag"'}

    def get_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise self.MissingObject()
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise self.MissingObject()
        return {
            "ContentLength": len(self.objects[(Bucket, Key)]),
            "ETag": '"test-etag"',
        }

    def delete_object(self, *, Bucket, Key):
        self.objects.pop((Bucket, Key), None)
        return {}


def test_s3_document_storage_contract_uses_private_backend_access() -> None:
    client = FakeS3()
    storage = S3DocumentStorage(production_settings(), client=client)
    stored = storage.put("project/document.txt", b"safe", "text/plain")
    assert stored.etag == '"test-etag"'
    assert storage.exists("project/document.txt") is True
    assert storage.metadata("project/document.txt").size_bytes == 4
    with storage.open("project/document.txt") as stream:
        assert stream.read() == b"safe"
    storage.delete("project/document.txt")
    assert client.objects == {}
    assert storage.exists("project/document.txt") is False
    with pytest.raises(AppError) as error:
        storage.put("../escape.txt", b"unsafe", "text/plain")
    assert error.value.code == "invalid_document_path"


class FailingS3(FakeS3):
    def head_object(self, *, Bucket, Key):
        raise RuntimeError("provider unavailable")


def test_s3_storage_normalizes_provider_errors_and_missing_objects() -> None:
    storage = S3DocumentStorage(production_settings(), client=FakeS3())
    assert storage.exists("project/missing.txt") is False
    with pytest.raises(AppError) as missing:
        storage.open("project/missing.txt")
    assert missing.value.code == "document_file_missing"

    unavailable = S3DocumentStorage(production_settings(), client=FailingS3())
    with pytest.raises(AppError) as error:
        unavailable.exists("project/document.txt")
    assert error.value.code == "document_storage_unavailable"


async def test_request_ids_and_security_headers_are_safe(client) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "bad request id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad request id"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" not in response.headers


async def test_production_http_boundaries_and_error_redaction(monkeypatch) -> None:
    import app.core.handlers as handlers_module
    import app.main as main_module

    settings = production_settings(integration_token_encryption_key=None)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(handlers_module, "get_settings", lambda: settings)
    application = main_module.create_app()
    router = APIRouter()

    @router.get("/forced-error")
    async def forced_error():
        raise RuntimeError("private /server/path and credential material")

    application.include_router(router)
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://api.example.com") as browser:
        health = await browser.get("/health")
        assert health.status_code == 200
        assert health.headers["Strict-Transport-Security"].startswith("max-age=")
        assert "frame-ancestors" in health.headers["Content-Security-Policy"]
        assert (await browser.get("/api/docs")).status_code == 404

        accepted = await browser.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://pmo.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert accepted.headers["Access-Control-Allow-Origin"] == "https://pmo.example.com"
        rejected = await browser.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "Access-Control-Allow-Origin" not in rejected.headers

        failure = await browser.get("/forced-error")
        assert failure.status_code == 500
        assert failure.json()["error"]["code"] == "internal_error"
        assert "server/path" not in failure.text
        assert "credential" not in failure.text
