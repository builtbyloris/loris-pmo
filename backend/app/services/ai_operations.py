import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.context import ProjectContext, ProjectContextBuilder
from app.ai.errors import AIError, AIInvalidResponseError, AINotConfiguredError
from app.ai.prompts import (
    DAILY_BRIEFING_SYSTEM_INSTRUCTION,
    MEETING_ASSISTANT_SYSTEM_INSTRUCTION,
    SCENARIO_ANALYSIS_SYSTEM_INSTRUCTION,
    WEEKLY_REVIEW_SYSTEM_INSTRUCTION,
)
from app.ai.provider import AIProvider, AIRequest, AIResponse
from app.core.errors import AppError
from app.models.ai_operations import (
    AIBriefing,
    AIBriefingKind,
    AIScenario,
    AIScenarioType,
    MeetingAIAnalysis,
    MeetingAIProposal,
    MeetingAIProposalKind,
    MeetingAIProposalStatus,
)
from app.models.control import ControlPriority, ImpactLevel, Issue, IssueStatus, Risk, RiskStatus
from app.models.intelligence import HealthSnapshot
from app.models.memory import (
    ActionItemStatus,
    Decision,
    DecisionStatus,
    MeetingActionItem,
    MemorySource,
    ProjectLogEntry,
    ProjectLogType,
)
from app.models.people import ProjectMember, TaskAssignee
from app.models.task import Task, TaskStatus
from app.repositories.ai_operations import AIOperationsRepository
from app.repositories.control import ControlRepository
from app.repositories.work_planning import WorkPlanningRepository
from app.schemas.ai import AIEvidenceRead, AIEvidenceType, AIUsageRead
from app.schemas.ai_operations import (
    AIBriefingRead,
    AIGenerateRequest,
    AIScenarioOutput,
    AIScenarioRead,
    AIScenarioRequest,
    DailyBriefingOutput,
    MeetingAIAnalysisRead,
    MeetingAIConfirmRead,
    MeetingAIOutput,
    MeetingAIProposalRead,
    WeeklyReviewOutput,
)
from app.schemas.scheduling import ScheduleChangeRequest
from app.services.ai_analysis import AIAnalysisService
from app.services.audit import AuditService
from app.services.finance import FinanceService
from app.services.intelligence import ProjectIntelligenceService
from app.services.scheduling import SchedulingService

ATTENTION_QUESTION = (
    "What requires attention now across alerts health overdue or blocked tasks upcoming "
    "milestones budget risks issues workload meeting actions insights and recommendations?"
)
WEEKLY_DAYS = 7


