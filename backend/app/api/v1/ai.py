from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_ai_provider
from app.ai.provider import AIProvider
from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.schemas.ai import AIChatRequest, AIChatResponse, AIStatusRead
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
