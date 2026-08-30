from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_ai_provider
from app.ai.provider import AIProvider
from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.ai import AIInsightStatus, AIRecommendationStatus
from app.schemas.ai import (
    AIAnalysisSummary,
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AIChatRequest,
    AIChatResponse,
    AIInsightRead,
    AIRecommendationDecision,
    AIRecommendationRead,
    AIStatusRead,
)
from app.services.ai_analysis import AIAnalysisService
from app.services.project_assistant import ProjectAssistantService

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["project-assistant"])
Session = Annotated[AsyncSession, Depends(get_db)]
Provider = Annotated[AIProvider, Depends(get_ai_provider)]


@router.get("/status", response_model=AIStatusRead)
async def status(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIStatusRead:
    return await ProjectAssistantService(session, user.id, provider).status(project_id)


@router.post(
    "/chat",
    response_model=AIChatResponse,
    dependencies=[Depends(require_csrf)],
)
async def chat(
    project_id: UUID,
    data: AIChatRequest,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIChatResponse:
    return await ProjectAssistantService(session, user.id, provider).chat(project_id, data)


@router.get("/analysis", response_model=AIAnalysisSummary)
async def analysis_summary(
    project_id: UUID, user: CurrentUser, session: Session, provider: Provider
) -> AIAnalysisSummary:
    return await AIAnalysisService(session, user.id, provider).summary(project_id)


@router.post(
    "/analyze",
    response_model=AIAnalyzeResponse,
    dependencies=[Depends(require_csrf)],
)
async def analyze(
    project_id: UUID,
    data: AIAnalyzeRequest,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIAnalyzeResponse:
    return await AIAnalysisService(session, user.id, provider).analyze(project_id, data)


@router.get("/insights", response_model=list[AIInsightRead])
async def insights(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    provider: Provider,
    status: AIInsightStatus | None = None,
) -> list[AIInsightRead]:
    return await AIAnalysisService(session, user.id, provider).list_insights(project_id, status)


@router.post(
    "/insights/{insight_id}/dismiss",
    response_model=AIInsightRead,
    dependencies=[Depends(require_csrf)],
)
async def dismiss_insight(
    project_id: UUID,
    insight_id: UUID,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIInsightRead:
    return await AIAnalysisService(session, user.id, provider).dismiss_insight(
        project_id, insight_id
    )


@router.get("/recommendations", response_model=list[AIRecommendationRead])
async def recommendations(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    provider: Provider,
    status: AIRecommendationStatus | None = None,
) -> list[AIRecommendationRead]:
    return await AIAnalysisService(session, user.id, provider).list_recommendations(
        project_id, status
    )


@router.get("/recommendations/{recommendation_id}", response_model=AIRecommendationRead)
async def recommendation(
    project_id: UUID,
    recommendation_id: UUID,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIRecommendationRead:
    return await AIAnalysisService(session, user.id, provider).recommendation(
        project_id, recommendation_id
    )


async def _decide(
    project_id: UUID,
    recommendation_id: UUID,
    data: AIRecommendationDecision,
    user: CurrentUser,
    session: Session,
    provider: Provider,
    status: AIRecommendationStatus,
) -> AIRecommendationRead:
    return await AIAnalysisService(session, user.id, provider).decide(
        project_id, recommendation_id, status, data
    )


@router.post(
    "/recommendations/{recommendation_id}/accept",
    response_model=AIRecommendationRead,
    dependencies=[Depends(require_csrf)],
)
async def accept_recommendation(
    project_id: UUID,
    recommendation_id: UUID,
    data: AIRecommendationDecision,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIRecommendationRead:
    return await _decide(
        project_id,
        recommendation_id,
        data,
        user,
        session,
        provider,
        AIRecommendationStatus.ACCEPTED,
    )


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=AIRecommendationRead,
    dependencies=[Depends(require_csrf)],
)
async def reject_recommendation(
    project_id: UUID,
    recommendation_id: UUID,
    data: AIRecommendationDecision,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIRecommendationRead:
    return await _decide(
        project_id,
        recommendation_id,
        data,
        user,
        session,
        provider,
        AIRecommendationStatus.REJECTED,
    )


@router.post(
    "/recommendations/{recommendation_id}/ignore",
    response_model=AIRecommendationRead,
    dependencies=[Depends(require_csrf)],
)
async def ignore_recommendation(
    project_id: UUID,
    recommendation_id: UUID,
    data: AIRecommendationDecision,
    user: CurrentUser,
    session: Session,
    provider: Provider,
) -> AIRecommendationRead:
    return await _decide(
        project_id,
        recommendation_id,
        data,
        user,
        session,
        provider,
        AIRecommendationStatus.IGNORED,
    )
