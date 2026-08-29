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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class RiskStatus(StrEnum):
    IDENTIFIED = "IDENTIFIED"
    MONITORING = "MONITORING"
    MITIGATING = "MITIGATING"
    OCCURRED = "OCCURRED"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"


class IssueStatus(StrEnum):
    OPEN = "OPEN"
    IN_ANALYSIS = "IN_ANALYSIS"
    ACTION_PLANNED = "ACTION_PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ChangeStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"
    CANCELLED = "CANCELLED"


class ControlPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ImpactLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


risk_status_enum = Enum(RiskStatus, name="risk_status", native_enum=False, create_constraint=True)
issue_status_enum = Enum(
    IssueStatus, name="issue_status", native_enum=False, create_constraint=True
)
issue_priority_enum = Enum(
    ControlPriority, name="issue_priority", native_enum=False, create_constraint=True
)
change_status_enum = Enum(
    ChangeStatus, name="change_status", native_enum=False, create_constraint=True
)


class Risk(UUIDTimestampMixin, Base):
    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint("probability >= 1 AND probability <= 5", name="risk_probability_valid"),
        CheckConstraint("impact >= 1 AND impact <= 5", name="risk_impact_valid"),
        UniqueConstraint("project_id", "id", name="uq_risks_project_id"),
        ForeignKeyConstraint(
            ["project_id", "owner_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="RESTRICT",
            name="fk_risks_project_owner_member",
        ),
        Index("ix_risks_project_status", "project_id", "status"),
        Index("ix_risks_project_matrix", "project_id", "probability", "impact"),
        Index("ix_risks_project_review_date", "project_id", "review_date"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    probability: Mapped[int] = mapped_column(Integer, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_member_id: Mapped[UUID | None] = mapped_column(nullable=True)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    contingency: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RiskStatus] = mapped_column(
        risk_status_enum, default=RiskStatus.IDENTIFIED, nullable=False
    )
    identified_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    task_links: Mapped[list["RiskTaskLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    milestone_links: Mapped[list["RiskMilestoneLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class Issue(UUIDTimestampMixin, Base):
    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint(
            "estimated_delay_days IS NULL OR estimated_delay_days >= 0",
            name="issue_estimated_delay_nonnegative",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="issue_estimated_cost_nonnegative",
        ),
        CheckConstraint(
            "actual_delay_days IS NULL OR actual_delay_days >= 0",
            name="issue_actual_delay_nonnegative",
        ),
        CheckConstraint(
            "actual_cost IS NULL OR actual_cost >= 0",
            name="issue_actual_cost_nonnegative",
        ),
        UniqueConstraint("project_id", "id", name="uq_issues_project_id"),
        ForeignKeyConstraint(
            ["project_id", "owner_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="RESTRICT",
            name="fk_issues_project_owner_member",
        ),
        Index("ix_issues_project_status", "project_id", "status"),
        Index("ix_issues_project_priority", "project_id", "priority"),
        Index("ix_issues_project_identified_date", "project_id", "identified_date"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    priority: Mapped[ControlPriority] = mapped_column(
        issue_priority_enum, default=ControlPriority.MEDIUM, nullable=False
    )
    status: Mapped[IssueStatus] = mapped_column(
        issue_status_enum, default=IssueStatus.OPEN, nullable=False
    )
    owner_member_id: Mapped[UUID | None] = mapped_column(nullable=True)
    identified_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    schedule_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="issue_schedule_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    budget_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="issue_budget_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    scope_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="issue_scope_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    quality_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="issue_quality_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    estimated_delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    actual_delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task_links: Mapped[list["IssueTaskLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    milestone_links: Mapped[list["IssueMilestoneLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class ChangeRequest(UUIDTimestampMixin, Base):
    __tablename__ = "change_requests"
    __table_args__ = (
        CheckConstraint(
            "estimated_delay_days IS NULL OR estimated_delay_days >= 0",
            name="change_estimated_delay_nonnegative",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="change_estimated_cost_nonnegative",
        ),
        UniqueConstraint("project_id", "id", name="uq_change_requests_project_id"),
        Index("ix_change_requests_project_status", "project_id", "status"),
        Index("ix_change_requests_project_requested_date", "project_id", "requested_date"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requested_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    status: Mapped[ChangeStatus] = mapped_column(
        change_status_enum, default=ChangeStatus.DRAFT, nullable=False
    )
    scope_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="change_scope_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    schedule_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="change_schedule_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    budget_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="change_budget_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    resource_impact: Mapped[ImpactLevel] = mapped_column(
        Enum(ImpactLevel, name="change_resource_impact", native_enum=False, create_constraint=True),
        default=ImpactLevel.NONE,
        nullable=False,
    )
    estimated_delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    task_links: Mapped[list["ChangeRequestTaskLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    milestone_links: Mapped[list["ChangeRequestMilestoneLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    issue_links: Mapped[list["ChangeRequestIssueLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    risk_links: Mapped[list["ChangeRequestRiskLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class RiskTaskLink(Base):
    __tablename__ = "risk_task_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "risk_id"],
            ["risks.project_id", "risks.id"],
            ondelete="CASCADE",
            name="fk_risk_task_links_project_risk",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_risk_task_links_project_task",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    risk_id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[UUID] = mapped_column(primary_key=True)


class RiskMilestoneLink(Base):
    __tablename__ = "risk_milestone_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "risk_id"],
            ["risks.project_id", "risks.id"],
            ondelete="CASCADE",
            name="fk_risk_milestone_links_project_risk",
        ),
        ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            ondelete="CASCADE",
            name="fk_risk_milestone_links_project_milestone",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    risk_id: Mapped[UUID] = mapped_column(primary_key=True)
    milestone_id: Mapped[UUID] = mapped_column(primary_key=True)


class IssueTaskLink(Base):
    __tablename__ = "issue_task_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "issue_id"],
            ["issues.project_id", "issues.id"],
            ondelete="CASCADE",
            name="fk_issue_task_links_project_issue",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_issue_task_links_project_task",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    issue_id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[UUID] = mapped_column(primary_key=True)


class IssueMilestoneLink(Base):
    __tablename__ = "issue_milestone_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "issue_id"],
            ["issues.project_id", "issues.id"],
            ondelete="CASCADE",
            name="fk_issue_milestone_links_project_issue",
        ),
        ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            ondelete="CASCADE",
            name="fk_issue_milestone_links_project_milestone",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    issue_id: Mapped[UUID] = mapped_column(primary_key=True)
    milestone_id: Mapped[UUID] = mapped_column(primary_key=True)


class ChangeRequestTaskLink(Base):
    __tablename__ = "change_request_task_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            ondelete="CASCADE",
            name="fk_change_request_task_links_project_change",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_change_request_task_links_project_task",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    change_request_id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[UUID] = mapped_column(primary_key=True)


class ChangeRequestMilestoneLink(Base):
    __tablename__ = "change_request_milestone_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            ondelete="CASCADE",
            name="fk_change_request_milestone_links_project_change",
        ),
        ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            ondelete="CASCADE",
            name="fk_change_request_milestone_links_project_milestone",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    change_request_id: Mapped[UUID] = mapped_column(primary_key=True)
    milestone_id: Mapped[UUID] = mapped_column(primary_key=True)


class ChangeRequestIssueLink(Base):
    __tablename__ = "change_request_issue_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            ondelete="CASCADE",
            name="fk_change_request_issue_links_project_change",
        ),
        ForeignKeyConstraint(
            ["project_id", "issue_id"],
            ["issues.project_id", "issues.id"],
            ondelete="CASCADE",
            name="fk_change_request_issue_links_project_issue",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    change_request_id: Mapped[UUID] = mapped_column(primary_key=True)
    issue_id: Mapped[UUID] = mapped_column(primary_key=True)


class ChangeRequestRiskLink(Base):
    __tablename__ = "change_request_risk_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            ondelete="CASCADE",
            name="fk_change_request_risk_links_project_change",
        ),
        ForeignKeyConstraint(
            ["project_id", "risk_id"],
            ["risks.project_id", "risks.id"],
            ondelete="CASCADE",
            name="fk_change_request_risk_links_project_risk",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    change_request_id: Mapped[UUID] = mapped_column(primary_key=True)
    risk_id: Mapped[UUID] = mapped_column(primary_key=True)
