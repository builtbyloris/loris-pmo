from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from uuid import UUID, uuid4

from docx import Document as DocxDocument
from fastapi import UploadFile
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.documents import DocumentCategory, DocumentChunk, DocumentStatus, ProjectDocument
from app.models.project import Project
from app.schemas.documents import DocumentUpdate, KnowledgeMatch
from app.services.audit import AuditService
from app.services.authorization import AuthorizationService, Capability, accessible_project_ids
from app.services.projects import ProjectService

ALLOWED = {"pdf", "docx", "xlsx", "csv", "txt", "png", "jpg", "jpeg", "webp"}
EXTRACTABLE = {"pdf", "docx", "xlsx", "csv", "txt"}
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "are",
    "from",
    "what",
    "come",
    "della",
    "delle",
    "degli",
    "che",
    "per",
    "con",
    "una",
    "uno",
    "del",
    "dei",
}


def _tokens(value: str) -> set[str]:
    return {word for word in re.findall(r"[\w-]{3,}", value.lower()) if word not in STOP_WORDS}


def _chunk_text(parts: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    chunks: list[tuple[str, dict]] = []
    for text, location in parts:
        clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        start = 0
        while start < len(clean) and len(chunks) < 300:
            end = min(len(clean), start + 1200)
            if end < len(clean):
                split = clean.rfind(" ", start + 700, end)
                if split > start:
                    end = split
            value = clean[start:end].strip()
            if value:
                chunks.append((value, location))
            if end >= len(clean):
                break
            start = max(start + 1, end - 150)
    return chunks


def extract_document(data: bytes, extension: str) -> list[tuple[str, dict]]:
    if extension == "txt":
        return [(data.decode("utf-8-sig", errors="replace")[:200_000], {"section": "text"})]
    if extension == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return [
            ((page.extract_text() or "")[:30_000], {"page": index + 1})
            for index, page in enumerate(reader.pages[:50])
        ]
    if extension == "docx":
        document = DocxDocument(io.BytesIO(data))
        text = [paragraph.text for paragraph in document.paragraphs[:2000]]
        for table in document.tables[:50]:
            text.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows[:100])
        return [("\n".join(text)[:200_000], {"section": "document"})]
    if extension == "csv":
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace")))
        rows = [" | ".join(row[:40]) for _, row in zip(range(101), reader, strict=False)]
        return [("\n".join(rows), {"sheet": "CSV"})]
    if extension == "xlsx":
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        result = []
        for sheet in book.worksheets[:5]:
            rows = []
            for row in list(sheet.iter_rows(values_only=True))[:101]:
                rows.append(" | ".join("" if cell is None else str(cell) for cell in row[:30]))
            result.append(("\n".join(rows), {"sheet": sheet.title}))
        return result
    return []


