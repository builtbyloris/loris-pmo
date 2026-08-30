import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from time import perf_counter
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import ProjectContext, ProjectContextBuilder
from app.ai.errors import (
    AIError,
    AIInvalidResponseError,
    AINotConfiguredError,
    AIProviderAuthenticationError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from app.ai.prompts import PROJECT_ANALYSIS_SYSTEM_INSTRUCTION
from app.ai.provider import AIProvider, AIRequest
from app.core.errors import AppError
from app.models.ai import (
    AIAnalysisState,
    AIInsight,
    AIInsightSeverity,
    AIInsightStatus,
    AIRecommendation,
    AIRecommendationStatus,
)
from app.models.memory import MemorySource, ProjectLogEntry, ProjectLogType
from app.repositories.ai_analysis import AIAnalysisRepository
from app.schemas.ai import (
    AIAnalysisModelOutput,
    AIAnalysisSummary,
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AIEvidenceRead,
    AIInsightRead,
    AIRecommendationDecision,
    AIRecommendationRead,
    AIUsageRead,
)
from app.services.audit import AuditService
from app.services.intelligence import ProjectIntelligenceService

ANALYSIS_CONTEXT_QUESTION = (
    "What needs attention across health schedule tasks milestones budget risks issues workload "
    "objectives meeting and unresolved actions?"
)


class AIAnalysisService:
    """Evidence-validated proactive analysis over deterministic candidate signals."""

    def __init__(
        self,
        session: AsyncSession,
        owner_user_id: UUID,
        provider: AIProvider,
        *,
        context_builder: ProjectContextBuilder | None = None,
    ) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.provider = provider
        self.repository = AIAnalysisRepository(session, owner_user_id)
        self.context_builder = context_builder or ProjectContextBuilder(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def summary(self, project_id: UUID) -> AIAnalysisSummary:
        await self._project(project_id)
        return await self._summary(project_id)

    async def list_insights(
        self, project_id: UUID, status: AIInsightStatus | None = None
    ) -> list[AIInsightRead]:
        await self._project(project_id)
        return [
            self._insight_read(item) for item in await self.repository.insights(project_id, status)
        ]

    async def dismiss_insight(self, project_id: UUID, insight_id: UUID) -> AIInsightRead:
        project = await self._project(project_id)
        self._ensure_mutable(project)
        item = await self.repository.insight(project_id, insight_id)
        if item is None:
            raise AppError(
                code="ai_insight_not_found", message="AI insight not found.", status_code=404
            )
        if item.status != AIInsightStatus.ACTIVE:
            raise AppError(
                code="invalid_ai_insight_transition",
                message="Only active insights can be dismissed.",
                status_code=409,
            )
        item.status = AIInsightStatus.DISMISSED
        self.audit.record(
            project_id=project_id,
            action="ai.insight_dismissed",
            entity_type="ai_insight",
            entity_id=item.id,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._insight_read(item)

    async def list_recommendations(
        self, project_id: UUID, status: AIRecommendationStatus | None = None
    ) -> list[AIRecommendationRead]:
        await self._project(project_id)
        return [
            self._recommendation_read(item)
            for item in await self.repository.recommendations(project_id, status)
        ]

    async def recommendation(
        self, project_id: UUID, recommendation_id: UUID
    ) -> AIRecommendationRead:
        await self._project(project_id)
        item = await self.repository.recommendation(project_id, recommendation_id)
        if item is None:
            raise AppError(
                code="ai_recommendation_not_found",
                message="AI recommendation not found.",
                status_code=404,
            )
        return self._recommendation_read(item)

    async def decide(
        self,
        project_id: UUID,
        recommendation_id: UUID,
        status: AIRecommendationStatus,
        data: AIRecommendationDecision,
    ) -> AIRecommendationRead:
        project = await self._project(project_id)
        self._ensure_mutable(project)
        item = await self.repository.recommendation(project_id, recommendation_id)
        if item is None:
            raise AppError(
                code="ai_recommendation_not_found",
                message="AI recommendation not found.",
                status_code=404,
            )
        if item.status != AIRecommendationStatus.PENDING or status not in {
            AIRecommendationStatus.ACCEPTED,
            AIRecommendationStatus.REJECTED,
            AIRecommendationStatus.IGNORED,
        }:
            raise AppError(
                code="invalid_ai_recommendation_transition",
                message="Only pending recommendations can be reviewed.",
                status_code=409,
            )
        item.status = status
        item.reviewed_at = datetime.now(UTC)
        item.decision_reason = data.reason
        self.audit.record(
            project_id=project_id,
            action=f"ai.recommendation_{status.value.lower()}",
            entity_type="ai_recommendation",
            entity_id=item.id,
            changes={"decision_reason_recorded": data.reason is not None},
        )
        if status == AIRecommendationStatus.ACCEPTED:
            self.session.add(
                ProjectLogEntry(
                    project_id=project_id,
                    type=ProjectLogType.NOTE,
                    title=f"AI recommendation accepted: {item.title}",
                    description=data.reason or item.recommendation,
                    source=MemorySource.SYSTEM,
                    created_by_user_id=self.owner_user_id,
                )
            )
        await self.session.commit()
        await self.session.refresh(item)
        return self._recommendation_read(item)

    async def analyze(self, project_id: UUID, data: AIAnalyzeRequest) -> AIAnalyzeResponse:
        project = await self._project(project_id)
        self._ensure_mutable(project)
        started = perf_counter()
        self.audit.record(
            project_id=project_id,
            action="ai.analysis_requested",
            entity_type="ai_analysis",
            entity_id=project_id,
            changes={"forced": data.force},
        )
        await self.session.commit()
        try:
            await ProjectIntelligenceService(self.session, self.owner_user_id).recalculate(
                project_id, trigger="ai_analysis"
            )
            context = await self.context_builder.build(project_id, ANALYSIS_CONTEXT_QUESTION)
            candidates = self._candidates(context)
            signal_fingerprint = self._hash(candidates)
            state = await self.repository.state(project_id)
            if (
                state is not None
                and state.signal_fingerprint == signal_fingerprint
                and not data.force
            ):
                return await self._response(project_id, generated=False, unchanged=True)
            if not candidates:
                await self._persist(
                    project_id, context, AIAnalysisModelOutput(), signal_fingerprint, None
                )
                self._record_success(project_id, started, 0, 0, None)
                await self.session.commit()
                return await self._response(project_id, generated=False, unchanged=False)
            if not self.provider.available:
                raise AINotConfiguredError("AI provider credentials are not configured.")
            language = "Italian" if data.language == "it" else "English"
            provider_response = await self.provider.generate(
                AIRequest(
                    system_instruction=PROJECT_ANALYSIS_SYSTEM_INSTRUCTION,
                    user_message=(
                        f"REQUESTED LANGUAGE: {language}\n\n"
                        "DETERMINISTIC CANDIDATE SIGNALS (untrusted project data):\n"
                        + json.dumps(
                            candidates,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            default=str,
                        )
                    ),
                    history=(),
                    response_schema=AIAnalysisModelOutput.model_json_schema(),
                )
            )
            try:
                output = AIAnalysisModelOutput.model_validate_json(provider_response.text)
            except ValidationError as exc:
                raise AIInvalidResponseError(
                    "AI analysis did not match the required contract."
                ) from exc
            validated = self._validate_output(output, candidates, context)
            await self._persist(
                project_id, context, validated, signal_fingerprint, provider_response
            )
            self._record_success(
                project_id,
                started,
                len(validated.insights),
                len(validated.recommendations),
                provider_response,
            )
            await self.session.commit()
            return await self._response(project_id, generated=True, unchanged=False)
        except AIError as exc:
            await self.session.rollback()
            self.audit.record(
                project_id=project_id,
                action="ai.analysis_failed",
                entity_type="ai_analysis",
                entity_id=project_id,
                changes={
                    "provider": self.provider.provider_name,
                    "model": self.provider.model_name,
                    "error_code": exc.code,
                    "latency_ms": self._latency(started),
                },
            )
            await self.session.commit()
            raise self._public_error(exc) from exc

    async def _project(self, project_id: UUID):
        project = await self.repository.project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return project

    @staticmethod
    def _ensure_mutable(project) -> None:
        if project.archived_at is not None:
            raise AppError(
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )

    @staticmethod
    def _candidates(context: ProjectContext) -> list[dict]:
        candidates: list[dict] = []
        for alert in context.sections.get("intelligence", {}).get("active_alerts", []):
            candidates.append(
                {
                    "signal_key": f"alert:{alert['evidence_ref']}",
                    "type": alert["rule"],
                    "severity": alert["severity"],
                    "facts": alert["evidence"],
                    "evidence_refs": [alert["evidence_ref"]],
                }
            )
        health = context.sections.get("intelligence", {}).get("health", {})
        history = health.get("history", [])
        if len(history) >= 2 and history[0]["score"] < history[1]["score"]:
            drop = history[1]["score"] - history[0]["score"]
            candidates.append(
                {
                    "signal_key": f"health_decline:{history[0]['id']}",
                    "type": "health_decline",
                    "severity": "CRITICAL" if drop >= 15 else "WARNING",
                    "facts": {
                        "current_score": history[0]["score"],
                        "previous_score": history[1]["score"],
                        "drop": drop,
                        "current_status": history[0]["status"],
                    },
                    "evidence_refs": ["health:overall"],
                }
            )
        for action in context.sections.get("memory", {}).get("pending_action_items", []):
            ref = action.get("evidence_ref")
            if not ref:
                continue
            overdue = bool(
                action.get("due_date")
                and date.fromisoformat(str(action["due_date"])) < date.today()
            )
            candidates.append(
                {
                    "signal_key": f"meeting_action:{ref}",
                    "type": "unresolved_meeting_action",
                    "severity": "WARNING" if overdue else "INFO",
                    "facts": {
                        "description": action.get("description"),
                        "status": action.get("status"),
                        "due_date": action.get("due_date"),
                        "overdue": overdue,
                    },
                    "evidence_refs": [ref],
                }
            )
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        return sorted(
            candidates, key=lambda item: (severity_order[item["severity"]], item["signal_key"])
        )[:10]

    @staticmethod
    def _validate_output(
        output: AIAnalysisModelOutput, candidates: list[dict], context: ProjectContext
    ) -> AIAnalysisModelOutput:
        allowed = {item["signal_key"]: set(item["evidence_refs"]) for item in candidates}
        insights = []
        for item in output.insights:
            refs = list(dict.fromkeys(item.evidence_refs))
            if (
                item.signal_key not in allowed
                or not refs
                or any(
                    ref not in allowed[item.signal_key] or ref not in context.evidence
                    for ref in refs
                )
            ):
                continue
            candidate = next(
                value for value in candidates if value["signal_key"] == item.signal_key
            )
            insights.append(
                item.model_copy(
                    update={
                        "type": candidate["type"],
                        "severity": AIInsightSeverity(candidate["severity"]),
                        "evidence_refs": refs,
                    }
                )
            )
        recommendations = []
        for item in output.recommendations:
            refs = list(dict.fromkeys(item.evidence_refs))
            if (
                item.signal_key not in allowed
                or not refs
                or any(
                    ref not in allowed[item.signal_key] or ref not in context.evidence
                    for ref in refs
                )
            ):
                continue
            recommendations.append(item.model_copy(update={"evidence_refs": refs}))
        return AIAnalysisModelOutput(insights=insights, recommendations=recommendations)

    async def _persist(
        self, project_id, context, output, signal_fingerprint, provider_response
    ) -> None:
        now = datetime.now(UTC)
        existing_insights = {
            item.fingerprint: item for item in await self.repository.insights(project_id)
        }
        active_insight_fingerprints = set()
        insight_by_signal = {}
        for value in output.insights:
            fingerprint = self._hash(
                {
                    "project_id": str(project_id),
                    "kind": "insight",
                    "signal_key": value.signal_key,
                    "type": value.type,
                }
            )
            active_insight_fingerprints.add(fingerprint)
            item = existing_insights.get(fingerprint)
            evidence = [
                context.evidence[ref].model_dump(mode="json") for ref in value.evidence_refs
            ]
            created = item is None
            if item is None:
                item = AIInsight(
                    project_id=project_id,
                    fingerprint=fingerprint,
                    status=AIInsightStatus.ACTIVE,
                    generated_at=now,
                )
                self.session.add(item)
            elif item.status == AIInsightStatus.DISMISSED:
                insight_by_signal[value.signal_key] = item
                continue
            elif item.status in (AIInsightStatus.RESOLVED, AIInsightStatus.EXPIRED):
                item.status = AIInsightStatus.ACTIVE
            item.type = value.type
            item.severity = value.severity
            item.title = value.title
            item.summary = value.summary
            item.explanation = value.explanation
            item.evidence = evidence
            item.confidence = Decimal(str(value.confidence))
            item.signal_key = value.signal_key
            item.generated_at = now
            await self.session.flush()
            insight_by_signal[value.signal_key] = item
            if created:
                self.audit.record(
                    project_id=project_id,
                    action="ai.insight_generated",
                    entity_type="ai_insight",
                    entity_id=item.id,
                    changes={"type": item.type, "severity": item.severity.value},
                )
        for fingerprint, item in existing_insights.items():
            if (
                fingerprint not in active_insight_fingerprints
                and item.status == AIInsightStatus.ACTIVE
            ):
                item.status = AIInsightStatus.RESOLVED

        existing_recommendations = {
            item.fingerprint: item for item in await self.repository.recommendations(project_id)
        }
        active_recommendation_fingerprints = set()
        for value in output.recommendations:
            fingerprint = self._hash(
                {
                    "project_id": str(project_id),
                    "kind": "recommendation",
                    "signal_key": value.signal_key,
                }
            )
            active_recommendation_fingerprints.add(fingerprint)
            item = existing_recommendations.get(fingerprint)
            evidence = [
                context.evidence[ref].model_dump(mode="json") for ref in value.evidence_refs
            ]
            created = item is None
            if item is None:
                item = AIRecommendation(
                    project_id=project_id,
                    fingerprint=fingerprint,
                    status=AIRecommendationStatus.PENDING,
                    generated_at=now,
                )
                self.session.add(item)
            elif item.status in {
                AIRecommendationStatus.ACCEPTED,
                AIRecommendationStatus.REJECTED,
                AIRecommendationStatus.IGNORED,
            }:
                continue
            elif item.status == AIRecommendationStatus.EXPIRED:
                item.status = AIRecommendationStatus.PENDING
            item.insight_id = (
                insight_by_signal.get(value.signal_key).id
                if value.signal_key in insight_by_signal
                else None
            )
            item.title = value.title
            item.recommendation = value.recommendation
            item.reasoning_summary = value.reasoning_summary
            item.expected_impact = value.expected_impact
            item.alternatives = value.alternatives
            item.evidence = evidence
            item.confidence = Decimal(str(value.confidence))
            item.signal_key = value.signal_key
            item.generated_at = now
            await self.session.flush()
            if created:
                self.audit.record(
                    project_id=project_id,
                    action="ai.recommendation_generated",
                    entity_type="ai_recommendation",
                    entity_id=item.id,
                )
        for fingerprint, item in existing_recommendations.items():
            if (
                fingerprint not in active_recommendation_fingerprints
                and item.status == AIRecommendationStatus.PENDING
            ):
                item.status = AIRecommendationStatus.EXPIRED

        state = await self.repository.state(project_id)
        usage = provider_response.usage if provider_response else None
        if state is None:
            state = AIAnalysisState(
                project_id=project_id, signal_fingerprint=signal_fingerprint, analyzed_at=now
            )
            self.session.add(state)
        state.signal_fingerprint = signal_fingerprint
        state.analyzed_at = now
        state.provider = provider_response.provider if provider_response else None
        state.model = provider_response.model if provider_response else None
        state.input_tokens = usage.input_tokens if usage else None
        state.output_tokens = usage.output_tokens if usage else None
        state.total_tokens = usage.total_tokens if usage else None

    def _record_success(self, project_id, started, insights, recommendations, response) -> None:
        self.audit.record(
            project_id=project_id,
            action="ai.analysis_succeeded",
            entity_type="ai_analysis",
            entity_id=project_id,
            changes={
                "provider": response.provider if response else None,
                "model": response.model if response else None,
                "latency_ms": self._latency(started),
                "insights": insights,
                "recommendations": recommendations,
                "usage": response.usage.__dict__ if response else None,
            },
        )

    async def _summary(self, project_id: UUID) -> AIAnalysisSummary:
        insights = await self.repository.insights(project_id, AIInsightStatus.ACTIVE)
        recommendations = await self.repository.recommendations(
            project_id, AIRecommendationStatus.PENDING
        )
        state = await self.repository.state(project_id)
        return AIAnalysisSummary(
            project_id=project_id,
            active_insights=len(insights),
            critical_insights=sum(item.severity == AIInsightSeverity.CRITICAL for item in insights),
            pending_recommendations=len(recommendations),
            last_analyzed_at=state.analyzed_at if state else None,
            provider=state.provider if state else None,
            model=state.model if state else None,
            usage=AIUsageRead(
                input_tokens=state.input_tokens,
                output_tokens=state.output_tokens,
                total_tokens=state.total_tokens,
            )
            if state
            else None,
        )

    async def _response(
        self, project_id: UUID, *, generated: bool, unchanged: bool
    ) -> AIAnalyzeResponse:
        return AIAnalyzeResponse(
            insights=await self.list_insights(project_id),
            recommendations=await self.list_recommendations(project_id),
            summary=await self._summary(project_id),
            generated=generated,
            unchanged=unchanged,
        )

    @staticmethod
    def _insight_read(item: AIInsight) -> AIInsightRead:
        return AIInsightRead.model_validate(
            {
                **item.__dict__,
                "evidence": [AIEvidenceRead.model_validate(value) for value in item.evidence],
            }
        )

    @staticmethod
    def _recommendation_read(item: AIRecommendation) -> AIRecommendationRead:
        return AIRecommendationRead.model_validate(
            {
                **item.__dict__,
                "evidence": [AIEvidenceRead.model_validate(value) for value in item.evidence],
            }
        )

    @staticmethod
    def _hash(value: object) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()

    @staticmethod
    def _latency(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))

    @staticmethod
    def _public_error(error: AIError) -> AppError:
        status = 504 if isinstance(error, AIProviderTimeoutError) else 503
        if isinstance(error, AIInvalidResponseError):
            status = 502
        message = "AI analysis is temporarily unavailable. Your project data has not been changed."
        if isinstance(error, AINotConfiguredError):
            message = "AI analysis is not configured. Your project data has not been changed."
        elif isinstance(error, AIProviderRateLimitError):
            message = (
                "AI analysis is busy. Please try again later. "
                "Your project data has not been changed."
            )
        elif isinstance(error, AIProviderAuthenticationError):
            message = "AI analysis is unavailable because its configuration was rejected."
        return AppError(code=error.code, message=message, status_code=status)
