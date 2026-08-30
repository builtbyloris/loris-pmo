from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_operations import (
    AIBriefing,
    AIBriefingKind,
    AIScenario,
    MeetingAIAnalysis,
    MeetingAIProposal,
)
from app.models.audit import AuditEvent
from app.models.memory import Meeting
from app.models.project import Project


class AIOperationsRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.owner_user_id == self.owner_user_id,
                )
            )
        ).scalar_one_or_none()

    async def latest_briefing(self, project_id: UUID, kind: AIBriefingKind) -> AIBriefing | None:
        return (
            await self.session.execute(
                select(AIBriefing)
                .where(AIBriefing.project_id == project_id, AIBriefing.kind == kind)
                .order_by(AIBriefing.generated_at.desc(), AIBriefing.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def briefing_with_fingerprint(
        self, project_id: UUID, kind: AIBriefingKind, fingerprint: str
    ) -> AIBriefing | None:
        return (
            await self.session.execute(
                select(AIBriefing)
                .where(
                    AIBriefing.project_id == project_id,
                    AIBriefing.kind == kind,
                    AIBriefing.fingerprint == fingerprint,
                )
                .order_by(AIBriefing.generated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def weekly_reviews(self, project_id: UUID, limit: int = 12) -> list[AIBriefing]:
        return list(
            (
                await self.session.execute(
                    select(AIBriefing)
                    .where(
                        AIBriefing.project_id == project_id,
                        AIBriefing.kind == AIBriefingKind.WEEKLY,
                    )
                    .order_by(AIBriefing.generated_at.desc())
                    .limit(limit)
                )
            ).scalars()
        )

    async def scenarios(self, project_id: UUID, limit: int = 30) -> list[AIScenario]:
        return list(
            (
                await self.session.execute(
                    select(AIScenario)
                    .where(AIScenario.project_id == project_id)
                    .order_by(AIScenario.created_at.desc())
                    .limit(limit)
                )
            ).scalars()
        )

    async def scenario(self, project_id: UUID, scenario_id: UUID) -> AIScenario | None:
        return (
            await self.session.execute(
                select(AIScenario).where(
                    AIScenario.project_id == project_id,
                    AIScenario.id == scenario_id,
                )
            )
        ).scalar_one_or_none()

    async def meeting(self, project_id: UUID, meeting_id: UUID) -> Meeting | None:
        return (
            await self.session.execute(
                select(Meeting)
                .join(Project, Project.id == Meeting.project_id)
                .options(selectinload(Meeting.participants), selectinload(Meeting.action_items))
                .where(
                    Meeting.id == meeting_id,
                    Meeting.project_id == project_id,
                    Project.owner_user_id == self.owner_user_id,
                )
            )
        ).scalar_one_or_none()

    async def latest_meeting_analysis(
        self, project_id: UUID, meeting_id: UUID
    ) -> MeetingAIAnalysis | None:
        return (
            await self.session.execute(
                select(MeetingAIAnalysis)
                .options(selectinload(MeetingAIAnalysis.proposals))
                .where(
                    MeetingAIAnalysis.project_id == project_id,
                    MeetingAIAnalysis.meeting_id == meeting_id,
                )
                .order_by(MeetingAIAnalysis.generated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def meeting_analysis_with_fingerprint(
        self, project_id: UUID, meeting_id: UUID, fingerprint: str
    ) -> MeetingAIAnalysis | None:
        return (
            await self.session.execute(
                select(MeetingAIAnalysis)
                .options(selectinload(MeetingAIAnalysis.proposals))
                .where(
                    MeetingAIAnalysis.project_id == project_id,
                    MeetingAIAnalysis.meeting_id == meeting_id,
                    MeetingAIAnalysis.fingerprint == fingerprint,
                )
                .order_by(MeetingAIAnalysis.generated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def proposal(
        self, project_id: UUID, meeting_id: UUID, proposal_id: UUID
    ) -> MeetingAIProposal | None:
        return (
            await self.session.execute(
                select(MeetingAIProposal).where(
                    MeetingAIProposal.project_id == project_id,
                    MeetingAIProposal.meeting_id == meeting_id,
                    MeetingAIProposal.id == proposal_id,
                )
            )
        ).scalar_one_or_none()

    async def period_events(
        self, project_id: UUID, start: datetime, end: datetime
    ) -> list[AuditEvent]:
        return list(
            (
                await self.session.execute(
                    select(AuditEvent)
                    .where(
                        AuditEvent.project_id == project_id,
                        AuditEvent.created_at >= start,
                        AuditEvent.created_at <= end,
                    )
                    .order_by(AuditEvent.created_at, AuditEvent.id)
                )
            ).scalars()
        )

    async def event_before(self, project_id: UUID, before: datetime) -> bool:
        return (
            await self.session.execute(
                select(AuditEvent.id)
                .where(AuditEvent.project_id == project_id, AuditEvent.created_at < before)
                .limit(1)
            )
        ).scalar_one_or_none() is not None
