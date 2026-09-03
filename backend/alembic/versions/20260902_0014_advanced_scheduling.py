"""Add normalized active project schedule baselines.

Revision ID: 20260902_0014
Revises: 20260901_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0014"
down_revision: str | None = "20260901_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schedule_baselines",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_end_date", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=True),
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
            ["created_by_user_id"],
            ["users.id"],
            name="fk_schedule_baselines_created_by_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_schedule_baselines_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schedule_baselines"),
        sa.UniqueConstraint("project_id", name="uq_schedule_baselines_project"),
    )
    op.create_table(
        "schedule_baseline_tasks",
        sa.Column("baseline_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
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
            ["baseline_id"],
            ["schedule_baselines.id"],
            ondelete="CASCADE",
            name="fk_schedule_baseline_tasks_baseline_id_schedule_baselines",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_schedule_baseline_tasks_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_schedule_baseline_tasks_project_task",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schedule_baseline_tasks"),
        sa.UniqueConstraint("baseline_id", "task_id", name="uq_schedule_baseline_tasks_item"),
    )
    op.create_index(
        "ix_schedule_baseline_tasks_baseline", "schedule_baseline_tasks", ["baseline_id"]
    )
    op.create_table(
        "schedule_baseline_milestones",
        sa.Column("baseline_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
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
            ["baseline_id"],
            ["schedule_baselines.id"],
            ondelete="CASCADE",
            name="fk_schedule_baseline_milestones_baseline_id_schedule_baselines",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_schedule_baseline_milestones_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_schedule_baseline_milestones_project_milestone",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schedule_baseline_milestones"),
        sa.UniqueConstraint(
            "baseline_id", "milestone_id", name="uq_schedule_baseline_milestones_item"
        ),
    )
    op.create_index(
        "ix_schedule_baseline_milestones_baseline", "schedule_baseline_milestones", ["baseline_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_schedule_baseline_milestones_baseline", table_name="schedule_baseline_milestones"
    )
    op.drop_table("schedule_baseline_milestones")
    op.drop_index("ix_schedule_baseline_tasks_baseline", table_name="schedule_baseline_tasks")
    op.drop_table("schedule_baseline_tasks")
    op.drop_table("schedule_baselines")
