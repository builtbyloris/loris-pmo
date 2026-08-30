"""Add persistent AI insights, recommendations, and analysis state.

Revision ID: 20260830_0010
Revises: 20260829_0009
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0010"
down_revision: str | None = "20260829_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
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
        "ai_insights",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "INFO",
                "WARNING",
                "CRITICAL",
                name="ai_insight_severity",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("signal_key", sa.String(length=220), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "DISMISSED",
                "RESOLVED",
                "EXPIRED",
                name="ai_insight_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ai_insight_confidence"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "fingerprint", name="uq_ai_insights_project_fingerprint"),
    )
    op.create_index("ix_ai_insights_project_status", "ai_insights", ["project_id", "status"])
    op.create_index(
        "ix_ai_insights_project_generated", "ai_insights", ["project_id", "generated_at"]
    )
    op.create_table(
        "ai_recommendations",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=True),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("signal_key", sa.String(length=220), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "REJECTED",
                "IGNORED",
                "EXPIRED",
                name="ai_recommendation_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        *timestamps(),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ai_recommendation_confidence",
        ),
        sa.ForeignKeyConstraint(["insight_id"], ["ai_insights.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "fingerprint", name="uq_ai_recommendations_project_fingerprint"
        ),
    )
    op.create_index(
        "ix_ai_recommendations_project_status", "ai_recommendations", ["project_id", "status"]
    )
    op.create_index(
        "ix_ai_recommendations_project_generated",
        "ai_recommendations",
        ["project_id", "generated_at"],
    )
    op.create_table(
        "ai_analysis_states",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("signal_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("model", sa.String(length=160), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_ai_analysis_states_project"),
    )
    op.create_index("ix_ai_analysis_states_analyzed", "ai_analysis_states", ["analyzed_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_analysis_states_analyzed", table_name="ai_analysis_states")
    op.drop_table("ai_analysis_states")
    op.drop_index("ix_ai_recommendations_project_generated", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_project_status", table_name="ai_recommendations")
    op.drop_table("ai_recommendations")
    op.drop_index("ix_ai_insights_project_generated", table_name="ai_insights")
    op.drop_index("ix_ai_insights_project_status", table_name="ai_insights")
    op.drop_table("ai_insights")
