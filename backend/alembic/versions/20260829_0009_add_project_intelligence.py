"""Add project intelligence alerts and health history.

Revision ID: 20260829_0009
Revises: 20260829_0008
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0009"
down_revision: str | None = "20260829_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "health_snapshots",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "HEALTHY",
                "WATCH",
                "AT_RISK",
                "CRITICAL",
                name="health_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("drivers", sa.JSON(), nullable=False),
        sa.Column("trigger", sa.String(length=80), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_health_snapshots_project_created",
        "health_snapshots",
        ["project_id", "created_at"],
    )
    op.create_table(
        "alerts",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("rule_type", sa.String(length=80), nullable=False),
        sa.Column("condition_key", sa.String(length=180), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "INFO",
                "WARNING",
                "CRITICAL",
                name="alert_severity",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("title_key", sa.String(length=160), nullable=False),
        sa.Column("reason_key", sa.String(length=160), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("related_entity_type", sa.String(length=80), nullable=True),
        sa.Column("related_entity_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "ACKNOWLEDGED",
                "RESOLVED",
                name="alert_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "condition_key", name="uq_alerts_project_condition"),
    )
    op.create_index("ix_alerts_project_status", "alerts", ["project_id", "status"])
    op.create_index("ix_alerts_project_severity", "alerts", ["project_id", "severity"])


def downgrade() -> None:
    op.drop_index("ix_alerts_project_severity", table_name="alerts")
    op.drop_index("ix_alerts_project_status", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_health_snapshots_project_created", table_name="health_snapshots")
    op.drop_table("health_snapshots")
