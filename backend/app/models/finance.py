from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ExpenseStatus(StrEnum):
    PLANNED = "PLANNED"
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


expense_status_enum = Enum(
    ExpenseStatus,
    name="expense_status",
    native_enum=False,
    create_constraint=True,
)


class BudgetCategory(UUIDTimestampMixin, Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        CheckConstraint("planned_amount >= 0", name="budget_category_planned_nonnegative"),
        UniqueConstraint("project_id", "name", name="uq_budget_categories_project_name"),
        UniqueConstraint("project_id", "id", name="uq_budget_categories_project_id"),
        Index("ix_budget_categories_project_name", "project_id", "name"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    planned_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="category", passive_deletes=True
    )


class Expense(UUIDTimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="expense_amount_positive"),
        ForeignKeyConstraint(
            ["project_id", "budget_category_id"],
            ["budget_categories.project_id", "budget_categories.id"],
            ondelete="RESTRICT",
            name="fk_expenses_project_category",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="RESTRICT",
            name="fk_expenses_project_task",
        ),
        ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            ondelete="RESTRICT",
            name="fk_expenses_project_milestone",
        ),
        Index("ix_expenses_project_date", "project_id", "date"),
        Index("ix_expenses_project_status", "project_id", "status"),
        Index("ix_expenses_project_category", "project_id", "budget_category_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    budget_category_id: Mapped[UUID | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[ExpenseStatus] = mapped_column(
        expense_status_enum, default=ExpenseStatus.PLANNED, nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(nullable=True)
    milestone_id: Mapped[UUID | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[BudgetCategory | None] = relationship(back_populates="expenses")
