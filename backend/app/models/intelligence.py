from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDTimestampMixin


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


health_status_enum = Enum(
    HealthStatus, name="health_status", native_enum=False, create_constraint=True
)
alert_severity_enum = Enum(
    AlertSeverity, name="alert_severity", native_enum=False, create_constraint=True
)
alert_status_enum = Enum(
    AlertStatus, name="alert_status", native_enum=False, create_constraint=True
)


class HealthSnapshot(UUIDTimestampMixin, Base):
    __tablename__ = "health_snapshots"
    __table_args__ = (Index("ix_health_snapshots_project_created", "project_id", "created_at"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[HealthStatus] = mapped_column(health_status_enum, nullable=False)
    dimensions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    drivers: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    trigger: Mapped[str] = mapped_column(String(80), nullable=False)


class Alert(UUIDTimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("project_id", "condition_key", name="uq_alerts_project_condition"),
        Index("ix_alerts_project_status", "project_id", "status"),
        Index("ix_alerts_project_severity", "project_id", "severity"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(80), nullable=False)
    condition_key: Mapped[str] = mapped_column(String(180), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(alert_severity_enum, nullable=False)
    title_key: Mapped[str] = mapped_column(String(160), nullable=False)
    reason_key: Mapped[str] = mapped_column(String(160), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    status: Mapped[AlertStatus] = mapped_column(
        alert_status_enum, default=AlertStatus.ACTIVE, nullable=False
    )
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
