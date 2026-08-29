from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
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


class TaskStatus(StrEnum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


task_status_enum = Enum(TaskStatus, name="task_status", native_enum=False, create_constraint=True)
task_priority_enum = Enum(
    TaskPriority, name="task_priority", native_enum=False, create_constraint=True
)


class Task(UUIDTimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "due_date IS NULL OR start_date IS NULL OR due_date >= start_date",
            name="task_dates_valid",
        ),
        CheckConstraint("estimated_effort >= 0", name="task_estimated_effort_nonnegative"),
        CheckConstraint("actual_effort >= 0", name="task_actual_effort_nonnegative"),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="task_completion_percentage_valid",
        ),
        UniqueConstraint("project_id", "id", name="uq_tasks_project_id_id"),
        ForeignKeyConstraint(
            ["project_id", "parent_task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_tasks_project_parent_task",
        ),
        ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_tasks_project_milestone",
        ),
        Index("ix_tasks_project_archived", "project_id", "archived_at"),
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_project_due_date", "project_id", "due_date"),
        Index("ix_tasks_parent_task_id", "parent_task_id"),
        Index("ix_tasks_milestone_id", "milestone_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    parent_task_id: Mapped[UUID | None] = mapped_column(nullable=True)
    milestone_id: Mapped[UUID | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        task_status_enum, default=TaskStatus.BACKLOG, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        task_priority_enum, default=TaskPriority.MEDIUM, nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_effort: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    actual_effort: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    completion_percentage: Mapped[int] = mapped_column(default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tasks")  # noqa: F821
    assignees: Mapped[list["TaskAssignee"]] = relationship(  # noqa: F821
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="assignments,project_member",
    )

    @property
    def assignee_ids(self) -> list[UUID]:
        return [assignment.project_member_id for assignment in self.assignees]
