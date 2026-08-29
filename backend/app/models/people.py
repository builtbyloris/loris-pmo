from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ProjectRole(StrEnum):
    PROJECT_MANAGER = "PROJECT_MANAGER"
    SPONSOR = "SPONSOR"
    PRODUCT_OWNER = "PRODUCT_OWNER"
    TEAM_MEMBER = "TEAM_MEMBER"
    DEVELOPER = "DEVELOPER"
    DESIGNER = "DESIGNER"
    DATA_ANALYST = "DATA_ANALYST"
    QA_TESTER = "QA_TESTER"
    STAKEHOLDER = "STAKEHOLDER"
    OTHER = "OTHER"


class StakeholderLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


project_role_enum = Enum(
    ProjectRole, name="project_role", native_enum=False, create_constraint=True
)
stakeholder_influence_enum = Enum(
    StakeholderLevel,
    name="stakeholder_influence",
    native_enum=False,
    create_constraint=True,
)
stakeholder_interest_enum = Enum(
    StakeholderLevel,
    name="stakeholder_interest",
    native_enum=False,
    create_constraint=True,
)


class Person(UUIDTimestampMixin, Base):
    __tablename__ = "people"
    __table_args__ = (
        Index("ix_people_owner_name", "owner_user_id", "name"),
        Index("ix_people_owner_email", "owner_user_id", "email"),
        UniqueConstraint("owner_user_id", "id", name="uq_people_owner_id"),
    )

    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    department: Mapped[str | None] = mapped_column(String(160), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="person", cascade="all, delete-orphan", passive_deletes=True
    )


class ProjectMember(UUIDTimestampMixin, Base):
    __tablename__ = "project_members"
    __table_args__ = (
        CheckConstraint(
            "availability_percent >= 0 AND availability_percent <= 100",
            name="project_member_availability_valid",
        ),
        UniqueConstraint("project_id", "person_id", name="uq_project_members_project_person"),
        UniqueConstraint("project_id", "id", name="uq_project_members_project_id"),
        Index("ix_project_members_project_role", "project_id", "role"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ProjectRole] = mapped_column(
        project_role_enum, default=ProjectRole.TEAM_MEMBER, nullable=False
    )
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    availability_percent: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    person: Mapped[Person] = relationship(back_populates="memberships")
    assignments: Mapped[list["TaskAssignee"]] = relationship(
        back_populates="project_member",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="assignees,task",
    )


class TaskAssignee(UUIDTimestampMixin, Base):
    __tablename__ = "task_assignees"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_task_assignees_project_task",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="CASCADE",
            name="fk_task_assignees_project_member",
        ),
        UniqueConstraint(
            "project_id",
            "task_id",
            "project_member_id",
            name="uq_task_assignees_task_member",
        ),
        Index("ix_task_assignees_member", "project_id", "project_member_id"),
    )

    project_id: Mapped[UUID] = mapped_column(nullable=False)
    task_id: Mapped[UUID] = mapped_column(nullable=False)
    project_member_id: Mapped[UUID] = mapped_column(nullable=False)

    task: Mapped["Task"] = relationship(  # noqa: F821
        back_populates="assignees", overlaps="assignments,project_member"
    )
    project_member: Mapped[ProjectMember] = relationship(
        back_populates="assignments", overlaps="assignees,task"
    )


class Stakeholder(UUIDTimestampMixin, Base):
    __tablename__ = "stakeholders"
    __table_args__ = (
        CheckConstraint(
            "person_id IS NOT NULL OR (name IS NOT NULL AND length(trim(name)) > 0)",
            name="stakeholder_identity_required",
        ),
        Index("ix_stakeholders_project_matrix", "project_id", "influence", "interest"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    influence: Mapped[StakeholderLevel] = mapped_column(
        stakeholder_influence_enum, default=StakeholderLevel.MEDIUM, nullable=False
    )
    interest: Mapped[StakeholderLevel] = mapped_column(
        stakeholder_interest_enum, default=StakeholderLevel.MEDIUM, nullable=False
    )
    communication_frequency: Mapped[str | None] = mapped_column(String(160), nullable=True)
    communication_channel: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped[Person | None] = relationship()
