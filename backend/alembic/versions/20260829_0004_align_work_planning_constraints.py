"""Align Work Planning check-constraint names with model metadata.

Revision ID: 20260829_0004
Revises: 20260828_0003
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260829_0004"
down_revision: str | None = "20260828_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RENAMES = (
    (
        "tasks",
        "ck_tasks_ck_tasks_task_actual_effort_nonnegative",
        "ck_tasks_task_actual_effort_nonnegative",
    ),
    (
        "tasks",
        "ck_tasks_ck_tasks_task_completion_percentage_valid",
        "ck_tasks_task_completion_percentage_valid",
    ),
    (
        "tasks",
        "ck_tasks_ck_tasks_task_dates_valid",
        "ck_tasks_task_dates_valid",
    ),
    (
        "tasks",
        "ck_tasks_ck_tasks_task_estimated_effort_nonnegative",
        "ck_tasks_task_estimated_effort_nonnegative",
    ),
    (
        "task_dependencies",
        "ck_task_dependencies_ck_task_dependencies_task_dependen_fdf2",
        "ck_task_dependencies_task_dependency_not_self",
    ),
)


def _rename(table: str, old_name: str, new_name: str) -> None:
    op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')


def upgrade() -> None:
    for table, old_name, new_name in RENAMES:
        _rename(table, old_name, new_name)


def downgrade() -> None:
    for table, old_name, new_name in reversed(RENAMES):
        _rename(table, new_name, old_name)
