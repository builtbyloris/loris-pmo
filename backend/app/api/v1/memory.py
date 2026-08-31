from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import authorize_project_module
from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.memory import DecisionStatus, MeetingStatus, MemorySource, ProjectLogType
from app.schemas.memory import (
    ActionItemCreate,
    ActionItemRead,
    ActionItemUpdate,
    ActivityList,
    DecisionCreate,
    DecisionList,
    DecisionRead,
    DecisionUpdate,
    MeetingCreate,
    MeetingList,
    MeetingRead,
    MeetingUpdate,
    MemorySummary,
    ProjectLogCreate,
    ProjectLogList,
    ProjectLogRead,
    ProjectLogUpdate,
    SortOrder,
)
from app.services.authorization import Capability
from app.services.memory import MemoryService

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["project-memory"],
    dependencies=[
        Depends(
            authorize_project_module(
                Capability.MEETINGS_READ,
                Capability.MEETINGS_MANAGE,
                path_overrides={"/activity": Capability.AUDIT_READ},
            )
        )
    ],
)
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/log", response_model=ProjectLogList)
async def list_log(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    entry_type: Annotated[ProjectLogType | None, Query(alias="type")] = None,
    source: MemorySource | None = None,
    sort_order: SortOrder = SortOrder.DESC,
) -> ProjectLogList:
    return await MemoryService(session, user.id).list_logs(
        project_id, search=search, entry_type=entry_type, source=source, sort_order=sort_order
    )


@router.post(
    "/log",
    response_model=ProjectLogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_log(
    project_id: UUID, data: ProjectLogCreate, user: CurrentUser, session: Session
) -> ProjectLogRead:
    return await MemoryService(session, user.id).create_log(project_id, data)


@router.patch(
    "/log/{entry_id}", response_model=ProjectLogRead, dependencies=[Depends(require_csrf)]
)
async def update_log(
    project_id: UUID, entry_id: UUID, data: ProjectLogUpdate, user: CurrentUser, session: Session
) -> ProjectLogRead:
    return await MemoryService(session, user.id).update_log(project_id, entry_id, data)


@router.get("/meetings", response_model=MeetingList)
async def list_meetings(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    meeting_status: Annotated[MeetingStatus | None, Query(alias="status")] = None,
    sort_order: SortOrder = SortOrder.DESC,
) -> MeetingList:
    return await MemoryService(session, user.id).list_meetings(
        project_id, search=search, status=meeting_status, sort_order=sort_order
    )


@router.post(
    "/meetings",
    response_model=MeetingRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_meeting(
    project_id: UUID, data: MeetingCreate, user: CurrentUser, session: Session
) -> MeetingRead:
    return await MemoryService(session, user.id).create_meeting(project_id, data)


@router.patch(
    "/meetings/{meeting_id}", response_model=MeetingRead, dependencies=[Depends(require_csrf)]
)
async def update_meeting(
    project_id: UUID, meeting_id: UUID, data: MeetingUpdate, user: CurrentUser, session: Session
) -> MeetingRead:
    return await MemoryService(session, user.id).update_meeting(project_id, meeting_id, data)


@router.post(
    "/meetings/{meeting_id}/action-items",
    response_model=ActionItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_action_item(
    project_id: UUID, meeting_id: UUID, data: ActionItemCreate, user: CurrentUser, session: Session
) -> ActionItemRead:
    return await MemoryService(session, user.id).create_action_item(project_id, meeting_id, data)


@router.patch(
    "/meetings/{meeting_id}/action-items/{item_id}",
    response_model=ActionItemRead,
    dependencies=[Depends(require_csrf)],
)
async def update_action_item(
    project_id: UUID,
    meeting_id: UUID,
    item_id: UUID,
    data: ActionItemUpdate,
    user: CurrentUser,
    session: Session,
) -> ActionItemRead:
    return await MemoryService(session, user.id).update_action_item(
        project_id, meeting_id, item_id, data
    )


@router.get("/decisions", response_model=DecisionList)
async def list_decisions(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    decision_status: Annotated[DecisionStatus | None, Query(alias="status")] = None,
    sort_order: SortOrder = SortOrder.DESC,
) -> DecisionList:
    return await MemoryService(session, user.id).list_decisions(
        project_id, search=search, status=decision_status, sort_order=sort_order
    )


@router.post(
    "/decisions",
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_decision(
    project_id: UUID, data: DecisionCreate, user: CurrentUser, session: Session
) -> DecisionRead:
    return await MemoryService(session, user.id).create_decision(project_id, data)


@router.patch(
    "/decisions/{decision_id}", response_model=DecisionRead, dependencies=[Depends(require_csrf)]
)
async def update_decision(
    project_id: UUID, decision_id: UUID, data: DecisionUpdate, user: CurrentUser, session: Session
) -> DecisionRead:
    return await MemoryService(session, user.id).update_decision(project_id, decision_id, data)


@router.get("/activity", response_model=ActivityList)
async def activity(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    action: Annotated[str | None, Query(max_length=80)] = None,
    entity_type: Annotated[str | None, Query(max_length=80)] = None,
    sort_order: SortOrder = SortOrder.DESC,
) -> ActivityList:
    return await MemoryService(session, user.id).activity(
        project_id, search=search, action=action, entity_type=entity_type, sort_order=sort_order
    )


@router.get("/memory/summary", response_model=MemorySummary)
async def summary(project_id: UUID, user: CurrentUser, session: Session) -> MemorySummary:
    return await MemoryService(session, user.id).summary(project_id)
