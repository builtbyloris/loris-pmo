"""Add Sprint 11 operational AI outputs and meeting proposals.

Revision ID: 20260831_0011
Revises: 20260830_0010
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0011"
down_revision: str | None = "20260830_0010"
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
        "ai_briefings",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "DAILY",
                "WEEKLY",
                name="ai_briefing_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(80)),
        sa.Column("model", sa.String(160)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_briefings_project_kind_generated",
        "ai_briefings",
        ["project_id", "kind", "generated_at"],
    )
    op.create_index(
        "ix_ai_briefings_project_fingerprint", "ai_briefings", ["project_id", "fingerprint"]
    )
    op.create_table(
        "ai_scenarios",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "TASK_DELAY",
                "MILESTONE_DELAY",
                "COST_INCREASE",
                "RESOURCE_UNAVAILABLE",
                "RISK_OCCURS",
                name="ai_scenario_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("deterministic_impact", sa.JSON(), nullable=False),
        sa.Column("interpretation", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_scenarios_project_created", "ai_scenarios", ["project_id", "created_at"])
    op.create_index("ix_ai_scenarios_project_type", "ai_scenarios", ["project_id", "type"])
    op.create_table(
        "meeting_ai_analyses",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="CASCADE",
            name="fk_meeting_ai_analyses_project_meeting",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meeting_ai_analyses_meeting_generated",
        "meeting_ai_analyses",
        ["meeting_id", "generated_at"],
    )
    op.create_index(
        "ix_meeting_ai_analyses_fingerprint", "meeting_ai_analyses", ["project_id", "fingerprint"]
    )
    op.create_table(
        "meeting_ai_proposals",
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_key", sa.String(120), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "ACTION_ITEM",
                "DECISION",
                "RISK",
                "ISSUE",
                name="meeting_ai_proposal_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "CONFIRMED",
                "REJECTED",
                name="meeting_ai_proposal_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("confirmed_entity_type", sa.String(80)),
        sa.Column("confirmed_entity_id", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["analysis_id"], ["meeting_ai_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="CASCADE",
            name="fk_meeting_ai_proposals_project_meeting",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "proposal_key", name="uq_meeting_ai_proposal_key"),
    )
    op.create_index(
        "ix_meeting_ai_proposals_meeting_status", "meeting_ai_proposals", ["meeting_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_meeting_ai_proposals_meeting_status", table_name="meeting_ai_proposals")
    op.drop_table("meeting_ai_proposals")
    op.drop_index("ix_meeting_ai_analyses_fingerprint", table_name="meeting_ai_analyses")
    op.drop_index("ix_meeting_ai_analyses_meeting_generated", table_name="meeting_ai_analyses")
    op.drop_table("meeting_ai_analyses")
    op.drop_index("ix_ai_scenarios_project_type", table_name="ai_scenarios")
    op.drop_index("ix_ai_scenarios_project_created", table_name="ai_scenarios")
    op.drop_table("ai_scenarios")
    op.drop_index("ix_ai_briefings_project_fingerprint", table_name="ai_briefings")
    op.drop_index("ix_ai_briefings_project_kind_generated", table_name="ai_briefings")
    op.drop_table("ai_briefings")
