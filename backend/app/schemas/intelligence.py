from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.intelligence import AlertSeverity, AlertStatus, HealthStatus


class KPIValue(BaseModel):
    key: str
    value: int | float | str | None
    unit: str | None = None
    status: str
    available: bool = True
    reason: str | None = None


class HealthDriver(BaseModel):
    key: str
    severity: AlertSeverity
    evidence: dict[str, Any]


class HealthDimension(BaseModel):
    key: str
    score: int | None
    status: HealthStatus | None
    available: bool
    reason: str | None = None
    weight: int
    effective_weight: float
    evidence: dict[str, Any]


class HealthHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    score: int
    status: HealthStatus
    trigger: str
    created_at: datetime


class HealthRead(BaseModel):
    score: int | None
    status: HealthStatus | None
    dimensions: list[HealthDimension]
    drivers: list[HealthDriver]
    calculated_at: datetime
    history: list[HealthHistoryItem] = Field(default_factory=list)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    rule_type: str
    severity: AlertSeverity
    title_key: str
    reason_key: str
    evidence: dict[str, Any]
    related_entity_type: str | None
    related_entity_id: UUID | None
    status: AlertStatus
    first_detected_at: datetime
    last_detected_at: datetime
    acknowledged_at: datetime | None
    read_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutomationRuleRead(BaseModel):
    key: str
    trigger: str
    conditions: list[str]
    actions: list[str]
    enabled: bool


class IntelligenceRead(BaseModel):
    project_id: UUID
    kpis: list[KPIValue]
    health: HealthRead
    alerts: list[AlertRead]
    automation_rules: list[AutomationRuleRead]


class PortfolioProjectIntelligence(BaseModel):
    project_id: UUID
    project_name: str
    project_code: str
    health_score: int | None
    health_status: HealthStatus | None
    overdue_tasks: int
    high_critical_risks: int
    critical_issues: int
    budget_status: str
    active_alerts: int


class PortfolioIntelligence(BaseModel):
    healthy_projects: int
    watch_projects: int
    at_risk_projects: int
    critical_projects: int
    active_critical_alerts: int
    total_overdue_tasks: int
    total_high_critical_risks: int
    projects: list[PortfolioProjectIntelligence]
