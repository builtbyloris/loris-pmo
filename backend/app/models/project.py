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
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ProjectStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ProjectPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


status_enum = Enum(ProjectStatus, name="project_status", native_enum=False, create_constraint=True)
priority_enum = Enum(
    ProjectPriority, name="project_priority", native_enum=False, create_constraint=True
)


class Project(UUIDTimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "target_end_date IS NULL OR start_date IS NULL OR target_end_date >= start_date",
            name="project_dates_valid",
        ),
        CheckConstraint("planned_budget >= 0", name="project_budget_nonnegative"),
        UniqueConstraint("owner_user_id", "code", name="uq_projects_owner_code"),
        Index("ix_projects_owner_archived", "owner_user_id", "archived_at"),
        Index("ix_projects_owner_status", "owner_user_id", "status"),
    )

    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_or_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        status_enum, default=ProjectStatus.NOT_STARTED, nullable=False
    )
    priority: Mapped[ProjectPriority] = mapped_column(
        priority_enum, default=ProjectPriority.MEDIUM, nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_budget: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    objectives: Mapped[list["Objective"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    success_criteria: Mapped[list["SuccessCriterion"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    milestones: Mapped[list["Milestone"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
