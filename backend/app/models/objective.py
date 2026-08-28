from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ObjectiveStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    ACHIEVED = "ACHIEVED"
    CANCELLED = "CANCELLED"


objective_status_enum = Enum(
    ObjectiveStatus, name="objective_status", native_enum=False, create_constraint=True
)


class Objective(UUIDTimestampMixin, Base):
    __tablename__ = "objectives"
    __table_args__ = (
        Index("ix_objectives_project_status", "project_id", "status"),
        UniqueConstraint("project_id", "id", name="uq_objectives_project_id_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ObjectiveStatus] = mapped_column(
        objective_status_enum, default=ObjectiveStatus.NOT_STARTED, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="objectives")  # noqa: F821
