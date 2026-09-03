from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ScheduleBaseline(UUIDTimestampMixin, Base):
    __tablename__ = "schedule_baselines"
    __table_args__ = (UniqueConstraint("project_id", name="uq_schedule_baselines_project"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    target_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tasks: Mapped[list["ScheduleBaselineTask"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    milestones: Mapped[list["ScheduleBaselineMilestone"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class ScheduleBaselineTask(UUIDTimestampMixin, Base):
    __tablename__ = "schedule_baseline_tasks"
    __table_args__ = (
        UniqueConstraint("baseline_id", "task_id", name="uq_schedule_baseline_tasks_item"),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_schedule_baseline_tasks_project_task",
        ),
        Index("ix_schedule_baseline_tasks_baseline", "baseline_id"),
    )
    baseline_id: Mapped[UUID] = mapped_column(
        ForeignKey("schedule_baselines.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class ScheduleBaselineMilestone(UUIDTimestampMixin, Base):
    __tablename__ = "schedule_baseline_milestones"
    __table_args__ = (
        UniqueConstraint(
            "baseline_id", "milestone_id", name="uq_schedule_baseline_milestones_item"
        ),
        ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_schedule_baseline_milestones_project_milestone",
        ),
        Index("ix_schedule_baseline_milestones_baseline", "baseline_id"),
    )
    baseline_id: Mapped[UUID] = mapped_column(
        ForeignKey("schedule_baselines.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    milestone_id: Mapped[UUID] = mapped_column(nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
