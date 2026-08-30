from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AIMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AIEvidenceType(StrEnum):
    PROJECT = "project"
    TASK = "task"
    MILESTONE = "milestone"
    RISK = "risk"
    ISSUE = "issue"
    CHANGE_REQUEST = "change_request"
    BUDGET = "budget"
    KPI = "kpi"
    HEALTH = "health"
    ALERT = "alert"
    TEAM_MEMBER = "team_member"
    MEETING = "meeting"
    DECISION = "decision"
    PROJECT_LOG = "project_log"


class AIHistoryMessage(BaseModel):
    role: AIMessageRole
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        return value.strip()


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AIHistoryMessage] = Field(default_factory=list, max_length=6)
    language: Literal["en", "it"] = "en"

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()


class AIUsageRead(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AIEvidenceRead(BaseModel):
    ref: str
    type: AIEvidenceType
    id: UUID | None = None
    label: str
    detail: str


class AIModelOutput(BaseModel):
    answer: str = Field(min_length=1, max_length=12000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=10)
    missing_information: list[str] = Field(default_factory=list, max_length=10)
    suggested_followups: list[str] = Field(default_factory=list, max_length=4)


class AIChatResponse(BaseModel):
    answer: str
    evidence: list[AIEvidenceRead]
    assumptions: list[str]
    missing_information: list[str]
    suggested_followups: list[str]
    provider: str
    model: str
    usage: AIUsageRead
    context_sections: list[str]


class AIStatusRead(BaseModel):
    available: bool
    provider: str
    model: str
    reason: str | None = None
