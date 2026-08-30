from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
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


class AIBriefingKind(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class AIScenarioType(StrEnum):
    TASK_DELAY = "TASK_DELAY"
    MILESTONE_DELAY = "MILESTONE_DELAY"
    COST_INCREASE = "COST_INCREASE"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    RISK_OCCURS = "RISK_OCCURS"


class MeetingAIProposalKind(StrEnum):
    ACTION_ITEM = "ACTION_ITEM"
    DECISION = "DECISION"
    RISK = "RISK"
    ISSUE = "ISSUE"


class MeetingAIProposalStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


briefing_kind_enum = Enum(
    AIBriefingKind, name="ai_briefing_kind", native_enum=False, create_constraint=True
)
scenario_type_enum = Enum(
    AIScenarioType, name="ai_scenario_type", native_enum=False, create_constraint=True
)
meeting_proposal_kind_enum = Enum(
    MeetingAIProposalKind,
    name="meeting_ai_proposal_kind",
    native_enum=False,
    create_constraint=True,
)
meeting_proposal_status_enum = Enum(
    MeetingAIProposalStatus,
    name="meeting_ai_proposal_status",
    native_enum=False,
    create_constraint=True,
)


class AIBriefing(UUIDTimestampMixin, Base):
    __tablename__ = "ai_briefings"
    __table_args__ = (
        Index("ix_ai_briefings_project_kind_generated", "project_id", "kind", "generated_at"),
        Index("ix_ai_briefings_project_fingerprint", "project_id", "fingerprint"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[AIBriefingKind] = mapped_column(briefing_kind_enum, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(160))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIScenario(UUIDTimestampMixin, Base):
    __tablename__ = "ai_scenarios"
    __table_args__ = (
        Index("ix_ai_scenarios_project_created", "project_id", "created_at"),
        Index("ix_ai_scenarios_project_type", "project_id", "type"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[AIScenarioType] = mapped_column(scenario_type_enum, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    deterministic_impact: Mapped[dict] = mapped_column(JSON, nullable=False)
    interpretation: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)


class MeetingAIAnalysis(UUIDTimestampMixin, Base):
    __tablename__ = "meeting_ai_analyses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="CASCADE",
            name="fk_meeting_ai_analyses_project_meeting",
        ),
        Index("ix_meeting_ai_analyses_meeting_generated", "meeting_id", "generated_at"),
        Index("ix_meeting_ai_analyses_fingerprint", "project_id", "fingerprint"),
    )

    project_id: Mapped[UUID] = mapped_column(nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposals: Mapped[list["MeetingAIProposal"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class MeetingAIProposal(UUIDTimestampMixin, Base):
    __tablename__ = "meeting_ai_proposals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="CASCADE",
            name="fk_meeting_ai_proposals_project_meeting",
        ),
        UniqueConstraint("analysis_id", "proposal_key", name="uq_meeting_ai_proposal_key"),
        Index("ix_meeting_ai_proposals_meeting_status", "meeting_id", "status"),
    )

    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("meeting_ai_analyses.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(nullable=False)
    proposal_key: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[MeetingAIProposalKind] = mapped_column(meeting_proposal_kind_enum, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    status: Mapped[MeetingAIProposalStatus] = mapped_column(
        meeting_proposal_status_enum,
        default=MeetingAIProposalStatus.PENDING,
        nullable=False,
    )
    confirmed_entity_type: Mapped[str | None] = mapped_column(String(80))
    confirmed_entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
