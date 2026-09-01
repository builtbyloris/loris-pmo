from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ai import AIInsightSeverity, AIInsightStatus, AIRecommendationStatus


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
    MEETING_ACTION = "meeting_action"
    AI_INSIGHT = "ai_insight"
    AI_RECOMMENDATION = "ai_recommendation"
    PERIOD_FACT = "period_fact"
    DOCUMENT = "document"
    CALENDAR_EVENT = "calendar_event"
    EMAIL_MESSAGE = "email_message"
    GITHUB_ISSUE = "github_issue"
    GITHUB_PULL_REQUEST = "github_pull_request"
    GITHUB_COMMIT = "github_commit"
    SIMULATION = "simulation"


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


class AIInsightOutput(BaseModel):
    signal_key: str = Field(min_length=1, max_length=220)
    type: str = Field(min_length=1, max_length=80)
    severity: AIInsightSeverity
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=1200)
    explanation: str = Field(min_length=1, max_length=4000)
    evidence_refs: list[str] = Field(min_length=1, max_length=10)
    confidence: float = Field(ge=0, le=1)


class AIRecommendationOutput(BaseModel):
    signal_key: str = Field(min_length=1, max_length=220)
    title: str = Field(min_length=1, max_length=240)
    recommendation: str = Field(min_length=1, max_length=2400)
    reasoning_summary: str = Field(min_length=1, max_length=2400)
    expected_impact: str | None = Field(default=None, max_length=1600)
    alternatives: list[str] = Field(default_factory=list, max_length=3)
    evidence_refs: list[str] = Field(min_length=1, max_length=10)
    confidence: float = Field(ge=0, le=1)


class AIAnalysisModelOutput(BaseModel):
    insights: list[AIInsightOutput] = Field(default_factory=list, max_length=5)
    recommendations: list[AIRecommendationOutput] = Field(default_factory=list, max_length=5)


class AIAnalyzeRequest(BaseModel):
    force: bool = False
    language: Literal["en", "it"] = "en"


class AIInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    type: str
    severity: AIInsightSeverity
    title: str
    summary: str
    explanation: str
    evidence: list[AIEvidenceRead]
    confidence: float
    status: AIInsightStatus
    generated_at: datetime
    updated_at: datetime


class AIRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    insight_id: UUID | None
    title: str
    recommendation: str
    reasoning_summary: str
    expected_impact: str | None
    alternatives: list[str]
    evidence: list[AIEvidenceRead]
    confidence: float
    status: AIRecommendationStatus
    generated_at: datetime
    reviewed_at: datetime | None
    decision_reason: str | None
    updated_at: datetime


class AIAnalysisSummary(BaseModel):
    project_id: UUID
    active_insights: int
    critical_insights: int
    pending_recommendations: int
    last_analyzed_at: datetime | None
    provider: str | None = None
    model: str | None = None
    usage: AIUsageRead | None = None


class AIAnalyzeResponse(BaseModel):
    insights: list[AIInsightRead]
    recommendations: list[AIRecommendationRead]
    summary: AIAnalysisSummary
    generated: bool
    unchanged: bool


class AIRecommendationDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
