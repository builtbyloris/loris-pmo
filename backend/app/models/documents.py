from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class DocumentCategory(StrEnum):
    REQUIREMENTS = "REQUIREMENTS"
    SPECIFICATIONS = "SPECIFICATIONS"
    MEETING_NOTES = "MEETING_NOTES"
    CONTRACTS = "CONTRACTS"
    REPORTS = "REPORTS"
    FINANCE = "FINANCE"
    OTHER = "OTHER"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"


class ImportTarget(StrEnum):
    TASKS = "TASKS"
    EXPENSES = "EXPENSES"


class ImportStatus(StrEnum):
    VALIDATED = "VALIDATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


category_enum = Enum(
    DocumentCategory, name="document_category", native_enum=False, create_constraint=True
)
status_enum = Enum(
    DocumentStatus, name="document_status", native_enum=False, create_constraint=True
)
import_target_enum = Enum(
    ImportTarget, name="import_target", native_enum=False, create_constraint=True
)
import_status_enum = Enum(
    ImportStatus, name="import_status", native_enum=False, create_constraint=True
)


class ProjectDocument(UUIDTimestampMixin, Base):
    __tablename__ = "project_documents"
    __table_args__ = (
        Index("ix_project_documents_project_created", "project_id", "created_at"),
        Index("ix_project_documents_project_status", "project_id", "status"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_filename: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[DocumentCategory] = mapped_column(
        category_enum, default=DocumentCategory.OTHER, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    status: Mapped[DocumentStatus] = mapped_column(
        status_enum, default=DocumentStatus.UPLOADED, nullable=False
    )
    processing_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class DocumentChunk(UUIDTimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
        Index("ix_document_chunks_project_document", "project_id", "document_id"),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_documents.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ImportBatch(UUIDTimestampMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (Index("ix_import_batches_project_created", "project_id", "created_at"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target: Mapped[ImportTarget] = mapped_column(import_target_enum, nullable=False)
    source_format: Mapped[str] = mapped_column(String(10), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_rows: Mapped[list] = mapped_column(JSON, nullable=False)
    validation_errors: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        import_status_enum, default=ImportStatus.VALIDATED, nullable=False
    )
