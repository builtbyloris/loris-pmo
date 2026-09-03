from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import (
    AIAnalysisState,
    AIInsight,
    AIInsightStatus,
    AIRecommendation,
    AIRecommendationStatus,
)
from app.models.project import Project
from app.services.authorization import accessible_project_ids


class AIAnalysisRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
            )
        ).scalar_one_or_none()

    async def state(self, project_id: UUID) -> AIAnalysisState | None:
        return (
            await self.session.execute(
                select(AIAnalysisState).where(AIAnalysisState.project_id == project_id)
            )
        ).scalar_one_or_none()

    async def insights(
        self, project_id: UUID, status: AIInsightStatus | None = None
    ) -> list[AIInsight]:
        query = select(AIInsight).where(AIInsight.project_id == project_id)
        if status is not None:
            query = query.where(AIInsight.status == status)
        return list(
            (await self.session.execute(query.order_by(AIInsight.generated_at.desc()))).scalars()
        )

    async def insight(self, project_id: UUID, insight_id: UUID) -> AIInsight | None:
        return (
            await self.session.execute(
                select(AIInsight).where(
                    AIInsight.project_id == project_id, AIInsight.id == insight_id
                )
            )
        ).scalar_one_or_none()

    async def recommendations(
        self, project_id: UUID, status: AIRecommendationStatus | None = None
    ) -> list[AIRecommendation]:
        query = select(AIRecommendation).where(AIRecommendation.project_id == project_id)
        if status is not None:
            query = query.where(AIRecommendation.status == status)
        return list(
            (
                await self.session.execute(query.order_by(AIRecommendation.generated_at.desc()))
            ).scalars()
        )

    async def recommendation(
        self, project_id: UUID, recommendation_id: UUID
    ) -> AIRecommendation | None:
        return (
            await self.session.execute(
                select(AIRecommendation).where(
                    AIRecommendation.project_id == project_id,
                    AIRecommendation.id == recommendation_id,
                )
            )
        ).scalar_one_or_none()