class DocumentService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID, settings: Settings) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.settings = settings
        self.audit = AuditService(session, owner_user_id)
        self.root = Path(settings.document_storage_path).expanduser().resolve()

    async def _project(self, project_id: UUID, *, mutable: bool = False) -> Project:
        project = await ProjectService(self.session, self.owner_user_id).get(project_id)
        if mutable:
            ProjectService._ensure_mutable(project)
        return project

    async def _document(self, project_id: UUID, document_id: UUID) -> ProjectDocument:
        result = await self.session.execute(
            select(ProjectDocument)
            .join(Project)
            .where(
                ProjectDocument.id == document_id,
                ProjectDocument.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise AppError(
                code="document_not_found", message="Document not found.", status_code=404
            )
        if document.category == DocumentCategory.FINANCE:
            await AuthorizationService(self.session, self.owner_user_id).require(
                project_id, Capability.FINANCE_READ
            )
        return document

    async def list(self, project_id: UUID) -> list[ProjectDocument]:
        await self._project(project_id)
        query = select(ProjectDocument).where(ProjectDocument.project_id == project_id)
        if not await AuthorizationService(self.session, self.owner_user_id).can(
            project_id, Capability.FINANCE_READ
        ):
            query = query.where(ProjectDocument.category != DocumentCategory.FINANCE)
        result = await self.session.execute(query.order_by(ProjectDocument.created_at.desc()))
        return list(result.scalars())

    async def upload(
        self,
        project_id: UUID,
        upload: UploadFile,
        category: DocumentCategory,
        description: str | None,
    ) -> ProjectDocument:
        await self._project(project_id, mutable=True)
        if category == DocumentCategory.FINANCE:
            await AuthorizationService(self.session, self.owner_user_id).require(
                project_id, Capability.FINANCE_MANAGE
            )
        original = Path(upload.filename or "document").name[:255]
        extension = Path(original).suffix.lower().lstrip(".")
        if extension not in ALLOWED:
            raise AppError(
                code="document_type_not_supported",
                message="Unsupported document type.",
                status_code=415,
            )
        limit = self.settings.document_max_upload_mb * 1024 * 1024
        content = await upload.read(limit + 1)
        if len(content) > limit:
            raise AppError(
                code="document_too_large",
                message="Document exceeds the upload limit.",
                status_code=413,
            )
        if not content:
            raise AppError(
                code="document_empty", message="The uploaded document is empty.", status_code=422
            )
        document_id = uuid4()
        internal = f"{document_id.hex}.{extension}"
        relative = Path(str(project_id)) / internal
        target = (self.root / relative).resolve()
        if self.root not in target.parents:
            raise AppError(
                code="invalid_document_path", message="Invalid document path.", status_code=400
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        document = ProjectDocument(
            id=document_id,
            project_id=project_id,
            original_filename=original,
            internal_filename=internal,
            file_type=extension,
            mime_type=(upload.content_type or "application/octet-stream")[:120],
            size_bytes=len(content),
            category=category,
            description=description,
            storage_key=str(relative),
            status=DocumentStatus.PROCESSING
            if extension in EXTRACTABLE
            else DocumentStatus.UNSUPPORTED,
            processing_error=None
            if extension in EXTRACTABLE
            else "Text extraction is not available for this file type.",
            created_by_user_id=self.owner_user_id,
        )
        self.session.add(document)
        await self.session.flush()
        try:
            if extension in EXTRACTABLE:
                chunks = _chunk_text(extract_document(content, extension))
                for index, (text, location) in enumerate(chunks):
                    self.session.add(
                        DocumentChunk(
                            document_id=document.id,
                            project_id=project_id,
                            chunk_index=index,
                            text=text,
                            location=location,
                        )
                    )
                document.status = DocumentStatus.READY
                document.processing_error = None
        except Exception:
            document.status = DocumentStatus.FAILED
            document.processing_error = (
                "Text extraction failed; the original file remains available."
            )
        self.audit.record(
            project_id=project_id,
            action="document.uploaded",
            entity_type="project_document",
            entity_id=document.id,
            changes={
                "filename": original,
                "file_type": extension,
                "size_bytes": len(content),
                "status": document.status.value,
            },
        )
        await self.session.commit()
        return await self._document(project_id, document.id)

    def path_for(self, document: ProjectDocument) -> Path:
        path = (self.root / document.storage_key).resolve()
        if self.root not in path.parents or not path.is_file():
            raise AppError(
                code="document_file_missing",
                message="Document file is unavailable.",
                status_code=404,
            )
        return path

    async def update(
        self, project_id: UUID, document_id: UUID, data: DocumentUpdate
    ) -> ProjectDocument:
        await self._project(project_id, mutable=True)
        document = await self._document(project_id, document_id)
        changes = data.model_dump(exclude_unset=True)
        if (
            document.category == DocumentCategory.FINANCE
            or changes.get("category") == DocumentCategory.FINANCE
        ):
            await AuthorizationService(self.session, self.owner_user_id).require(
                project_id, Capability.FINANCE_MANAGE
            )
        for key, value in changes.items():
            setattr(document, key, value)
        self.audit.record(
            project_id=project_id,
            action="document.updated",
            entity_type="project_document",
            entity_id=document.id,
            changes={"fields": list(changes)},
        )
        await self.session.commit()
        return await self._document(project_id, document_id)

    async def delete(self, project_id: UUID, document_id: UUID) -> None:
        await self._project(project_id, mutable=True)
        document = await self._document(project_id, document_id)
        path = (self.root / document.storage_key).resolve()
        self.audit.record(
            project_id=project_id,
            action="document.deleted",
            entity_type="project_document",
            entity_id=document.id,
            changes={"filename": document.original_filename},
        )
        await self.session.delete(document)
        await self.session.commit()
        if self.root in path.parents:
            path.unlink(missing_ok=True)

    async def search(self, project_id: UUID, query: str, limit: int = 5) -> list[KnowledgeMatch]:
        await self._project(project_id)
        terms = _tokens(query)
        if not terms:
            return []
        statement = (
            select(DocumentChunk, ProjectDocument)
            .join(ProjectDocument, ProjectDocument.id == DocumentChunk.document_id)
            .join(Project)
            .where(
                DocumentChunk.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
                ProjectDocument.status == DocumentStatus.READY,
            )
        )
        if not await AuthorizationService(self.session, self.owner_user_id).can(
            project_id, Capability.FINANCE_READ
        ):
            statement = statement.where(ProjectDocument.category != DocumentCategory.FINANCE)
        result = await self.session.execute(statement)
        matches = []
        lowered = query.lower().strip()
        for chunk, document in result.all():
            overlap = terms & _tokens(chunk.text)
            if not overlap:
                continue
            score = len(overlap) / len(terms) + (0.25 if lowered in chunk.text.lower() else 0)
            matches.append(
                KnowledgeMatch(
                    evidence_id=f"document_chunk:{chunk.id}",
                    document_id=document.id,
                    filename=document.original_filename,
                    excerpt=chunk.text[:900],
                    location=chunk.location,
                    score=round(score, 4),
                )
            )
        return sorted(matches, key=lambda item: (-item.score, item.filename))[:limit]
