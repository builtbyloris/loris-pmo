from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.people import ProjectRole, StakeholderLevel


def _clean(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    department: str | None = Field(default=None, max_length=160)
    skills: list[str] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=10000)

    _strip_name = field_validator("name")(_clean)

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    department: str | None = Field(default=None, max_length=160)
    skills: list[str] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> "PersonUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class PersonRead(BaseModel):
    id: UUID
    name: str
    email: EmailStr | None
    department: str | None
    skills: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberCreate(BaseModel):
    person_id: UUID
    role: ProjectRole = ProjectRole.TEAM_MEMBER
    responsibilities: str | None = Field(default=None, max_length=10000)
    availability_percent: int = Field(default=100, ge=0, le=100)


class MemberUpdate(BaseModel):
    role: ProjectRole | None = None
    responsibilities: str | None = Field(default=None, max_length=10000)
    availability_percent: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def required_values_cannot_be_null(self) -> "MemberUpdate":
        for field_name in ("role", "availability_percent"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class MemberRead(BaseModel):
    id: UUID
    project_id: UUID
    person_id: UUID
    role: ProjectRole
    responsibilities: str | None
    availability_percent: int
    person: PersonRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StakeholderCreate(BaseModel):
    person_id: UUID | None = None
    name: str | None = Field(default=None, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    influence: StakeholderLevel = StakeholderLevel.MEDIUM
    interest: StakeholderLevel = StakeholderLevel.MEDIUM
    communication_frequency: str | None = Field(default=None, max_length=160)
    communication_channel: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def identity_is_required(self) -> "StakeholderCreate":
        if self.person_id is None and not (self.name and self.name.strip()):
            raise ValueError("name is required when no person is linked")
        if self.name is not None:
            self.name = self.name.strip() or None
        return self


class StakeholderUpdate(BaseModel):
    person_id: UUID | None = None
    name: str | None = Field(default=None, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    influence: StakeholderLevel | None = None
    interest: StakeholderLevel | None = None
    communication_frequency: str | None = Field(default=None, max_length=160)
    communication_channel: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def required_values_cannot_be_null(self) -> "StakeholderUpdate":
        for field_name in ("influence", "interest"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class StakeholderRead(BaseModel):
    id: UUID
    project_id: UUID
    person_id: UUID | None
    name: str | None
    display_name: str
    organization: str | None
    role: str | None
    influence: StakeholderLevel
    interest: StakeholderLevel
    communication_frequency: str | None
    communication_channel: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class WorkloadStatus(StrEnum):
    NO_DATA = "NO_DATA"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MemberWorkload(BaseModel):
    member_id: UUID
    person_id: UUID
    name: str
    role: ProjectRole
    availability_percent: int
    active_task_count: int = Field(ge=0)
    overdue_task_count: int = Field(ge=0)
    due_soon_task_count: int = Field(ge=0)
    estimated_effort: Decimal
    actual_effort: Decimal
    effort_data_complete: bool
    workload_status: WorkloadStatus


class PeopleSummary(BaseModel):
    team_size: int = Field(ge=0)
    stakeholder_count: int = Field(ge=0)
    workload_warning_count: int = Field(ge=0)
