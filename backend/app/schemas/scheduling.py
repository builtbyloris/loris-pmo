from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DeadlineStatus(StrEnum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    LATE = "LATE"
    UNAVAILABLE = "UNAVAILABLE"


class ScheduleDependency(BaseModel):
    predecessor_id: UUID
    successor_id: UUID
    type: Literal["FINISH_TO_START"] = "FINISH_TO_START"


class ScheduleTaskRead(BaseModel):
    id: UUID
    title: str
    start: date | None
    finish: date | None
    duration_days: int | None
    progress: int
    milestone_id: UUID | None
    dependencies: list[UUID]
    critical: bool | None
    earliest_start_offset: int | None
    earliest_finish_offset: int | None
    latest_start_offset: int | None
    latest_finish_offset: int | None
    total_float: int | None
    free_float: int | None
    baseline_start: date | None
    baseline_finish: date | None
    start_variance: int | None
    finish_variance: int | None
    warnings: list[str] = Field(default_factory=list)


class ScheduleMilestoneRead(BaseModel):
    id: UUID
    title: str
    current_date: date | None
    projected_date: date | None
    baseline_date: date | None
    variance_days: int | None
    status: DeadlineStatus
    affected_task_ids: list[UUID] = Field(default_factory=list)


class CriticalPathRead(BaseModel):
    complete: bool
    reasons: list[str]
    project_duration_days: int | None
    critical_task_ids: list[UUID]
    critical_sequences: list[list[UUID]]


class DeadlineImpactRead(BaseModel):
    projected_finish: date | None
    deadline: date | None
    variance_days: int | None
    status: DeadlineStatus


class ScheduleRead(BaseModel):
    project_id: UUID
    generated_at: datetime
    fingerprint: str
    calendar_model: Literal["CALENDAR_DAYS"] = "CALENDAR_DAYS"
    calculation_complete: bool
    scheduling_completeness_percent: float
    tasks: list[ScheduleTaskRead]
    milestones: list[ScheduleMilestoneRead]
    dependencies: list[ScheduleDependency]
    critical_path: CriticalPathRead
    deadline_impact: DeadlineImpactRead
    baseline_variance_days: int | None
    baseline_created_at: datetime | None


class BaselineCreate(BaseModel):
    replace: bool = False


class BaselineRead(BaseModel):
    id: UUID
    project_id: UUID
    target_end_date: date | None
    created_at: datetime
    updated_at: datetime
    task_count: int
    milestone_count: int


class ScheduleChangeRequest(BaseModel):
    entity_type: Literal["TASK", "MILESTONE"]
    task_id: UUID | None = None
    milestone_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None

    @model_validator(mode="after")
    def validate_change(self):
        if self.entity_type == "TASK":
            if not self.task_id or self.milestone_id or not self.start_date or not self.due_date:
                raise ValueError("A task change requires task_id, start_date, and due_date")
            if self.due_date < self.start_date:
                raise ValueError("due_date must not precede start_date")
        elif not self.milestone_id or self.task_id or not self.due_date:
            raise ValueError("A milestone change requires milestone_id and due_date")
        return self


class AffectedTaskRead(BaseModel):
    id: UUID
    title: str
    before_start: date | None
    before_finish: date | None
    projected_start: date
    projected_finish: date
    shift_days: int | None
    source: bool = False


class SchedulePreviewRead(BaseModel):
    preview_token: str
    schedule_fingerprint: str
    proposed_change: ScheduleChangeRequest
    affected_tasks: list[AffectedTaskRead]
    milestone_impacts: list[ScheduleMilestoneRead]
    deadline_impact: DeadlineImpactRead
    critical_path: CriticalPathRead
    warnings: list[str]


class ScheduleApplyRequest(BaseModel):
    preview_token: str = Field(min_length=64, max_length=64)
    change: ScheduleChangeRequest


class ScheduleApplyRead(BaseModel):
    applied_at: datetime
    affected_task_ids: list[UUID]
    milestone_id: UUID | None
    schedule: ScheduleRead
