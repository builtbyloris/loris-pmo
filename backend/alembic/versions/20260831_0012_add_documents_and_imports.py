"""Add Sprint 12 project documents, chunks, and import batches."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0012"
down_revision: str | None = "20260831_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps():
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "project_documents",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("internal_filename", sa.String(100), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "REQUIREMENTS",
                "SPECIFICATIONS",
                "MEETING_NOTES",
                "CONTRACTS",
                "REPORTS",
                "FINANCE",
                "OTHER",
                name="document_category",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text()),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADED",
                "PROCESSING",
                "READY",
                "FAILED",
                "UNSUPPORTED",
                name="document_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("processing_error", sa.String(200)),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_filename"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_project_documents_project_created", "project_documents", ["project_id", "created_at"]
    )
    op.create_index(
        "ix_project_documents_project_status", "project_documents", ["project_id", "status"]
    )
    op.create_table(
        "document_chunks",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.JSON()),
        *timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["project_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
    )
    op.create_index(
        "ix_document_chunks_project_document", "document_chunks", ["project_id", "document_id"]
    )
    op.create_table(
        "import_batches",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "target",
            sa.Enum("TASKS", "EXPENSES", name="import_target", native_enum=False),
            nullable=False,
        ),
        sa.Column("source_format", sa.String(10), nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("normalized_rows", sa.JSON(), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("VALIDATED", "COMPLETED", "FAILED", name="import_status", native_enum=False),
            nullable=False,
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_batches_project_created", "import_batches", ["project_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_import_batches_project_created", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_index("ix_document_chunks_project_document", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_project_documents_project_status", table_name="project_documents")
    op.drop_index("ix_project_documents_project_created", table_name="project_documents")
    op.drop_table("project_documents")
