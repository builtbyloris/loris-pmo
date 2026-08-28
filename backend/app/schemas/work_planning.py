from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.milestone import MilestoneStatus
from app.models.task import TaskPriority, TaskStatus
from app.models.task_dependency import DependencyType


def _required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be empty")
    return stripped


class TaskCreate(BaseModel):
    parent_task_id: UUID | None = None
    milestone_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    start_date: date | None = None
    due_date: date | None = None
    estimated_effort: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2
    )
    actual_effort: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    completion_percentage: int = Field(default=0, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=10000)

    _strip_title = field_validator("title")(_required_text)

    @model_validator(mode="after")
    def normalize_status_and_dates(self) -> "TaskCreate":
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValueError("due_date must not precede start_date")
        if self.status == TaskStatus.DONE:
            self.completion_percentage = 100
        return self


class TaskUpdate(BaseModel):
    parent_task_id: UUID | None = None
    milestone_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    start_date: date | None = None
    due_date: date | None = None
    estimated_effort: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    actual_effort: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    completion_percentage: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "TaskUpdate":
        for field_name in (
            "title",
            "status",
            "priority",
            "estimated_effort",
            "actual_effort",
            "completion_percentage",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValueError("due_date must not precede start_date")
        if self.status == TaskStatus.DONE:
            self.completion_percentage = 100
        return self


class TaskRead(BaseModel):
    id: UUID
    project_id: UUID
    parent_task_id: UUID | None
    milestone_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    start_date: date | None
    due_date: date | None
    estimated_effort: Decimal
    actual_effort: Decimal
    completion_percentage: int
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int = Field(ge=0)


class TaskSort(StrEnum):
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"
    TITLE = "title"
    START_DATE = "start_date"
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    STATUS = "status"


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    due_date: date | None = None
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    notes: str | None = Field(default=None, max_length=10000)

    _strip_title = field_validator("title")(_required_text)


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    due_date: date | None = None
    status: MilestoneStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "MilestoneUpdate":
        for field_name in ("title", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class MilestoneRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    due_date: date | None
    status: MilestoneStatus
    notes: str | None
    progress: float | None
    linked_task_count: int = Field(ge=0)
    completed_task_count: int = Field(ge=0)
    overdue_task_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class DependencyCreate(BaseModel):
    source_task_id: UUID
    target_task_id: UUID
    dependency_type: DependencyType


class DependencyRead(BaseModel):
    id: UUID
    project_id: UUID
    source_task_id: UUID
    target_task_id: UUID
    dependency_type: DependencyType
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkPlanningSummary(BaseModel):
    total_tasks: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)
    overdue_tasks: int = Field(ge=0)
    upcoming_milestones: int = Field(ge=0)
    progress: float | None
