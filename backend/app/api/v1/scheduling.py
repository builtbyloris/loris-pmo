from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import authorize_project_module
from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.schemas.scheduling import (
    BaselineCreate,
    BaselineRead,
    CriticalPathRead,
    ScheduleApplyRead,
    ScheduleApplyRequest,
    ScheduleChangeRequest,
    SchedulePreviewRead,
    ScheduleRead,
)
from app.services.authorization import Capability
from app.services.scheduling import SchedulingService

router = APIRouter(
    prefix="/projects/{project_id}/schedule",
    tags=["scheduling"],
    dependencies=[
        Depends(authorize_project_module(Capability.SCHEDULE_READ, Capability.SCHEDULE_MANAGE))
    ],
)
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=ScheduleRead)
async def get_schedule(project_id: UUID, user: CurrentUser, session: Session):
    return await SchedulingService(session, user.id).schedule(project_id)


@router.get("/critical-path", response_model=CriticalPathRead)
async def get_critical_path(project_id: UUID, user: CurrentUser, session: Session):
    return (await SchedulingService(session, user.id).schedule(project_id)).critical_path


@router.get("/baseline", response_model=BaselineRead | None)
async def get_baseline(project_id: UUID, user: CurrentUser, session: Session):
    return await SchedulingService(session, user.id).baseline(project_id)


@router.post(
    "/baseline",
    response_model=BaselineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_baseline(
    project_id: UUID, data: BaselineCreate, user: CurrentUser, session: Session
):
    return await SchedulingService(session, user.id).create_baseline(
        project_id, replace=data.replace
    )


@router.post("/preview", response_model=SchedulePreviewRead, dependencies=[Depends(require_csrf)])
async def preview(
    project_id: UUID, data: ScheduleChangeRequest, user: CurrentUser, session: Session
):
    return await SchedulingService(session, user.id).preview(project_id, data)


@router.post("/apply", response_model=ScheduleApplyRead, dependencies=[Depends(require_csrf)])
async def apply(project_id: UUID, data: ScheduleApplyRequest, user: CurrentUser, session: Session):
    return await SchedulingService(session, user.id).apply(project_id, data)
