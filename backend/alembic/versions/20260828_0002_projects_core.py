"""Add Projects Core entities and audit events.

Revision ID: 20260828_0002
Revises: 20260828_0001
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0002"
down_revision: str | None = "20260828_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    project_status = sa.Enum(
        "NOT_STARTED",
        "ACTIVE",
        "ON_HOLD",
        "COMPLETED",
        "ARCHIVED",
        name="project_status",
        native_enum=False,
        create_constraint=True,
    )
    project_priority = sa.Enum(
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
        name="project_priority",
        native_enum=False,
        create_constraint=True,
    )
    objective_status = sa.Enum(
        "NOT_STARTED",
        "IN_PROGRESS",
        "ACHIEVED",
        "CANCELLED",
        name="objective_status",
        native_enum=False,
        create_constraint=True,
    )
    criterion_status = sa.Enum(
        "NOT_MET",
        "MET",
        "NOT_APPLICABLE",
        name="success_criterion_status",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "projects",
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("client_or_area", sa.String(200), nullable=True),
        sa.Column("status", project_status, nullable=False),
        sa.Column("priority", project_priority, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_end_date", sa.Date(), nullable=True),
        sa.Column("planned_budget", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("planned_budget >= 0", name="ck_projects_project_budget_nonnegative"),
        sa.CheckConstraint(
            "target_end_date IS NULL OR start_date IS NULL OR target_end_date >= start_date",
            name="ck_projects_project_dates_valid",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], name="fk_projects_owner_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("owner_user_id", "code", name="uq_projects_owner_code"),
    )
    op.create_index("ix_projects_owner_archived", "projects", ["owner_user_id", "archived_at"])
    op.create_index("ix_projects_owner_status", "projects", ["owner_user_id", "status"])
    op.create_table(
        "objectives",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", objective_status, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_objectives_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_objectives"),
        sa.UniqueConstraint("project_id", "id", name="uq_objectives_project_id_id"),
    )
    op.create_index("ix_objectives_project_status", "objectives", ["project_id", "status"])
    op.create_table(
        "success_criteria",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("objective_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_value", sa.String(240), nullable=True),
        sa.Column("status", criterion_status, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["project_id", "objective_id"],
            ["objectives.project_id", "objectives.id"],
            name="fk_success_criteria_project_objective",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_success_criteria_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_success_criteria"),
    )
    op.create_index(
        "ix_success_criteria_project_status", "success_criteria", ["project_id", "status"]
    )
    op.create_table(
        "audit_events",
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_audit_events_actor_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_audit_events_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index(
        "ix_audit_events_actor_created", "audit_events", ["actor_user_id", "created_at"]
    )
    op.create_index("ix_audit_events_project_created", "audit_events", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_project_created", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_success_criteria_project_status", table_name="success_criteria")
    op.drop_table("success_criteria")
    op.drop_index("ix_objectives_project_status", table_name="objectives")
    op.drop_table("objectives")
    op.drop_index("ix_projects_owner_status", table_name="projects")
    op.drop_index("ix_projects_owner_archived", table_name="projects")
    op.drop_table("projects")
