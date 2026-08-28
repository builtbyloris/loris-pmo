from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class MilestoneStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    AT_RISK = "AT_RISK"
    COMPLETED = "COMPLETED"


milestone_status_enum = Enum(
    MilestoneStatus,
    name="milestone_status",
    native_enum=False,
    create_constraint=True,
)


class Milestone(UUIDTimestampMixin, Base):
    __tablename__ = "milestones"
    __table_args__ = (
        Index("ix_milestones_project_due_date", "project_id", "due_date"),
        UniqueConstraint("project_id", "id", name="uq_milestones_project_id_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[MilestoneStatus] = mapped_column(
        milestone_status_enum, default=MilestoneStatus.NOT_STARTED, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="milestones")  # noqa: F821
