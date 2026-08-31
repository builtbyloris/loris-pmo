from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.milestone import Milestone
from app.models.people import ProjectMember
from app.models.project import Project
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.task_dependency import DependencyType, TaskDependency
from app.schemas.projects import SortOrder
from app.schemas.work_planning import TaskSort
from app.services.authorization import accessible_project_ids


class WorkPlanningRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    def _owned_projects(self) -> Select[tuple[Project]]:
        return select(Project).where(Project.id.in_(accessible_project_ids(self.owner_user_id)))

    async def get_project(self, project_id: UUID) -> Project | None:
        result = await self.session.execute(self._owned_projects().where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def get_task(
        self, project_id: UUID, task_id: UUID, *, include_archived: bool = False
    ) -> Task | None:
        query = (
            select(Task)
            .options(selectinload(Task.assignees))
            .join(Project, Project.id == Task.project_id)
            .where(
                Task.id == task_id,
                Task.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
            )
        )
        if not include_archived:
            query = query.where(Task.archived_at.is_(None))
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_tasks(
        self,
        project_id: UUID,
        *,
        search: str | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        milestone_id: UUID | None = None,
        include_archived: bool = False,
        sort_by: TaskSort = TaskSort.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[Task], int]:
        filters = [
            Task.project_id == project_id,
            Project.id.in_(accessible_project_ids(self.owner_user_id)),
        ]
        if not include_archived:
            filters.append(Task.archived_at.is_(None))
        if status:
            filters.append(Task.status == status)
        if priority:
            filters.append(Task.priority == priority)
        if milestone_id:
            filters.append(Task.milestone_id == milestone_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(or_(Task.title.ilike(term), Task.description.ilike(term)))
        count = (
            await self.session.execute(select(func.count(Task.id)).join(Project).where(*filters))
        ).scalar_one()
        sort_column = {
            TaskSort.UPDATED_AT: Task.updated_at,
            TaskSort.CREATED_AT: Task.created_at,
            TaskSort.TITLE: Task.title,
            TaskSort.START_DATE: Task.start_date,
            TaskSort.DUE_DATE: Task.due_date,
            TaskSort.PRIORITY: Task.priority,
            TaskSort.STATUS: Task.status,
        }[sort_by]
        ordering = sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()
        result = await self.session.execute(
            select(Task)
            .options(selectinload(Task.assignees))
            .join(Project)
            .where(*filters)
            .order_by(ordering, Task.id)
        )
        return list(result.scalars()), int(count)

    async def get_members(self, project_id: UUID, member_ids: list[UUID]) -> list[ProjectMember]:
        if not member_ids:
            return []
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.id.in_(member_ids),
            )
        )
        return list(result.scalars())

    async def task_has_children(self, project_id: UUID, task_id: UUID) -> bool:
        count = (
            await self.session.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == project_id,
                    Task.parent_task_id == task_id,
                    Task.archived_at.is_(None),
                )
            )
        ).scalar_one()
        return bool(count)

    async def get_milestone(self, project_id: UUID, milestone_id: UUID) -> Milestone | None:
        result = await self.session.execute(
            select(Milestone)
            .join(Project, Project.id == Milestone.project_id)
            .where(
                Milestone.id == milestone_id,
                Milestone.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
            )
        )
        return result.scalar_one_or_none()

    async def list_milestones(self, project_id: UUID) -> list[Milestone]:
        result = await self.session.execute(
            select(Milestone)
            .join(Project, Project.id == Milestone.project_id)
            .where(
                Milestone.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
            )
            .order_by(Milestone.due_date.asc().nulls_last(), Milestone.created_at)
        )
        return list(result.scalars())

    async def get_dependency(self, project_id: UUID, dependency_id: UUID) -> TaskDependency | None:
        result = await self.session.execute(
            select(TaskDependency)
            .join(Project, Project.id == TaskDependency.project_id)
            .where(
                TaskDependency.id == dependency_id,
                TaskDependency.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
            )
        )
        return result.scalar_one_or_none()

    async def list_dependencies(
        self, project_id: UUID, *, active_only: bool = True
    ) -> list[TaskDependency]:
        source = aliased(Task)
        target = aliased(Task)
        query = (
            select(TaskDependency)
            .join(Project, Project.id == TaskDependency.project_id)
            .join(
                source,
                (source.project_id == TaskDependency.project_id)
                & (source.id == TaskDependency.source_task_id),
            )
            .join(
                target,
                (target.project_id == TaskDependency.project_id)
                & (target.id == TaskDependency.target_task_id),
            )
            .where(
                TaskDependency.project_id == project_id,
                Project.id.in_(accessible_project_ids(self.owner_user_id)),
            )
        )
        if active_only:
            query = query.where(source.archived_at.is_(None), target.archived_at.is_(None))
        result = await self.session.execute(query.order_by(TaskDependency.created_at))
        return list(result.scalars())

    async def dependency_exists(
        self,
        project_id: UUID,
        source_task_id: UUID,
        target_task_id: UUID,
        dependency_type: DependencyType,
    ) -> bool:
        count = (
            await self.session.execute(
                select(func.count(TaskDependency.id)).where(
                    TaskDependency.project_id == project_id,
                    TaskDependency.source_task_id == source_task_id,
                    TaskDependency.target_task_id == target_task_id,
                    TaskDependency.dependency_type == dependency_type,
                )
            )
        ).scalar_one()
        return bool(count)
