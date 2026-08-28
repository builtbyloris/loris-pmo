from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.project import ProjectPriority, ProjectStatus
from app.schemas.projects import (
    ObjectiveCreate,
    ObjectiveRead,
    ObjectiveUpdate,
    ProjectCreate,
    ProjectDetail,
    ProjectList,
    ProjectSort,
    ProjectUpdate,
    SortOrder,
    SuccessCriterionCreate,
    SuccessCriterionRead,
    SuccessCriterionUpdate,
)
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=ProjectList)
async def list_projects(
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=200)] = None,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    priority: ProjectPriority | None = None,
    include_archived: bool = False,
    sort_by: ProjectSort = ProjectSort.UPDATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
) -> ProjectList:
    return await ProjectService(session, user.id).list(
        search=search,
        status=project_status,
        priority=priority,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "",
    response_model=ProjectDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_project(data: ProjectCreate, user: CurrentUser, session: Session) -> ProjectDetail:
    project = await ProjectService(session, user.id).create(data)
    return ProjectDetail.model_validate(project)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: UUID, user: CurrentUser, session: Session) -> ProjectDetail:
    project = await ProjectService(session, user.id).get(project_id)
    return ProjectDetail.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectDetail, dependencies=[Depends(require_csrf)])
async def update_project(
    project_id: UUID, data: ProjectUpdate, user: CurrentUser, session: Session
) -> ProjectDetail:
    project = await ProjectService(session, user.id).update(project_id, data)
    return ProjectDetail.model_validate(project)


@router.post(
    "/{project_id}/archive", response_model=ProjectDetail, dependencies=[Depends(require_csrf)]
)
async def archive_project(project_id: UUID, user: CurrentUser, session: Session) -> ProjectDetail:
    project = await ProjectService(session, user.id).archive(project_id)
    return ProjectDetail.model_validate(project)


@router.get("/{project_id}/objectives", response_model=list[ObjectiveRead])
async def list_objectives(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[ObjectiveRead]:
    return [
        ObjectiveRead.model_validate(item)
        for item in await ProjectService(session, user.id).list_objectives(project_id)
    ]


@router.post(
    "/{project_id}/objectives",
    response_model=ObjectiveRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_objective(
    project_id: UUID, data: ObjectiveCreate, user: CurrentUser, session: Session
) -> ObjectiveRead:
    objective = await ProjectService(session, user.id).create_objective(project_id, data)
    return ObjectiveRead.model_validate(objective)


@router.patch(
    "/{project_id}/objectives/{objective_id}",
    response_model=ObjectiveRead,
    dependencies=[Depends(require_csrf)],
)
async def update_objective(
    project_id: UUID,
    objective_id: UUID,
    data: ObjectiveUpdate,
    user: CurrentUser,
    session: Session,
) -> ObjectiveRead:
    objective = await ProjectService(session, user.id).update_objective(
        project_id, objective_id, data
    )
    return ObjectiveRead.model_validate(objective)


@router.delete(
    "/{project_id}/objectives/{objective_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_objective(
    project_id: UUID, objective_id: UUID, user: CurrentUser, session: Session
) -> None:
    await ProjectService(session, user.id).delete_objective(project_id, objective_id)


@router.get("/{project_id}/success-criteria", response_model=list[SuccessCriterionRead])
async def list_criteria(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[SuccessCriterionRead]:
    return [
        SuccessCriterionRead.model_validate(item)
        for item in await ProjectService(session, user.id).list_criteria(project_id)
    ]


@router.post(
    "/{project_id}/success-criteria",
    response_model=SuccessCriterionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_criterion(
    project_id: UUID, data: SuccessCriterionCreate, user: CurrentUser, session: Session
) -> SuccessCriterionRead:
    criterion = await ProjectService(session, user.id).create_criterion(project_id, data)
    return SuccessCriterionRead.model_validate(criterion)


@router.patch(
    "/{project_id}/success-criteria/{criterion_id}",
    response_model=SuccessCriterionRead,
    dependencies=[Depends(require_csrf)],
)
async def update_criterion(
    project_id: UUID,
    criterion_id: UUID,
    data: SuccessCriterionUpdate,
    user: CurrentUser,
    session: Session,
) -> SuccessCriterionRead:
    criterion = await ProjectService(session, user.id).update_criterion(
        project_id, criterion_id, data
    )
    return SuccessCriterionRead.model_validate(criterion)


@router.delete(
    "/{project_id}/success-criteria/{criterion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_criterion(
    project_id: UUID, criterion_id: UUID, user: CurrentUser, session: Session
) -> None:
    await ProjectService(session, user.id).delete_criterion(project_id, criterion_id)
