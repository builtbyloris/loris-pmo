from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.documents import (
    DocumentCategory,
    DocumentSemanticStatus,
    DocumentStatus,
    ImportStatus,
    ImportTarget,
)


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
    semantic_status: DocumentSemanticStatus
    embedding_model: str | None
    embedding_version: str | None
    semantic_indexed_at: datetime | None
    semantic_error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    category: DocumentCategory | None = None
    description: str | None = Field(default=None, max_length=2000)


class RetrievalMode(StrEnum):
    LEXICAL = "LEXICAL"
    SEMANTIC = "SEMANTIC"
    HYBRID = "HYBRID"


class QueryIntent(StrEnum):
    LOOKUP = "LOOKUP"
    MULTI_DOCUMENT = "MULTI_DOCUMENT"
    COMPARISON = "COMPARISON"
    SUMMARY = "SUMMARY"


class KnowledgeMatch(BaseModel):
    evidence_id: str
    document_id: UUID
    filename: str
    excerpt: str
    location: dict[str, Any] | None = None
    score: float
    lexical_score: float | None = None
    semantic_score: float | None = None
    rank: int
    retrieval_mode: RetrievalMode
    chunk_index: int
    category: DocumentCategory


class KnowledgeQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    categories: list[DocumentCategory] = Field(default_factory=list, max_length=7)
    limit: int = Field(default=5, ge=1, le=10)


class RetrievalDiagnostics(BaseModel):
    mode: RetrievalMode
    intent: QueryIntent
    lexical_candidates: int
    semantic_candidates: int
    authorized_chunks_considered: int
    merged_candidates: int
    selected_chunks: int
    semantic_available: bool
    fallback_reason: str | None = None


class KnowledgeQueryRead(BaseModel):
    matches: list[KnowledgeMatch]
    diagnostics: RetrievalDiagnostics


class KnowledgeStatusRead(BaseModel):
    provider_available: bool
    embedding_model: str
    embedding_version: str
    total_documents: int
    ready_documents: int
    indexed_documents: int
    partial_documents: int
    failed_documents: int
    lexical_only_documents: int
    total_chunks: int
    indexed_chunks: int


class KnowledgeIndexRead(BaseModel):
    document_id: UUID
    status: DocumentSemanticStatus
    indexed_chunks: int
    total_chunks: int
    reused_chunks: int
    model: str | None
    indexed_at: datetime | None
    error: str | None


class KnowledgeAnswerRequest(KnowledgeQuery):
    language: Literal["en", "it"] = "en"


class KnowledgeComparisonRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=2, max_length=4)
    focus: str = Field(default="Compare the selected documents.", min_length=2, max_length=500)
    language: Literal["en", "it"] = "en"


class KnowledgeComparisonOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=3000)
    agreements: list[str] = Field(default_factory=list, max_length=5)
    differences: list[str] = Field(default_factory=list, max_length=5)
    potential_conflicts: list[str] = Field(default_factory=list, max_length=5)
    missing_information: list[str] = Field(default_factory=list, max_length=5)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class KnowledgeComparisonRead(BaseModel):
    summary: str
    agreements: list[str]
    differences: list[str]
    potential_conflicts: list[str]
    missing_information: list[str]
    evidence: list[dict[str, Any]]
    provider: str
    model: str


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
