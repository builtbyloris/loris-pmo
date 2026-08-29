from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.control import RiskSeverity
from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.control import ChangeStatus, ControlPriority, IssueStatus, RiskStatus
from app.schemas.control import (
    ChangeCreate,
    ChangeDecision,
    ChangeList,
    ChangeRead,
    ChangeSort,
    ChangeUpdate,
    ControlSummary,
    IssueCreate,
    IssueList,
    IssueRead,
    IssueResolution,
    IssueSort,
    IssueUpdate,
    RiskCreate,
    RiskList,
    RiskRead,
    RiskSort,
    RiskUpdate,
    SortOrder,
)
from app.services.control import ControlService

router = APIRouter(prefix="/projects/{project_id}", tags=["control"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/risks", response_model=RiskList)
async def list_risks(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    risk_status: Annotated[RiskStatus | None, Query(alias="status")] = None,
    severity: RiskSeverity | None = None,
    sort_by: RiskSort = RiskSort.UPDATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
) -> RiskList:
    return await ControlService(session, user.id).list_risks(
        project_id,
        search=search,
        status=risk_status,
        severity=severity,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/risks",
    response_model=RiskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_risk(
    project_id: UUID, data: RiskCreate, user: CurrentUser, session: Session
) -> RiskRead:
    return await ControlService(session, user.id).create_risk(project_id, data)


@router.get("/risks/{risk_id}", response_model=RiskRead)
async def get_risk(
    project_id: UUID, risk_id: UUID, user: CurrentUser, session: Session
) -> RiskRead:
    return await ControlService(session, user.id).get_risk(project_id, risk_id)


@router.patch("/risks/{risk_id}", response_model=RiskRead, dependencies=[Depends(require_csrf)])
async def update_risk(
    project_id: UUID, risk_id: UUID, data: RiskUpdate, user: CurrentUser, session: Session
) -> RiskRead:
    return await ControlService(session, user.id).update_risk(project_id, risk_id, data)


@router.post(
    "/risks/{risk_id}/close", response_model=RiskRead, dependencies=[Depends(require_csrf)]
)
async def close_risk(
    project_id: UUID, risk_id: UUID, user: CurrentUser, session: Session
) -> RiskRead:
    return await ControlService(session, user.id).close_risk(project_id, risk_id)


@router.get("/issues", response_model=IssueList)
async def list_issues(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    issue_status: Annotated[IssueStatus | None, Query(alias="status")] = None,
    priority: ControlPriority | None = None,
    sort_by: IssueSort = IssueSort.UPDATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
) -> IssueList:
    return await ControlService(session, user.id).list_issues(
        project_id,
        search=search,
        status=issue_status,
        priority=priority,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/issues",
    response_model=IssueRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_issue(
    project_id: UUID, data: IssueCreate, user: CurrentUser, session: Session
) -> IssueRead:
    return await ControlService(session, user.id).create_issue(project_id, data)


@router.get("/issues/{issue_id}", response_model=IssueRead)
async def get_issue(
    project_id: UUID, issue_id: UUID, user: CurrentUser, session: Session
) -> IssueRead:
    return await ControlService(session, user.id).get_issue(project_id, issue_id)


@router.patch("/issues/{issue_id}", response_model=IssueRead, dependencies=[Depends(require_csrf)])
async def update_issue(
    project_id: UUID, issue_id: UUID, data: IssueUpdate, user: CurrentUser, session: Session
) -> IssueRead:
    return await ControlService(session, user.id).update_issue(project_id, issue_id, data)


@router.post(
    "/issues/{issue_id}/resolve", response_model=IssueRead, dependencies=[Depends(require_csrf)]
)
async def resolve_issue(
    project_id: UUID, issue_id: UUID, data: IssueResolution, user: CurrentUser, session: Session
) -> IssueRead:
    return await ControlService(session, user.id).resolve_issue(project_id, issue_id, data)


@router.post(
    "/issues/{issue_id}/close", response_model=IssueRead, dependencies=[Depends(require_csrf)]
)
async def close_issue(
    project_id: UUID, issue_id: UUID, user: CurrentUser, session: Session
) -> IssueRead:
    return await ControlService(session, user.id).close_issue(project_id, issue_id)


@router.get("/changes", response_model=ChangeList)
async def list_changes(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    change_status: Annotated[ChangeStatus | None, Query(alias="status")] = None,
    sort_by: ChangeSort = ChangeSort.UPDATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
) -> ChangeList:
    return await ControlService(session, user.id).list_changes(
        project_id,
        search=search,
        status=change_status,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/changes",
    response_model=ChangeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_change(
    project_id: UUID, data: ChangeCreate, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).create_change(project_id, data)


@router.get("/changes/{change_id}", response_model=ChangeRead)
async def get_change(
    project_id: UUID, change_id: UUID, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).get_change(project_id, change_id)


@router.patch(
    "/changes/{change_id}", response_model=ChangeRead, dependencies=[Depends(require_csrf)]
)
async def update_change(
    project_id: UUID, change_id: UUID, data: ChangeUpdate, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).update_change(project_id, change_id, data)


@router.post(
    "/changes/{change_id}/submit", response_model=ChangeRead, dependencies=[Depends(require_csrf)]
)
async def submit_change(
    project_id: UUID, change_id: UUID, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).submit_change(project_id, change_id)


@router.post(
    "/changes/{change_id}/approve", response_model=ChangeRead, dependencies=[Depends(require_csrf)]
)
async def approve_change(
    project_id: UUID, change_id: UUID, data: ChangeDecision, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).approve_change(project_id, change_id, data)


@router.post(
    "/changes/{change_id}/reject", response_model=ChangeRead, dependencies=[Depends(require_csrf)]
)
async def reject_change(
    project_id: UUID, change_id: UUID, data: ChangeDecision, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).reject_change(project_id, change_id, data)


@router.post(
    "/changes/{change_id}/implement",
    response_model=ChangeRead,
    dependencies=[Depends(require_csrf)],
)
async def implement_change(
    project_id: UUID, change_id: UUID, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).implement_change(project_id, change_id)


@router.post(
    "/changes/{change_id}/cancel", response_model=ChangeRead, dependencies=[Depends(require_csrf)]
)
async def cancel_change(
    project_id: UUID, change_id: UUID, user: CurrentUser, session: Session
) -> ChangeRead:
    return await ControlService(session, user.id).cancel_change(project_id, change_id)


@router.get("/control/summary", response_model=ControlSummary)
async def control_summary(project_id: UUID, user: CurrentUser, session: Session) -> ControlSummary:
    return await ControlService(session, user.id).summary(project_id)
