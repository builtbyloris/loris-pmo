"""Add tasks, milestones, and task dependencies.

Revision ID: 20260828_0003
Revises: 20260828_0002
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0003"
down_revision: str | None = "20260828_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    milestone_status = sa.Enum(
        "NOT_STARTED",
        "IN_PROGRESS",
        "AT_RISK",
        "COMPLETED",
        name="milestone_status",
        native_enum=False,
        create_constraint=True,
    )
    task_status = sa.Enum(
        "BACKLOG",
        "TODO",
        "IN_PROGRESS",
        "BLOCKED",
        "REVIEW",
        "DONE",
        "CANCELLED",
        name="task_status",
        native_enum=False,
        create_constraint=True,
    )
    task_priority = sa.Enum(
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
        name="task_priority",
        native_enum=False,
        create_constraint=True,
    )
    dependency_type = sa.Enum(
        "BLOCKS",
        "DEPENDS_ON",
        "RELATED_TO",
        name="task_dependency_type",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "milestones",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", milestone_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
            name="fk_milestones_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_milestones"),
        sa.UniqueConstraint("project_id", "id", name="uq_milestones_project_id_id"),
    )
    op.create_index("ix_milestones_project_due_date", "milestones", ["project_id", "due_date"])

    op.create_table(
        "tasks",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("parent_task_id", sa.Uuid(), nullable=True),
        sa.Column("milestone_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_effort", sa.Numeric(10, 2), nullable=False),
        sa.Column("actual_effort", sa.Numeric(10, 2), nullable=False),
        sa.Column("completion_percentage", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("actual_effort >= 0", name="ck_tasks_task_actual_effort_nonnegative"),
        sa.CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_tasks_task_completion_percentage_valid",
        ),
        sa.CheckConstraint(
            "due_date IS NULL OR start_date IS NULL OR due_date >= start_date",
            name="ck_tasks_task_dates_valid",
        ),
        sa.CheckConstraint(
            "estimated_effort >= 0", name="ck_tasks_task_estimated_effort_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_tasks_project_milestone",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "parent_task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_tasks_project_parent_task",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_tasks_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
        sa.UniqueConstraint("project_id", "id", name="uq_tasks_project_id_id"),
    )
    op.create_index("ix_tasks_milestone_id", "tasks", ["milestone_id"])
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"])
    op.create_index("ix_tasks_project_archived", "tasks", ["project_id", "archived_at"])
    op.create_index("ix_tasks_project_due_date", "tasks", ["project_id", "due_date"])
    op.create_index("ix_tasks_project_status", "tasks", ["project_id", "status"])

    op.create_table(
        "task_dependencies",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_task_id", sa.Uuid(), nullable=False),
        sa.Column("target_task_id", sa.Uuid(), nullable=False),
        sa.Column("dependency_type", dependency_type, nullable=False),
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
        sa.CheckConstraint(
            "source_task_id <> target_task_id",
            name="ck_task_dependencies_task_dependency_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "source_task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_task_dependencies_project_source",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "target_task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_task_dependencies_project_target",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_task_dependencies_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_task_dependencies"),
        sa.UniqueConstraint(
            "project_id",
            "source_task_id",
            "target_task_id",
            "dependency_type",
            name="uq_task_dependencies_relation",
        ),
    )
    op.create_index(
        "ix_task_dependencies_source",
        "task_dependencies",
        ["project_id", "source_task_id"],
    )
    op.create_index(
        "ix_task_dependencies_target",
        "task_dependencies",
        ["project_id", "target_task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_task_dependencies_target", table_name="task_dependencies")
    op.drop_index("ix_task_dependencies_source", table_name="task_dependencies")
    op.drop_table("task_dependencies")
    op.drop_index("ix_tasks_project_status", table_name="tasks")
    op.drop_index("ix_tasks_project_due_date", table_name="tasks")
    op.drop_index("ix_tasks_project_archived", table_name="tasks")
    op.drop_index("ix_tasks_parent_task_id", table_name="tasks")
    op.drop_index("ix_tasks_milestone_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_milestones_project_due_date", table_name="milestones")
    op.drop_table("milestones")
