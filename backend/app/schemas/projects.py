import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.objective import ObjectiveStatus
from app.models.project import ProjectPriority, ProjectStatus
from app.models.success_criterion import SuccessCriterionStatus

PROJECT_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,31}$")


def _required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be empty")
    return stripped


class ObjectiveCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=5000)
    status: ObjectiveStatus = ObjectiveStatus.NOT_STARTED

    _strip_title = field_validator("title")(_required_text)


class ObjectiveUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=5000)
    status: ObjectiveStatus | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "ObjectiveUpdate":
        for field_name in ("title", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ObjectiveRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: ObjectiveStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessCriterionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    objective_id: UUID | None = None
    target_value: str | None = Field(default=None, max_length=240)
    status: SuccessCriterionStatus = SuccessCriterionStatus.NOT_MET

    _strip_description = field_validator("description")(_required_text)


class SuccessCriterionUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    objective_id: UUID | None = None
    target_value: str | None = Field(default=None, max_length=240)
    status: SuccessCriterionStatus | None = None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "SuccessCriterionUpdate":
        for field_name in ("description", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class SuccessCriterionRead(BaseModel):
    id: UUID
    project_id: UUID
    objective_id: UUID | None
    description: str
    target_value: str | None
    status: SuccessCriterionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=2, max_length=32)
    description: str | None = Field(default=None, max_length=10000)
    client_or_area: str | None = Field(default=None, max_length=200)
    status: ProjectStatus = ProjectStatus.NOT_STARTED
    priority: ProjectPriority = ProjectPriority.MEDIUM
    start_date: date | None = None
    target_end_date: date | None = None
    planned_budget: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)
    objectives: list[ObjectiveCreate] = Field(default_factory=list, max_length=50)
    success_criteria: list[SuccessCriterionCreate] = Field(default_factory=list, max_length=100)

    _strip_name = field_validator("name")(_required_text)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not PROJECT_CODE_PATTERN.fullmatch(normalized):
            raise ValueError("must use 2-32 letters, numbers, dots, underscores, or hyphens")
        return normalized

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "ProjectCreate":
        if self.start_date and self.target_end_date and self.target_end_date < self.start_date:
            raise ValueError("target_end_date must not precede start_date")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=2, max_length=32)
    description: str | None = Field(default=None, max_length=10000)
    client_or_area: str | None = Field(default=None, max_length=200)
    status: ProjectStatus | None = None
    priority: ProjectPriority | None = None
    start_date: date | None = None
    target_end_date: date | None = None
    planned_budget: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not PROJECT_CODE_PATTERN.fullmatch(normalized):
            raise ValueError("must use 2-32 letters, numbers, dots, underscores, or hyphens")
        return normalized

    @model_validator(mode="after")
    def dates_are_ordered_when_both_present(self) -> "ProjectUpdate":
        if self.start_date and self.target_end_date and self.target_end_date < self.start_date:
            raise ValueError("target_end_date must not precede start_date")
        return self

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "ProjectUpdate":
        for field_name in ("name", "code", "status", "priority", "planned_budget"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProjectRead(BaseModel):
    id: UUID
    name: str
    code: str
    description: str | None
    client_or_area: str | None
    status: ProjectStatus
    priority: ProjectPriority
    start_date: date | None
    target_end_date: date | None
    planned_budget: Decimal | None
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(ProjectRead):
    objectives: list[ObjectiveRead]
    success_criteria: list[SuccessCriterionRead]


class ProjectList(BaseModel):
    items: list[ProjectRead]
    total: int = Field(ge=0)


class ProjectSort(StrEnum):
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"
    NAME = "name"
    START_DATE = "start_date"
    TARGET_END_DATE = "target_end_date"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PortfolioSummary(BaseModel):
    total_projects: int = Field(ge=0)
    active_projects: int = Field(ge=0)
    on_hold_projects: int = Field(ge=0)
    completed_projects: int = Field(ge=0)
