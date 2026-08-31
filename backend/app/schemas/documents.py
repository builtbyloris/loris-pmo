from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.documents import DocumentCategory, DocumentStatus, ImportStatus, ImportTarget


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    size_bytes: int
    category: DocumentCategory
    description: str | None
    status: DocumentStatus
    processing_error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    category: DocumentCategory | None = None
    description: str | None = Field(default=None, max_length=2000)


class KnowledgeMatch(BaseModel):
    evidence_id: str
    document_id: UUID
    filename: str
    excerpt: str
    location: dict[str, Any] | None = None
    score: float


class KnowledgeQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class KnowledgeQueryRead(BaseModel):
    matches: list[KnowledgeMatch]


class ReportType(StrEnum):
    PROJECT_SUMMARY = "project-summary"
    EXECUTIVE_SUMMARY = "executive-summary"
    WEEKLY = "weekly"
    BUDGET = "budget"
    CONTROL = "control"
    TEAM = "team"


class ExportDataset(StrEnum):
    TASKS = "tasks"
    MILESTONES = "milestones"
    EXPENSES = "expenses"
    RISKS = "risks"
    ISSUES = "issues"
    CHANGES = "changes"
    TEAM = "team"
    ACTIVITY = "activity"


class ReportSection(BaseModel):
    key: str
    title: str
    data: Any


class ReportRead(BaseModel):
    project_id: UUID
    type: ReportType
    title: str
    generated_at: datetime
    period_start: datetime | None = None
    period_end: datetime | None = None
    sections: list[ReportSection]


class ImportPreviewRead(BaseModel):
    id: UUID
    project_id: UUID
    target: ImportTarget
    source_format: str
    source_filename: str
    row_count: int
    valid_count: int
    errors: list[dict[str, Any]]
    preview: list[dict[str, Any]]
    can_confirm: bool
    status: ImportStatus


class ImportConfirmRead(BaseModel):
    batch_id: UUID
    target: ImportTarget
    imported_count: int
    status: ImportStatus
