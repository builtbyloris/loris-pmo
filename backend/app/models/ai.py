from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDTimestampMixin


class AIInsightSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AIInsightStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


class AIRecommendationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IGNORED = "IGNORED"
    EXPIRED = "EXPIRED"


insight_severity_enum = Enum(
    AIInsightSeverity, name="ai_insight_severity", native_enum=False, create_constraint=True
)
insight_status_enum = Enum(
    AIInsightStatus, name="ai_insight_status", native_enum=False, create_constraint=True
)
recommendation_status_enum = Enum(
    AIRecommendationStatus,
    name="ai_recommendation_status",
    native_enum=False,
    create_constraint=True,
)


class AIInsight(UUIDTimestampMixin, Base):
    __tablename__ = "ai_insights"
    __table_args__ = (
        UniqueConstraint("project_id", "fingerprint", name="uq_ai_insights_project_fingerprint"),
        Index("ix_ai_insights_project_status", "project_id", "status"),
        Index("ix_ai_insights_project_generated", "project_id", "generated_at"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ai_insight_confidence"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AIInsightSeverity] = mapped_column(insight_severity_enum, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    signal_key: Mapped[str] = mapped_column(String(220), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AIInsightStatus] = mapped_column(
        insight_status_enum, default=AIInsightStatus.ACTIVE, nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIRecommendation(UUIDTimestampMixin, Base):
    __tablename__ = "ai_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "fingerprint", name="uq_ai_recommendations_project_fingerprint"
        ),
        Index("ix_ai_recommendations_project_status", "project_id", "status"),
        Index("ix_ai_recommendations_project_generated", "project_id", "generated_at"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ai_recommendation_confidence"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    insight_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_insights.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    signal_key: Mapped[str] = mapped_column(String(220), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AIRecommendationStatus] = mapped_column(
        recommendation_status_enum, default=AIRecommendationStatus.PENDING, nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)


class AIAnalysisState(UUIDTimestampMixin, Base):
    __tablename__ = "ai_analysis_states"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_ai_analysis_states_project"),
        Index("ix_ai_analysis_states_analyzed", "analyzed_at"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    signal_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(160))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
