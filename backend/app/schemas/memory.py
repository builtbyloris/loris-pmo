from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.memory import (
    ActionItemStatus,
    DecisionStatus,
    MeetingStatus,
    MemoryEntityType,
    MemorySource,
    ProjectLogType,
)


def _text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value cannot be blank")
    return value


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class EntityLink(BaseModel):
    entity_type: MemoryEntityType
    entity_id: UUID


class EntityLinkRead(EntityLink):
    entity_name: str | None = None


class ProjectLogCreate(BaseModel):
    type: ProjectLogType = ProjectLogType.NOTE
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    links: list[EntityLink] = Field(default_factory=list, max_length=100)

    _strip_title = field_validator("title")(_text)


class ProjectLogUpdate(BaseModel):
    type: ProjectLogType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    links: list[EntityLink] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_update(self) -> "ProjectLogUpdate":
        for field_name in ("type", "title"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.title is not None:
            self.title = _text(self.title)
        return self


class ProjectLogRead(BaseModel):
    id: UUID
    project_id: UUID
    type: ProjectLogType
    title: str
    description: str | None
    source: MemorySource
    created_by_user_id: UUID
    links: list[EntityLinkRead]
    created_at: datetime
    updated_at: datetime


class ProjectLogList(BaseModel):
    items: list[ProjectLogRead]
    total: int


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    agenda: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=20000)
    status: MeetingStatus = MeetingStatus.PLANNED
    participant_ids: list[UUID] = Field(default_factory=list, max_length=100)

    _strip_title = field_validator("title")(_text)

    @field_validator("scheduled_at")
    @classmethod
    def require_scheduled_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduled_at must include a timezone")
        return value


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    agenda: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=20000)
    status: MeetingStatus | None = None
    participant_ids: list[UUID] | None = Field(default=None, max_length=100)

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("scheduled_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_update(self) -> "MeetingUpdate":
        for field_name in ("title", "scheduled_at", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ActionItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=5000)
    owner_member_id: UUID | None = None
    due_date: date | None = None
    task_id: UUID | None = None

    _strip_description = field_validator("description")(_text)


class ActionItemUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    owner_member_id: UUID | None = None
    due_date: date | None = None
    task_id: UUID | None = None
    status: ActionItemStatus | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "ActionItemUpdate":
        for field_name in ("description", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ActionItemRead(BaseModel):
    id: UUID
    project_id: UUID
    meeting_id: UUID
    description: str
    owner_member_id: UUID | None
    due_date: date | None
    status: ActionItemStatus
    task_id: UUID | None
    created_at: datetime
    updated_at: datetime


class MeetingRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    scheduled_at: datetime
    duration_minutes: int | None
    agenda: str | None
    notes: str | None
    status: MeetingStatus
    participant_ids: list[UUID]
    action_items: list[ActionItemRead]
    created_at: datetime
    updated_at: datetime


class MeetingList(BaseModel):
    items: list[MeetingRead]
    total: int


class DecisionCreate(BaseModel):
    meeting_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    decision: str = Field(min_length=1, max_length=10000)
    decision_date: date
    decision_maker_member_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=10000)
    alternatives: str | None = Field(default=None, max_length=10000)
    selected_option: str | None = Field(default=None, max_length=10000)
    expected_impact: str | None = Field(default=None, max_length=10000)
    actual_impact: str | None = Field(default=None, max_length=10000)
    status: DecisionStatus = DecisionStatus.PROPOSED
    notes: str | None = Field(default=None, max_length=10000)
    links: list[EntityLink] = Field(default_factory=list, max_length=100)

    _strip_title = field_validator("title")(_text)
    _strip_decision = field_validator("decision")(_text)


class DecisionUpdate(BaseModel):
    meeting_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    decision: str | None = Field(default=None, min_length=1, max_length=10000)
    decision_date: date | None = None
    decision_maker_member_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=10000)
    alternatives: str | None = Field(default=None, max_length=10000)
    selected_option: str | None = Field(default=None, max_length=10000)
    expected_impact: str | None = Field(default=None, max_length=10000)
    actual_impact: str | None = Field(default=None, max_length=10000)
    status: DecisionStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)
    links: list[EntityLink] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_update(self) -> "DecisionUpdate":
        for field_name in ("title", "decision", "decision_date", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class DecisionRead(BaseModel):
    id: UUID
    project_id: UUID
    meeting_id: UUID | None
    title: str
    decision: str
    decision_date: date
    decision_maker_member_id: UUID | None
    reason: str | None
    alternatives: str | None
    selected_option: str | None
    expected_impact: str | None
    actual_impact: str | None
    status: DecisionStatus
    notes: str | None
    links: list[EntityLinkRead]
    created_at: datetime
    updated_at: datetime


class DecisionList(BaseModel):
    items: list[DecisionRead]
    total: int


class ActivityRead(BaseModel):
    id: UUID
    actor_user_id: UUID
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: UUID
    entity_name: str | None
    changes: dict | None
    created_at: datetime


class ActivityList(BaseModel):
    items: list[ActivityRead]
    total: int


class MemorySummaryItem(BaseModel):
    id: UUID
    title: str
    status: str | None = None
    occurred_at: datetime | date


class MemorySummary(BaseModel):
    recent_meetings: list[MemorySummaryItem]
    recent_decisions: list[MemorySummaryItem]
    recent_log_entries: list[MemorySummaryItem]
    pending_action_items: int
