from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.analytics.control import RiskSeverity
from app.models.control import (
    ChangeStatus,
    ControlPriority,
    ImpactLevel,
    IssueStatus,
    RiskStatus,
)


def _required_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


def _unique_ids(values: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(values))


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=160)
    probability: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    owner_member_id: UUID | None = None
    mitigation: str | None = Field(default=None, max_length=10000)
    contingency: str | None = Field(default=None, max_length=10000)
    status: RiskStatus = RiskStatus.IDENTIFIED
    identified_date: date
    review_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)
    task_ids: list[UUID] = Field(default_factory=list, max_length=100)
    milestone_ids: list[UUID] = Field(default_factory=list, max_length=100)

    _strip_title = field_validator("title")(_required_text)

    @model_validator(mode="after")
    def validate_dates_and_links(self) -> "RiskCreate":
        if self.review_date and self.review_date < self.identified_date:
            raise ValueError("review_date must not precede identified_date")
        self.task_ids = _unique_ids(self.task_ids)
        self.milestone_ids = _unique_ids(self.milestone_ids)
        return self


class RiskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=160)
    probability: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    owner_member_id: UUID | None = None
    mitigation: str | None = Field(default=None, max_length=10000)
    contingency: str | None = Field(default=None, max_length=10000)
    status: RiskStatus | None = None
    identified_date: date | None = None
    review_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)
    task_ids: list[UUID] | None = Field(default=None, max_length=100)
    milestone_ids: list[UUID] | None = Field(default=None, max_length=100)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "RiskUpdate":
        for field_name in ("title", "probability", "impact", "status", "identified_date"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.task_ids is not None:
            self.task_ids = _unique_ids(self.task_ids)
        if self.milestone_ids is not None:
            self.milestone_ids = _unique_ids(self.milestone_ids)
        return self


class RiskRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    category: str | None
    probability: int
    impact: int
    risk_score: int
    severity: RiskSeverity
    owner_member_id: UUID | None
    mitigation: str | None
    contingency: str | None
    status: RiskStatus
    identified_date: date
    review_date: date | None
    notes: str | None
    task_ids: list[UUID]
    milestone_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class RiskList(BaseModel):
    items: list[RiskRead]
    total: int = Field(ge=0)


class RiskSort(StrEnum):
    UPDATED_AT = "updated_at"
    TITLE = "title"
    SCORE = "score"
    PROBABILITY = "probability"
    IMPACT = "impact"
    REVIEW_DATE = "review_date"


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=160)
    priority: ControlPriority = ControlPriority.MEDIUM
    owner_member_id: UUID | None = None
    identified_date: date
    schedule_impact: ImpactLevel = ImpactLevel.NONE
    budget_impact: ImpactLevel = ImpactLevel.NONE
    scope_impact: ImpactLevel = ImpactLevel.NONE
    quality_impact: ImpactLevel = ImpactLevel.NONE
    estimated_delay_days: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)
    task_ids: list[UUID] = Field(default_factory=list, max_length=100)
    milestone_ids: list[UUID] = Field(default_factory=list, max_length=100)

    _strip_title = field_validator("title")(_required_text)

    @model_validator(mode="after")
    def normalize_links(self) -> "IssueCreate":
        self.task_ids = _unique_ids(self.task_ids)
        self.milestone_ids = _unique_ids(self.milestone_ids)
        return self


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=160)
    priority: ControlPriority | None = None
    status: IssueStatus | None = None
    owner_member_id: UUID | None = None
    identified_date: date | None = None
    schedule_impact: ImpactLevel | None = None
    budget_impact: ImpactLevel | None = None
    scope_impact: ImpactLevel | None = None
    quality_impact: ImpactLevel | None = None
    estimated_delay_days: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    actual_delay_days: int | None = Field(default=None, ge=0)
    actual_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    resolution: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=10000)
    task_ids: list[UUID] | None = Field(default=None, max_length=100)
    milestone_ids: list[UUID] | None = Field(default=None, max_length=100)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "IssueUpdate":
        for field_name in (
            "title",
            "priority",
            "status",
            "identified_date",
            "schedule_impact",
            "budget_impact",
            "scope_impact",
            "quality_impact",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.task_ids is not None:
            self.task_ids = _unique_ids(self.task_ids)
        if self.milestone_ids is not None:
            self.milestone_ids = _unique_ids(self.milestone_ids)
        return self


class IssueResolution(BaseModel):
    resolution: str = Field(min_length=1, max_length=10000)
    actual_delay_days: int | None = Field(default=None, ge=0)
    actual_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    _strip_resolution = field_validator("resolution")(_required_text)


class IssueRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    category: str | None
    priority: ControlPriority
    status: IssueStatus
    owner_member_id: UUID | None
    identified_date: date
    schedule_impact: ImpactLevel
    budget_impact: ImpactLevel
    scope_impact: ImpactLevel
    quality_impact: ImpactLevel
    estimated_delay_days: int | None
    estimated_cost: Decimal | None
    actual_delay_days: int | None
    actual_cost: Decimal | None
    resolution: str | None
    notes: str | None
    resolved_at: datetime | None
    task_ids: list[UUID]
    milestone_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class IssueList(BaseModel):
    items: list[IssueRead]
    total: int = Field(ge=0)


class IssueSort(StrEnum):
    UPDATED_AT = "updated_at"
    TITLE = "title"
    IDENTIFIED_DATE = "identified_date"
    PRIORITY = "priority"
    STATUS = "status"


class ChangeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    reason: str | None = Field(default=None, max_length=10000)
    requested_by: str | None = Field(default=None, max_length=200)
    requested_date: date
    scope_impact: ImpactLevel = ImpactLevel.NONE
    schedule_impact: ImpactLevel = ImpactLevel.NONE
    budget_impact: ImpactLevel = ImpactLevel.NONE
    resource_impact: ImpactLevel = ImpactLevel.NONE
    estimated_delay_days: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)
    task_ids: list[UUID] = Field(default_factory=list, max_length=100)
    milestone_ids: list[UUID] = Field(default_factory=list, max_length=100)
    issue_ids: list[UUID] = Field(default_factory=list, max_length=100)
    risk_ids: list[UUID] = Field(default_factory=list, max_length=100)

    _strip_title = field_validator("title")(_required_text)

    @model_validator(mode="after")
    def normalize_links(self) -> "ChangeCreate":
        self.task_ids = _unique_ids(self.task_ids)
        self.milestone_ids = _unique_ids(self.milestone_ids)
        self.issue_ids = _unique_ids(self.issue_ids)
        self.risk_ids = _unique_ids(self.risk_ids)
        return self


class ChangeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    reason: str | None = Field(default=None, max_length=10000)
    requested_by: str | None = Field(default=None, max_length=200)
    requested_date: date | None = None
    scope_impact: ImpactLevel | None = None
    schedule_impact: ImpactLevel | None = None
    budget_impact: ImpactLevel | None = None
    resource_impact: ImpactLevel | None = None
    estimated_delay_days: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)
    task_ids: list[UUID] | None = Field(default=None, max_length=100)
    milestone_ids: list[UUID] | None = Field(default=None, max_length=100)
    issue_ids: list[UUID] | None = Field(default=None, max_length=100)
    risk_ids: list[UUID] | None = Field(default=None, max_length=100)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "ChangeUpdate":
        for field_name in (
            "title",
            "requested_date",
            "scope_impact",
            "schedule_impact",
            "budget_impact",
            "resource_impact",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        for field_name in ("task_ids", "milestone_ids", "issue_ids", "risk_ids"):
            values = getattr(self, field_name)
            if values is not None:
                setattr(self, field_name, _unique_ids(values))
        return self


class ChangeDecision(BaseModel):
    decision: str = Field(min_length=1, max_length=10000)

    _strip_decision = field_validator("decision")(_required_text)


class ChangeRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    reason: str | None
    requested_by: str | None
    requested_date: date
    status: ChangeStatus
    scope_impact: ImpactLevel
    schedule_impact: ImpactLevel
    budget_impact: ImpactLevel
    resource_impact: ImpactLevel
    estimated_delay_days: int | None
    estimated_cost: Decimal | None
    decision: str | None
    decision_date: date | None
    notes: str | None
    task_ids: list[UUID]
    milestone_ids: list[UUID]
    issue_ids: list[UUID]
    risk_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class ChangeList(BaseModel):
    items: list[ChangeRead]
    total: int = Field(ge=0)


class ChangeSort(StrEnum):
    UPDATED_AT = "updated_at"
    TITLE = "title"
    REQUESTED_DATE = "requested_date"
    STATUS = "status"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class ControlSummary(BaseModel):
    open_risks: int = Field(ge=0)
    high_critical_risks: int = Field(ge=0)
    open_issues: int = Field(ge=0)
    critical_issues: int = Field(ge=0)
    pending_changes: int = Field(ge=0)
