from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.ai_operations import (
    AIBriefingKind,
    AIScenarioType,
    MeetingAIProposalKind,
    MeetingAIProposalStatus,
)
from app.schemas.ai import AIEvidenceRead, AIUsageRead

Language = Literal["en", "it"]


class AIGenerateRequest(BaseModel):
    force: bool = False
    language: Language = "en"


class DailyAttentionItemOutput(BaseModel):
    priority: Literal["critical", "warning", "info"]
    title: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1, max_length=1200)
    evidence_refs: list[str] = Field(min_length=1, max_length=5)


class DailyBriefingOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    attention_items: list[DailyAttentionItemOutput] = Field(default_factory=list, max_length=5)
    suggested_focus: list[str] = Field(default_factory=list, max_length=5)


class WeeklyReviewOutput(BaseModel):
    executive_summary: str = Field(min_length=1, max_length=2400)
    progress: list[str] = Field(default_factory=list, max_length=6)
    setbacks: list[str] = Field(default_factory=list, max_length=6)
    decisions: list[str] = Field(default_factory=list, max_length=6)
    risks_and_issues: list[str] = Field(default_factory=list, max_length=6)
    financial_summary: str = Field(min_length=1, max_length=1600)
    next_week_focus: list[str] = Field(default_factory=list, max_length=6)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    insufficient_history: bool = False


class AIBriefingRead(BaseModel):
    id: UUID
    project_id: UUID
    kind: AIBriefingKind
    fingerprint: str
    period_start: datetime | None
    period_end: datetime | None
    content: dict
    evidence: list[AIEvidenceRead]
    provider: str | None
    model: str | None
    usage: AIUsageRead
    generated_at: datetime
    created_at: datetime
    reused: bool = False


class AIScenarioRequest(BaseModel):
    type: AIScenarioType
    language: Language = "en"
    task_id: UUID | None = None
    milestone_id: UUID | None = None
    member_id: UUID | None = None
    risk_id: UUID | None = None
    delay_days: int | None = Field(default=None, ge=1, le=365)
    cost_increase: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def validate_parameters(self) -> "AIScenarioRequest":
        required = {
            AIScenarioType.TASK_DELAY: (self.task_id, self.delay_days),
            AIScenarioType.MILESTONE_DELAY: (self.milestone_id, self.delay_days),
            AIScenarioType.COST_INCREASE: (self.cost_increase,),
            AIScenarioType.RESOURCE_UNAVAILABLE: (self.member_id,),
            AIScenarioType.RISK_OCCURS: (self.risk_id,),
        }[self.type]
        if any(value is None for value in required):
            raise ValueError("The selected scenario is missing required parameters")
        return self

    def safe_parameters(self) -> dict:
        return self.model_dump(mode="json", exclude={"language", "type"}, exclude_none=True)


class AIScenarioOutput(BaseModel):
    interpretation: str = Field(min_length=1, max_length=3000)
    impacts: list[str] = Field(default_factory=list, max_length=8)
    options: list[str] = Field(default_factory=list, max_length=6)
    assumptions: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=15)


class AIScenarioRead(BaseModel):
    id: UUID
    project_id: UUID
    type: AIScenarioType
    parameters: dict
    deterministic_impact: dict
    interpretation: AIScenarioOutput
    evidence: list[AIEvidenceRead]
    provider: str
    model: str
    usage: AIUsageRead
    created_at: datetime


class MeetingAIProposalOutput(BaseModel):
    proposal_key: str = Field(min_length=1, max_length=120)
    kind: MeetingAIProposalKind
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=5000)
    owner_member_id: UUID | None = None
    due_date: date | None = None
    decision_reason: str | None = Field(default=None, max_length=3000)
    alternatives: list[str] = Field(default_factory=list, max_length=3)
    expected_impact: str | None = Field(default=None, max_length=2000)
    probability: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    estimated_delay_days: int | None = Field(default=None, ge=0, le=3650)
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    evidence_refs: list[str] = Field(min_length=1, max_length=10)

    @field_validator("proposal_key")
    @classmethod
    def strip_key(cls, value: str) -> str:
        return value.strip()


class MeetingAIOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    proposals: list[MeetingAIProposalOutput] = Field(default_factory=list, max_length=12)
    evidence_refs: list[str] = Field(min_length=1, max_length=15)


class MeetingAIProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    project_id: UUID
    meeting_id: UUID
    proposal_key: str
    kind: MeetingAIProposalKind
    payload: dict
    evidence: list[AIEvidenceRead]
    status: MeetingAIProposalStatus
    confirmed_entity_type: str | None
    confirmed_entity_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MeetingAIAnalysisRead(BaseModel):
    id: UUID
    project_id: UUID
    meeting_id: UUID
    fingerprint: str
    summary: str
    evidence: list[AIEvidenceRead]
    provider: str
    model: str
    usage: AIUsageRead
    generated_at: datetime
    proposals: list[MeetingAIProposalRead]
    reused: bool = False


class MeetingAIConfirmRead(BaseModel):
    proposal: MeetingAIProposalRead
    entity_type: str
    entity_id: UUID
