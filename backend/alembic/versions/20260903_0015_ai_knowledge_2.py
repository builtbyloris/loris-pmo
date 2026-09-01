"""Add V2.3 document semantic index metadata and chunk embeddings."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0015"
down_revision: str | None = "20260902_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_documents",
        sa.Column(
            "semantic_status",
            sa.Enum(
                "NOT_INDEXED",
                "INDEXING",
                "READY",
                "PARTIAL",
                "FAILED",
                "LEXICAL_ONLY",
                name="document_semantic_status",
                native_enum=False,
            ),
            server_default="NOT_INDEXED",
            nullable=False,
        ),
    )
    op.add_column("project_documents", sa.Column("embedding_model", sa.String(100)))
    op.add_column("project_documents", sa.Column("embedding_version", sa.String(32)))
    op.add_column("project_documents", sa.Column("semantic_indexed_at", sa.DateTime(timezone=True)))
    op.add_column("project_documents", sa.Column("semantic_error", sa.String(100)))
    op.execute(
        "UPDATE project_documents SET semantic_status = 'LEXICAL_ONLY' WHERE status = 'READY'"
    )
    op.create_table(
        "document_chunk_embeddings",
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["project_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", name="uq_document_chunk_embeddings_chunk"),
    )
    op.create_index(
        "ix_document_chunk_embeddings_project_model",
        "document_chunk_embeddings",
        ["project_id", "model", "version"],
    )
    op.create_index(
        "ix_document_chunk_embeddings_document",
        "document_chunk_embeddings",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunk_embeddings_document", table_name="document_chunk_embeddings")
    op.drop_index(
        "ix_document_chunk_embeddings_project_model", table_name="document_chunk_embeddings"
    )
    op.drop_table("document_chunk_embeddings")
    op.drop_column("project_documents", "semantic_error")
    op.drop_column("project_documents", "semantic_indexed_at")
    op.drop_column("project_documents", "embedding_version")
    op.drop_column("project_documents", "embedding_model")
    op.drop_column("project_documents", "semantic_status")