class AIOperationsService:
    """Bounded, evidence-validated operational AI. Operational writes require confirmation."""

    def __init__(self, session: AsyncSession, owner_user_id: UUID, provider: AIProvider) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.provider = provider
        self.repository = AIOperationsRepository(session, owner_user_id)
        self.context_builder = ProjectContextBuilder(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def latest_daily(self, project_id: UUID) -> AIBriefingRead | None:
        await self._project(project_id)
        value = await self.repository.latest_briefing(project_id, AIBriefingKind.DAILY)
        return self._briefing_read(value) if value else None

    async def generate_daily(self, project_id: UUID, data: AIGenerateRequest) -> AIBriefingRead:
        project = await self._project(project_id)
        self._mutable(project)
        await ProjectIntelligenceService(self.session, self.owner_user_id).recalculate(
            project_id, trigger="ai_daily_briefing"
        )
        context = await self.context_builder.build(project_id, ATTENTION_QUESTION)
        candidates = self._daily_candidates(context)
        fingerprint = self._hash(candidates)
        if not data.force:
            existing = await self.repository.briefing_with_fingerprint(
                project_id, AIBriefingKind.DAILY, fingerprint
            )
            if existing:
                return self._briefing_read(existing, reused=True)
        started = perf_counter()
        try:
            if candidates:
                response = await self._generate(
                    DAILY_BRIEFING_SYSTEM_INSTRUCTION,
                    data.language,
                    {"candidate_signals": candidates},
                    DailyBriefingOutput,
                )
                output = DailyBriefingOutput.model_validate_json(response.text)
                allowed = {ref for item in candidates for ref in item["evidence_refs"]}
                items = [
                    item.model_copy(
                        update={"evidence_refs": list(dict.fromkeys(item.evidence_refs))}
                    )
                    for item in output.attention_items
                    if item.evidence_refs
                    and all(
                        ref in allowed and ref in context.evidence for ref in item.evidence_refs
                    )
                ][:5]
                output = output.model_copy(update={"attention_items": items})
                refs = list(dict.fromkeys(ref for item in items for ref in item.evidence_refs))
            else:
                response = None
                output = DailyBriefingOutput(
                    summary=(
                        "Non risultano elementi urgenti dai segnali disponibili."
                        if data.language == "it"
                        else "No urgent items were found in the available signals."
                    )
                )
                refs = []
            now = datetime.now(UTC)
            item = AIBriefing(
                project_id=project_id,
                kind=AIBriefingKind.DAILY,
                fingerprint=fingerprint,
                content=output.model_dump(mode="json"),
                evidence=self._evidence(context, refs),
                generated_at=now,
                **self._provider_fields(response),
            )
            self.session.add(item)
            await self.session.flush()
            self.audit.record(
                project_id=project_id,
                action="ai.daily_briefing_generated",
                entity_type="ai_briefing",
                entity_id=item.id,
                changes={
                    "reused": False,
                    "items": len(output.attention_items),
                    "latency_ms": self._latency(started),
                },
            )
            await self.session.commit()
            await self.session.refresh(item)
            return self._briefing_read(item)
        except (AIError, ValidationError) as exc:
            await self.session.rollback()
            raise self._safe_ai_error(exc) from exc

    async def weekly_reviews(self, project_id: UUID) -> list[AIBriefingRead]:
        await self._project(project_id)
        return [
            self._briefing_read(item) for item in await self.repository.weekly_reviews(project_id)
        ]

    async def generate_weekly(self, project_id: UUID, data: AIGenerateRequest) -> AIBriefingRead:
        project = await self._project(project_id)
        self._mutable(project)
        await ProjectIntelligenceService(self.session, self.owner_user_id).recalculate(
            project_id, trigger="ai_weekly_review"
        )
        end = datetime.now(UTC)
        start = end - timedelta(days=WEEKLY_DAYS)
        events = await self.repository.period_events(project_id, start, end)
        facts, evidence = self._period_facts(events, start, end)
        await self._add_health_movement(project_id, start, end, facts, evidence)
        insufficient = not await self.repository.event_before(project_id, start)
        fingerprint = self._hash({"period": [start.date(), end.date()], "facts": facts})
        if not data.force:
            existing = await self.repository.briefing_with_fingerprint(
                project_id, AIBriefingKind.WEEKLY, fingerprint
            )
            if existing:
                return self._briefing_read(existing, reused=True)
        try:
            response = await self._generate(
                WEEKLY_REVIEW_SYSTEM_INSTRUCTION,
                data.language,
                {
                    "period": {"start": start, "end": end},
                    "facts": facts,
                    "insufficient_history": insufficient,
                },
                WeeklyReviewOutput,
            )
            output = WeeklyReviewOutput.model_validate_json(response.text)
            allowed = set(evidence)
            refs = [ref for ref in dict.fromkeys(output.evidence_refs) if ref in allowed]
            if not refs:
                refs = list(evidence)
            output = output.model_copy(
                update={"evidence_refs": refs, "insufficient_history": insufficient}
            )
            item = AIBriefing(
                project_id=project_id,
                kind=AIBriefingKind.WEEKLY,
                fingerprint=fingerprint,
                period_start=start,
                period_end=end,
                content=output.model_dump(mode="json"),
                evidence=[evidence[ref].model_dump(mode="json") for ref in refs],
                generated_at=end,
                **self._provider_fields(response),
            )
            self.session.add(item)
            await self.session.flush()
            self.audit.record(
                project_id=project_id,
                action="ai.weekly_review_generated",
                entity_type="ai_briefing",
                entity_id=item.id,
                changes={"period_days": WEEKLY_DAYS, "events": len(events)},
            )
            await self.session.commit()
            await self.session.refresh(item)
            return self._briefing_read(item)
        except (AIError, ValidationError) as exc:
            await self.session.rollback()
            raise self._safe_ai_error(exc) from exc

    async def list_scenarios(self, project_id: UUID) -> list[AIScenarioRead]:
        await self._project(project_id)
        return [self._scenario_read(item) for item in await self.repository.scenarios(project_id)]

    async def get_scenario(self, project_id: UUID, scenario_id: UUID) -> AIScenarioRead:
        await self._project(project_id)
        item = await self.repository.scenario(project_id, scenario_id)
        if item is None:
            raise AppError(
                code="ai_scenario_not_found", message="Scenario not found.", status_code=404
            )
        return self._scenario_read(item)

    async def run_scenario(self, project_id: UUID, data: AIScenarioRequest) -> AIScenarioRead:
        project = await self._project(project_id)
        self._mutable(project)
        impact, evidence = await self._simulate(project, data)
        try:
            response = await self._generate(
                SCENARIO_ANALYSIS_SYSTEM_INSTRUCTION,
                data.language,
                {
                    "scenario_type": data.type,
                    "parameters": data.safe_parameters(),
                    "deterministic_impact": impact,
                    "evidence_catalog": [
                        value.model_dump(mode="json") for value in evidence.values()
                    ],
                },
                AIScenarioOutput,
            )
            output = AIScenarioOutput.model_validate_json(response.text)
            refs = list(dict.fromkeys(output.evidence_refs))
            if not refs or any(ref not in evidence for ref in refs):
                raise AIInvalidResponseError(
                    "Scenario response contained invalid evidence references."
                )
            item = AIScenario(
                project_id=project_id,
                type=data.type,
                parameters=data.safe_parameters(),
                deterministic_impact=impact,
                interpretation=output.model_dump(mode="json"),
                evidence=[evidence[ref].model_dump(mode="json") for ref in refs],
                **self._provider_fields(response),
            )
            self.session.add(item)
            await self.session.flush()
            self.audit.record(
                project_id=project_id,
                action="ai.scenario_run",
                entity_type="ai_scenario",
                entity_id=item.id,
                changes={"type": data.type.value},
            )
            await self.session.commit()
            await self.session.refresh(item)
            return self._scenario_read(item)
        except (AIError, ValidationError) as exc:
            await self.session.rollback()
            raise self._safe_ai_error(exc) from exc

    async def latest_meeting(
        self, project_id: UUID, meeting_id: UUID
    ) -> MeetingAIAnalysisRead | None:
        await self._meeting(project_id, meeting_id)
        item = await self.repository.latest_meeting_analysis(project_id, meeting_id)
        return self._meeting_read(item) if item else None

    async def analyze_meeting(
        self, project_id: UUID, meeting_id: UUID, data: AIGenerateRequest
    ) -> MeetingAIAnalysisRead:
        project = await self._project(project_id)
        self._mutable(project)
        meeting = await self._meeting(project_id, meeting_id)
        if not (meeting.notes or meeting.agenda):
            raise AppError(
                code="meeting_content_required",
                message="Meeting notes or agenda are required.",
                status_code=422,
            )
        fingerprint = self._hash(
            {
                "title": meeting.title,
                "agenda": meeting.agenda,
                "notes": meeting.notes,
                "participants": sorted(str(p.project_member_id) for p in meeting.participants),
            }
        )
        if not data.force:
            existing = await self.repository.meeting_analysis_with_fingerprint(
                project_id, meeting_id, fingerprint
            )
            if existing:
                return self._meeting_read(existing, reused=True)
        context = await self.context_builder.build(
            project_id, "meeting decisions actions risks issues"
        )
        meeting_ref = f"meeting:{meeting.id}"
        if meeting_ref not in context.evidence:
            context.evidence[meeting_ref] = AIEvidenceRead(
                ref=meeting_ref,
                type=AIEvidenceType.MEETING,
                id=meeting.id,
                label=meeting.title,
                detail=f"{meeting.status.value} · {meeting.scheduled_at.isoformat()}",
            )
        try:
            response = await self._generate(
                MEETING_ASSISTANT_SYSTEM_INSTRUCTION,
                data.language,
                {
                    "meeting": {
                        "title": meeting.title,
                        "scheduled_at": meeting.scheduled_at,
                        "agenda": meeting.agenda,
                        "notes": meeting.notes,
                        "participant_member_ids": [
                            str(p.project_member_id) for p in meeting.participants
                        ],
                    },
                    "project_context": context.sections,
                    "required_meeting_evidence_ref": meeting_ref,
                },
                MeetingAIOutput,
            )
            output = MeetingAIOutput.model_validate_json(response.text)
            participant_ids = {p.project_member_id for p in meeting.participants}
            proposals = []
            keys = set()
            for proposal in output.proposals:
                refs = list(dict.fromkeys(proposal.evidence_refs))
                if (
                    proposal.proposal_key in keys
                    or meeting_ref not in refs
                    or any(ref not in context.evidence for ref in refs)
                ):
                    raise AIInvalidResponseError(
                        "Meeting response contained invalid proposal evidence."
                    )
                if proposal.owner_member_id and proposal.owner_member_id not in participant_ids:
                    raise AIInvalidResponseError("Meeting response proposed an invalid owner.")
                if proposal.kind == MeetingAIProposalKind.RISK and (
                    proposal.probability is None or proposal.impact is None
                ):
                    raise AIInvalidResponseError("Risk proposals require probability and impact.")
                keys.add(proposal.proposal_key)
                proposals.append((proposal, refs))
            root_refs = list(dict.fromkeys(output.evidence_refs))
            if meeting_ref not in root_refs or any(
                ref not in context.evidence for ref in root_refs
            ):
                raise AIInvalidResponseError("Meeting response contained invalid evidence.")
            now = datetime.now(UTC)
            analysis = MeetingAIAnalysis(
                project_id=project_id,
                meeting_id=meeting_id,
                fingerprint=fingerprint,
                summary=output.summary,
                evidence=self._evidence(context, root_refs),
                generated_at=now,
                **self._provider_fields(response),
            )
            self.session.add(analysis)
            await self.session.flush()
            for proposal, refs in proposals:
                self.session.add(
                    MeetingAIProposal(
                        analysis_id=analysis.id,
                        project_id=project_id,
                        meeting_id=meeting_id,
                        proposal_key=proposal.proposal_key,
                        kind=proposal.kind,
                        payload=proposal.model_dump(
                            mode="json", exclude={"proposal_key", "kind", "evidence_refs"}
                        ),
                        evidence=self._evidence(context, refs),
                        status=MeetingAIProposalStatus.PENDING,
                    )
                )
            self.audit.record(
                project_id=project_id,
                action="ai.meeting_analysis_generated",
                entity_type="meeting_ai_analysis",
                entity_id=analysis.id,
                changes={"proposals": len(proposals)},
            )
            await self.session.commit()
            item = await self.repository.latest_meeting_analysis(project_id, meeting_id)
            return self._meeting_read(item)
        except (AIError, ValidationError) as exc:
            await self.session.rollback()
            raise self._safe_ai_error(exc) from exc

    async def confirm_proposal(
        self, project_id: UUID, meeting_id: UUID, proposal_id: UUID
    ) -> MeetingAIConfirmRead:
        project = await self._project(project_id)
        self._mutable(project)
        await self._meeting(project_id, meeting_id)
        proposal = await self._proposal(project_id, meeting_id, proposal_id)
        if proposal.status != MeetingAIProposalStatus.PENDING:
            raise AppError(
                code="invalid_meeting_proposal_transition",
                message="Only pending proposals can be confirmed.",
                status_code=409,
            )
        payload = proposal.payload
        owner_member_id = (
            UUID(payload["owner_member_id"]) if payload.get("owner_member_id") else None
        )
        if proposal.kind == MeetingAIProposalKind.ACTION_ITEM:
            entity = MeetingActionItem(
                project_id=project_id,
                meeting_id=meeting_id,
                description=payload["description"],
                owner_member_id=owner_member_id,
                due_date=date.fromisoformat(payload["due_date"])
                if payload.get("due_date")
                else None,
                status=ActionItemStatus.CONFIRMED,
            )
            entity_type = "meeting_action"
        elif proposal.kind == MeetingAIProposalKind.DECISION:
            entity = Decision(
                project_id=project_id,
                meeting_id=meeting_id,
                title=payload["title"],
                decision=payload["description"],
                decision_date=date.today(),
                decision_maker_member_id=owner_member_id,
                reason=payload.get("decision_reason"),
                alternatives="\n".join(payload.get("alternatives") or []) or None,
                expected_impact=payload.get("expected_impact"),
                status=DecisionStatus.DECIDED,
            )
            entity_type = "decision"
        elif proposal.kind == MeetingAIProposalKind.RISK:
            entity = Risk(
                project_id=project_id,
                title=payload["title"],
                description=payload["description"],
                probability=payload["probability"],
                impact=payload["impact"],
                owner_member_id=owner_member_id,
                identified_date=date.today(),
                status=RiskStatus.IDENTIFIED,
            )
            entity_type = "risk"
        else:
            entity = Issue(
                project_id=project_id,
                title=payload["title"],
                description=payload["description"],
                priority=ControlPriority(payload.get("priority") or "MEDIUM"),
                owner_member_id=owner_member_id,
                identified_date=date.today(),
                status=IssueStatus.OPEN,
                schedule_impact=ImpactLevel.NONE,
                budget_impact=ImpactLevel.NONE,
                scope_impact=ImpactLevel.NONE,
                quality_impact=ImpactLevel.NONE,
                estimated_delay_days=payload.get("estimated_delay_days"),
                estimated_cost=Decimal(str(payload["estimated_cost"]))
                if payload.get("estimated_cost") is not None
                else None,
            )
            entity_type = "issue"
        self.session.add(entity)
        await self.session.flush()
        action = {
            "meeting_action": "meeting_action.created",
            "decision": "decision.recorded",
            "risk": "risk.created",
            "issue": "issue.created",
        }[entity_type]
        self.audit.record(
            project_id=project_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity.id,
            changes={"source": "confirmed_meeting_ai_proposal"},
        )
        proposal.status = MeetingAIProposalStatus.CONFIRMED
        proposal.confirmed_entity_type = entity_type
        proposal.confirmed_entity_id = entity.id
        proposal.reviewed_at = datetime.now(UTC)
        self.audit.record(
            project_id=project_id,
            action="ai.meeting_proposal_confirmed",
            entity_type="meeting_ai_proposal",
            entity_id=proposal.id,
            changes={"created_entity_type": entity_type, "created_entity_id": str(entity.id)},
        )
        self.session.add(
            ProjectLogEntry(
                project_id=project_id,
                type=ProjectLogType.AI_EVENT,
                title=f"Meeting AI proposal confirmed: {payload['title']}",
                description=f"Created {entity_type} after explicit user confirmation.",
                source=MemorySource.SYSTEM,
                created_by_user_id=self.owner_user_id,
            )
        )
        await self.session.commit()
        await self.session.refresh(proposal)
        return MeetingAIConfirmRead(
            proposal=self._proposal_read(proposal), entity_type=entity_type, entity_id=entity.id
        )

    async def reject_proposal(
        self, project_id: UUID, meeting_id: UUID, proposal_id: UUID
    ) -> MeetingAIProposalRead:
        project = await self._project(project_id)
        self._mutable(project)
        await self._meeting(project_id, meeting_id)
        proposal = await self._proposal(project_id, meeting_id, proposal_id)
        if proposal.status != MeetingAIProposalStatus.PENDING:
            raise AppError(
                code="invalid_meeting_proposal_transition",
                message="Only pending proposals can be rejected.",
                status_code=409,
            )
        proposal.status = MeetingAIProposalStatus.REJECTED
        proposal.reviewed_at = datetime.now(UTC)
        self.audit.record(
            project_id=project_id,
            action="ai.meeting_proposal_rejected",
            entity_type="meeting_ai_proposal",
            entity_id=proposal.id,
        )
        await self.session.commit()
        await self.session.refresh(proposal)
        return self._proposal_read(proposal)

    async def _simulate(
        self, project, data: AIScenarioRequest
    ) -> tuple[dict, dict[str, AIEvidenceRead]]:
        work = WorkPlanningRepository(self.session, self.owner_user_id)
        evidence: dict[str, AIEvidenceRead] = {}

        def add(ref, kind, entity_id, label, detail):
            evidence[ref] = AIEvidenceRead(
                ref=ref, type=kind, id=entity_id, label=label, detail=detail
            )

        if data.type == AIScenarioType.TASK_DELAY:
            task = await work.get_task(project.id, data.task_id)
            if not task:
                raise AppError(code="task_not_found", message="Task not found.", status_code=404)
            if not task.start_date or not task.due_date:
                raise AppError(
                    code="task_schedule_incomplete",
                    message="Task dates are required for delay simulation.",
                    status_code=422,
                )
            ref = f"task:{task.id}"
            add(ref, AIEvidenceType.TASK, task.id, task.title, f"due {task.due_date}")
            preview = await SchedulingService(self.session, self.owner_user_id).preview(
                project.id,
                ScheduleChangeRequest(
                    entity_type="TASK",
                    task_id=task.id,
                    start_date=task.start_date + timedelta(days=data.delay_days),
                    due_date=task.due_date + timedelta(days=data.delay_days),
                ),
            )
            impact = {
                "projected_due_date": task.due_date + timedelta(days=data.delay_days),
                "delay_days": data.delay_days,
                "affected_tasks": [item.model_dump(mode="json") for item in preview.affected_tasks],
                "milestone_impacts": [
                    item.model_dump(mode="json")
                    for item in preview.milestone_impacts
                    if item.affected_task_ids
                ],
                "deadline_impact": preview.deadline_impact.model_dump(mode="json"),
                "critical_path": preview.critical_path.model_dump(mode="json"),
            }
        elif data.type == AIScenarioType.MILESTONE_DELAY:
            milestone = await work.get_milestone(project.id, data.milestone_id)
            if not milestone:
                raise AppError(
                    code="milestone_not_found", message="Milestone not found.", status_code=404
                )
            if not milestone.due_date:
                raise AppError(
                    code="milestone_schedule_incomplete",
                    message="Milestone date is required for delay simulation.",
                    status_code=422,
                )
            ref = f"milestone:{milestone.id}"
            add(
                ref,
                AIEvidenceType.MILESTONE,
                milestone.id,
                milestone.title,
                f"due {milestone.due_date}",
            )
            preview = await SchedulingService(self.session, self.owner_user_id).preview(
                project.id,
                ScheduleChangeRequest(
                    entity_type="MILESTONE",
                    milestone_id=milestone.id,
                    due_date=milestone.due_date + timedelta(days=data.delay_days),
                ),
            )
            impact = {
                "projected_due_date": milestone.due_date + timedelta(days=data.delay_days),
                "delay_days": data.delay_days,
                "milestone_impacts": [
                    item.model_dump(mode="json")
                    for item in preview.milestone_impacts
                    if item.id == milestone.id
                ],
                "deadline_impact": preview.deadline_impact.model_dump(mode="json"),
                "critical_path": preview.critical_path.model_dump(mode="json"),
            }
        elif data.type == AIScenarioType.COST_INCREASE:
            totals = (
                await FinanceService(self.session, self.owner_user_id).analytics(project.id)
            ).totals
            ref = "budget:summary"
            add(ref, AIEvidenceType.BUDGET, None, "Budget summary", f"forecast {totals.forecast}")
            new_forecast = totals.forecast + data.cost_increase
            impact = {
                "current_forecast": totals.forecast,
                "cost_increase": data.cost_increase,
                "projected_forecast": new_forecast,
                "planned_budget": project.planned_budget,
                "projected_variance": project.planned_budget - new_forecast,
            }
        elif data.type == AIScenarioType.RESOURCE_UNAVAILABLE:
            member = (
                await self.session.execute(
                    select(ProjectMember)
                    .options(selectinload(ProjectMember.person))
                    .where(
                        ProjectMember.project_id == project.id, ProjectMember.id == data.member_id
                    )
                )
            ).scalar_one_or_none()
            if not member:
                raise AppError(
                    code="project_member_not_found",
                    message="Project member not found.",
                    status_code=404,
                )
            ref = f"team_member:{member.id}"
            add(ref, AIEvidenceType.TEAM_MEMBER, member.id, member.person.name, member.role.value)
            task_ids = list(
                (
                    await self.session.execute(
                        select(TaskAssignee.task_id).where(
                            TaskAssignee.project_id == project.id,
                            TaskAssignee.project_member_id == member.id,
                        )
                    )
                ).scalars()
            )
            active = (
                list(
                    (
                        await self.session.execute(
                            select(Task.id).where(
                                Task.id.in_(task_ids),
                                Task.status.not_in([TaskStatus.DONE, TaskStatus.CANCELLED]),
                            )
                        )
                    ).scalars()
                )
                if task_ids
                else []
            )
            impact = {
                "member_id": str(member.id),
                "active_assigned_task_ids": [str(value) for value in active],
                "active_task_count": len(active),
            }
        else:
            risk = await ControlRepository(self.session, self.owner_user_id).get_risk(
                project.id, data.risk_id
            )
            if not risk:
                raise AppError(code="risk_not_found", message="Risk not found.", status_code=404)
            ref = f"risk:{risk.id}"
            add(
                ref,
                AIEvidenceType.RISK,
                risk.id,
                risk.title,
                f"score {risk.probability * risk.impact}",
            )
            impact = {
                "risk_score": risk.probability * risk.impact,
                "probability": risk.probability,
                "impact": risk.impact,
                "linked_task_ids": [str(link.task_id) for link in risk.task_links],
                "linked_milestone_ids": [str(link.milestone_id) for link in risk.milestone_links],
                "mitigation_available": bool(risk.mitigation),
                "contingency_available": bool(risk.contingency),
            }
        simulation_ref = f"simulation:{data.type.value.lower()}"
        add(
            simulation_ref,
            AIEvidenceType.SIMULATION,
            None,
            "Deterministic scenario impact",
            data.type.value,
        )
        impact["simulation_only"] = True
        return self._jsonable(impact), evidence

    @staticmethod
    def _daily_candidates(context: ProjectContext) -> list[dict]:
        candidates = AIAnalysisService._candidates(context)
        for kind in ("insights", "recommendations"):
            for value in context.sections.get("ai_records", {}).get(kind, []):
                candidates.append(
                    {
                        "signal_key": f"{kind}:{value['evidence_ref']}",
                        "type": kind[:-1],
                        "severity": "INFO",
                        "facts": {key: val for key, val in value.items() if key != "evidence_ref"},
                        "evidence_refs": [value["evidence_ref"]],
                    }
                )
        return candidates[:12]

    async def _add_health_movement(self, project_id, start, end, facts, evidence):
        period = list(
            (
                await self.session.execute(
                    select(HealthSnapshot)
                    .where(
                        HealthSnapshot.project_id == project_id,
                        HealthSnapshot.created_at >= start,
                        HealthSnapshot.created_at <= end,
                    )
                    .order_by(HealthSnapshot.created_at)
                )
            ).scalars()
        )
        previous = (
            await self.session.execute(
                select(HealthSnapshot)
                .where(
                    HealthSnapshot.project_id == project_id,
                    HealthSnapshot.created_at < start,
                )
                .order_by(HealthSnapshot.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        first = previous or (period[0] if period else None)
        last = period[-1] if period else previous
        ref = "period_fact:health_movement"
        evidence[ref] = AIEvidenceRead(
            ref=ref,
            type=AIEvidenceType.PERIOD_FACT,
            label="Health movement",
            detail=(
                f"{first.score if first else 'unknown'} to "
                f"{last.score if last else 'unknown'} during the rolling period"
            ),
        )
        facts["health_movement"] = {
            "start_score": first.score if first else None,
            "end_score": last.score if last else None,
            "start_status": first.status.value if first else None,
            "end_status": last.status.value if last else None,
            "snapshot_count": len(period),
            "evidence_ref": ref,
        }

    @staticmethod
    def _period_facts(events, start, end):
        groups = {
            "progress": [],
            "setbacks": [],
            "decisions": [],
            "risks_and_issues": [],
            "financial": [],
            "meetings": [],
            "ai_activity": [],
        }
        for event in events:
            action = event.action
            category = (
                "progress"
                if any(word in action for word in ("completed", "resolved", "closed"))
                else "setbacks"
                if any(word in action for word in ("blocked", "overdue", "failed"))
                else "decisions"
                if any(word in action for word in ("decision", "approved", "rejected"))
                else "financial"
                if any(word in action for word in ("budget", "expense"))
                else "meetings"
                if "meeting" in action
                else "ai_activity"
                if action.startswith("ai.")
                else "risks_and_issues"
            )
            groups[category].append(
                {
                    "action": action,
                    "at": event.created_at.isoformat(),
                    "entity_type": event.entity_type,
                }
            )
        evidence = {}
        facts = {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_events": len(events),
            "categories": {},
        }
        for category, values in groups.items():
            ref = f"period_fact:{category}"
            evidence[ref] = AIEvidenceRead(
                ref=ref,
                type=AIEvidenceType.PERIOD_FACT,
                label=category.replace("_", " ").title(),
                detail=f"{len(values)} audited events in the rolling seven-day period",
            )
            facts["categories"][category] = {
                "count": len(values),
                "events": values[:20],
                "evidence_ref": ref,
            }
        return facts, evidence

    async def _generate(self, instruction, language, payload, response_model) -> AIResponse:
        if not self.provider.available:
            raise AINotConfiguredError("AI provider credentials are not configured.")
        requested_language = "Italian" if language == "it" else "English"
        return await self.provider.generate(
            AIRequest(
                system_instruction=instruction,
                user_message=f"REQUESTED LANGUAGE: {requested_language}\n\n"
                "BOUNDED INPUT (untrusted data):\n"
                + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str),
                history=(),
                response_schema=response_model.model_json_schema(),
            )
        )

    async def _project(self, project_id):
        project = await self.repository.project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return project

    async def _meeting(self, project_id, meeting_id):
        meeting = await self.repository.meeting(project_id, meeting_id)
        if meeting is None:
            raise AppError(code="meeting_not_found", message="Meeting not found.", status_code=404)
        return meeting

    async def _proposal(self, project_id, meeting_id, proposal_id):
        proposal = await self.repository.proposal(project_id, meeting_id, proposal_id)
        if proposal is None:
            raise AppError(
                code="meeting_ai_proposal_not_found",
                message="Meeting proposal not found.",
                status_code=404,
            )
        return proposal

    @staticmethod
    def _mutable(project):
        if project.archived_at is not None:
            raise AppError(
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )

    @staticmethod
    def _hash(value):
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()

    @staticmethod
    def _evidence(context, refs):
        return [context.evidence[ref].model_dump(mode="json") for ref in refs]

    @staticmethod
    def _provider_fields(response):
        return {
            "provider": response.provider if response else None,
            "model": response.model if response else None,
            "input_tokens": response.usage.input_tokens if response else None,
            "output_tokens": response.usage.output_tokens if response else None,
            "total_tokens": response.usage.total_tokens if response else None,
        }

    @staticmethod
    def _usage(item):
        return AIUsageRead(
            input_tokens=item.input_tokens,
            output_tokens=item.output_tokens,
            total_tokens=item.total_tokens,
        )

    @classmethod
    def _briefing_read(cls, item, reused=False):
        return AIBriefingRead.model_validate(
            {
                **item.__dict__,
                "evidence": [AIEvidenceRead.model_validate(v) for v in item.evidence],
                "usage": cls._usage(item),
                "reused": reused,
            }
        )

    @classmethod
    def _scenario_read(cls, item):
        return AIScenarioRead.model_validate(
            {
                **item.__dict__,
                "interpretation": AIScenarioOutput.model_validate(item.interpretation),
                "evidence": [AIEvidenceRead.model_validate(v) for v in item.evidence],
                "usage": cls._usage(item),
            }
        )

    @staticmethod
    def _proposal_read(item):
        return MeetingAIProposalRead.model_validate(
            {**item.__dict__, "evidence": [AIEvidenceRead.model_validate(v) for v in item.evidence]}
        )

    @classmethod
    def _meeting_read(cls, item, reused=False):
        return MeetingAIAnalysisRead.model_validate(
            {
                **item.__dict__,
                "evidence": [AIEvidenceRead.model_validate(v) for v in item.evidence],
                "usage": cls._usage(item),
                "proposals": [cls._proposal_read(v) for v in item.proposals],
                "reused": reused,
            }
        )

    @staticmethod
    def _latency(started):
        return max(0, round((perf_counter() - started) * 1000))

    @staticmethod
    def _jsonable(value):
        return json.loads(json.dumps(value, default=str))

    @staticmethod
    def _safe_ai_error(exc):
        if isinstance(exc, ValidationError):
            exc = AIInvalidResponseError("AI response did not match the required contract.")
        return AIAnalysisService._public_error(exc)
