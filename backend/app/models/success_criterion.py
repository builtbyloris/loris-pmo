from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, ForeignKeyConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class SuccessCriterionStatus(StrEnum):
    NOT_MET = "NOT_MET"
    MET = "MET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


criterion_status_enum = Enum(
    SuccessCriterionStatus,
    name="success_criterion_status",
    native_enum=False,
    create_constraint=True,
)


class SuccessCriterion(UUIDTimestampMixin, Base):
    __tablename__ = "success_criteria"
    __table_args__ = (
        Index("ix_success_criteria_project_status", "project_id", "status"),
        ForeignKeyConstraint(
            ["project_id", "objective_id"],
            ["objectives.project_id", "objectives.id"],
            name="fk_success_criteria_project_objective",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[UUID | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[str | None] = mapped_column(String(240), nullable=True)
    status: Mapped[SuccessCriterionStatus] = mapped_column(
        criterion_status_enum, default=SuccessCriterionStatus.NOT_MET, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="success_criteria")  # noqa: F821
