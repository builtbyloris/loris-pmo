from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.task import TaskPriority, TaskStatus
from app.schemas.projects import SortOrder
from app.schemas.work_planning import (
    DependencyCreate,
    DependencyRead,
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    TaskCreate,
    TaskList,
    TaskRead,
    TaskSort,
    TaskUpdate,
    WorkPlanningSummary,
)
from app.services.work_planning import WorkPlanningService

router = APIRouter(prefix="/projects/{project_id}", tags=["work-planning"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/tasks", response_model=TaskList)
async def list_tasks(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=200)] = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    milestone_id: UUID | None = None,
    include_archived: bool = False,
    sort_by: TaskSort = TaskSort.UPDATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
) -> TaskList:
    return await WorkPlanningService(session, user.id).list_tasks(
        project_id,
        search=search,
        status=task_status,
        priority=priority,
        milestone_id=milestone_id,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_task(
    project_id: UUID, data: TaskCreate, user: CurrentUser, session: Session
) -> TaskRead:
    return TaskRead.model_validate(
        await WorkPlanningService(session, user.id).create_task(project_id, data)
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    project_id: UUID, task_id: UUID, user: CurrentUser, session: Session
) -> TaskRead:
    return TaskRead.model_validate(
        await WorkPlanningService(session, user.id).get_task(project_id, task_id)
    )


@router.patch("/tasks/{task_id}", response_model=TaskRead, dependencies=[Depends(require_csrf)])
async def update_task(
    project_id: UUID,
    task_id: UUID,
    data: TaskUpdate,
    user: CurrentUser,
    session: Session,
) -> TaskRead:
    return TaskRead.model_validate(
        await WorkPlanningService(session, user.id).update_task(project_id, task_id, data)
    )


@router.post(
    "/tasks/{task_id}/archive",
    response_model=TaskRead,
    dependencies=[Depends(require_csrf)],
)
async def archive_task(
    project_id: UUID, task_id: UUID, user: CurrentUser, session: Session
) -> TaskRead:
    return TaskRead.model_validate(
        await WorkPlanningService(session, user.id).archive_task(project_id, task_id)
    )


@router.get("/milestones", response_model=list[MilestoneRead])
async def list_milestones(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[MilestoneRead]:
    return await WorkPlanningService(session, user.id).list_milestones(project_id)


@router.post(
    "/milestones",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_milestone(
    project_id: UUID, data: MilestoneCreate, user: CurrentUser, session: Session
) -> MilestoneRead:
    return await WorkPlanningService(session, user.id).create_milestone(project_id, data)


@router.patch(
    "/milestones/{milestone_id}",
    response_model=MilestoneRead,
    dependencies=[Depends(require_csrf)],
)
async def update_milestone(
    project_id: UUID,
    milestone_id: UUID,
    data: MilestoneUpdate,
    user: CurrentUser,
    session: Session,
) -> MilestoneRead:
    return await WorkPlanningService(session, user.id).update_milestone(
        project_id, milestone_id, data
    )


@router.get("/task-dependencies", response_model=list[DependencyRead])
async def list_dependencies(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[DependencyRead]:
    return [
        DependencyRead.model_validate(item)
        for item in await WorkPlanningService(session, user.id).list_dependencies(project_id)
    ]


@router.post(
    "/task-dependencies",
    response_model=DependencyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_dependency(
    project_id: UUID, data: DependencyCreate, user: CurrentUser, session: Session
) -> DependencyRead:
    return DependencyRead.model_validate(
        await WorkPlanningService(session, user.id).create_dependency(project_id, data)
    )


@router.delete(
    "/task-dependencies/{dependency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_dependency(
    project_id: UUID, dependency_id: UUID, user: CurrentUser, session: Session
) -> None:
    await WorkPlanningService(session, user.id).delete_dependency(project_id, dependency_id)


@router.get("/work-planning/summary", response_model=WorkPlanningSummary)
async def work_planning_summary(
    project_id: UUID, user: CurrentUser, session: Session
) -> WorkPlanningSummary:
    return await WorkPlanningService(session, user.id).summary(project_id)
