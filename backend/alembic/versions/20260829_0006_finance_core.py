"""Add budget categories and expenses.

Revision ID: 20260829_0006
Revises: 20260829_0005
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0006"
down_revision: str | None = "20260829_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    expense_status = sa.Enum(
        "PLANNED",
        "PENDING",
        "PAID",
        "CANCELLED",
        name="expense_status",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "budget_categories",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("planned_amount", sa.Numeric(14, 2), nullable=False),
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
        sa.CheckConstraint(
            "planned_amount >= 0",
            name=op.f("ck_budget_categories_budget_category_planned_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_budget_categories_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budget_categories"),
        sa.UniqueConstraint("project_id", "id", name="uq_budget_categories_project_id"),
        sa.UniqueConstraint(
            "project_id", "name", name="uq_budget_categories_project_name"
        ),
    )
    op.create_index(
        "ix_budget_categories_project_name", "budget_categories", ["project_id", "name"]
    )

    op.create_table(
        "expenses",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("budget_category_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("supplier", sa.String(200), nullable=True),
        sa.Column("payer", sa.String(200), nullable=True),
        sa.Column("status", expense_status, nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("milestone_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint("amount > 0", name=op.f("ck_expenses_expense_amount_positive")),
        sa.ForeignKeyConstraint(
            ["project_id", "budget_category_id"],
            ["budget_categories.project_id", "budget_categories.id"],
            ondelete="RESTRICT",
            name="fk_expenses_project_category",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            ondelete="RESTRICT",
            name="fk_expenses_project_milestone",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_expenses_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="RESTRICT",
            name="fk_expenses_project_task",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
    )
    op.create_index(
        "ix_expenses_project_category", "expenses", ["project_id", "budget_category_id"]
    )
    op.create_index("ix_expenses_project_date", "expenses", ["project_id", "date"])
    op.create_index("ix_expenses_project_status", "expenses", ["project_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_expenses_project_status", table_name="expenses")
    op.drop_index("ix_expenses_project_date", table_name="expenses")
    op.drop_index("ix_expenses_project_category", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_budget_categories_project_name", table_name="budget_categories")
    op.drop_table("budget_categories")
