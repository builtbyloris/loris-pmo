from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.intelligence import AlertSeverity, AlertStatus
from app.schemas.intelligence import AlertRead, HealthRead, IntelligenceRead, KPIValue
from app.services.intelligence import ProjectIntelligenceService

router = APIRouter(prefix="/projects/{project_id}", tags=["intelligence"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/kpis", response_model=list[KPIValue])
async def kpis(project_id: UUID, user: CurrentUser, session: Session) -> list[KPIValue]:
    return await ProjectIntelligenceService(session, user.id).kpis(project_id)


@router.get("/health", response_model=HealthRead)
async def health(project_id: UUID, user: CurrentUser, session: Session) -> HealthRead:
    return await ProjectIntelligenceService(session, user.id).health(project_id)


@router.get("/alerts", response_model=list[AlertRead])
async def alerts(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    status: Annotated[AlertStatus | None, Query()] = None,
    severity: Annotated[AlertSeverity | None, Query()] = None,
) -> list[AlertRead]:
    return await ProjectIntelligenceService(session, user.id).list_alerts(
        project_id, status=status, severity=severity
    )


@router.get("/intelligence", response_model=IntelligenceRead)
async def intelligence(project_id: UUID, user: CurrentUser, session: Session) -> IntelligenceRead:
    return await ProjectIntelligenceService(session, user.id).intelligence(project_id)


@router.post(
    "/intelligence/recalculate",
    response_model=IntelligenceRead,
    dependencies=[Depends(require_csrf)],
)
async def recalculate(project_id: UUID, user: CurrentUser, session: Session) -> IntelligenceRead:
    return await ProjectIntelligenceService(session, user.id).recalculate(project_id)


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertRead,
    dependencies=[Depends(require_csrf)],
)
async def acknowledge(
    project_id: UUID, alert_id: UUID, user: CurrentUser, session: Session
) -> AlertRead:
    return await ProjectIntelligenceService(session, user.id).acknowledge(project_id, alert_id)


@router.post(
    "/alerts/{alert_id}/read",
    response_model=AlertRead,
    dependencies=[Depends(require_csrf)],
)
async def mark_read(
    project_id: UUID, alert_id: UUID, user: CurrentUser, session: Session
) -> AlertRead:
    return await ProjectIntelligenceService(session, user.id).mark_read(project_id, alert_id)
