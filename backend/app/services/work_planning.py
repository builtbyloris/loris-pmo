from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.collaboration import (
    MembershipStatus,
    Notification,
    NotificationType,
    ProjectMembership,
)
from app.models.memory import MemoryEntityType, ProjectLogType
from app.models.milestone import Milestone, MilestoneStatus
from app.models.people import ProjectMember, TaskAssignee
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.task_dependency import DependencyType, TaskDependency
from app.repositories.work_planning import WorkPlanningRepository
from app.schemas.work_planning import (
    DependencyCreate,
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    TaskCreate,
    TaskList,
    TaskUpdate,
    WorkPlanningSummary,
)
from app.services.audit import AuditService
from app.services.memory import MemoryService


class WorkPlanningService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = WorkPlanningRepository(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def _project_or_404(self, project_id: UUID) -> Project:
        project = await self.repository.get_project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return project

    @staticmethod
    def _ensure_mutable(project: Project) -> None:
        if project.archived_at is not None:
            raise AppError(
                code="project_archived",
                message="Archived projects are read-only.",
                status_code=409,
            )

    async def _task_or_404(
        self, project_id: UUID, task_id: UUID, *, include_archived: bool = False
    ) -> Task:
        task = await self.repository.get_task(
            project_id, task_id, include_archived=include_archived
        )
        if task is None:
            raise AppError(code="task_not_found", message="Task not found.", status_code=404)
        return task

    async def _milestone_or_404(self, project_id: UUID, milestone_id: UUID) -> Milestone:
        milestone = await self.repository.get_milestone(project_id, milestone_id)
        if milestone is None:
            raise AppError(
                code="milestone_not_found", message="Milestone not found.", status_code=404
            )
        return milestone

    async def _commit(self, *, duplicate_dependency: bool = False) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if duplicate_dependency:
                raise AppError(
                    code="dependency_exists",
                    message="This task dependency already exists.",
                    status_code=409,
                ) from exc
            raise

    async def _validate_task_links(
        self,
        project_id: UUID,
        *,
        task_id: UUID | None,
        parent_task_id: UUID | None,
        milestone_id: UUID | None,
    ) -> None:
        if parent_task_id is not None:
            if task_id == parent_task_id:
                raise AppError(
                    code="invalid_parent_task",
                    message="A task cannot be its own parent.",
                    status_code=422,
                )
            parent = await self.repository.get_task(project_id, parent_task_id)
            if parent is None:
                raise AppError(
                    code="parent_task_not_found",
                    message="Parent task not found in this project.",
                    status_code=422,
                )
            if parent.parent_task_id is not None:
                raise AppError(
                    code="nested_subtask_not_supported",
                    message="Only one level of subtasks is supported.",
                    status_code=422,
                )
            if task_id and await self.repository.task_has_children(project_id, task_id):
                raise AppError(
                    code="task_with_children_cannot_be_subtask",
                    message="A task with subtasks cannot become a subtask.",
                    status_code=409,
                )
        if milestone_id is not None:
            if await self.repository.get_milestone(project_id, milestone_id) is None:
                raise AppError(
                    code="milestone_not_found",
                    message="Milestone not found in this project.",
                    status_code=422,
                )

    async def _validate_assignees(self, project_id: UUID, member_ids: list[UUID]) -> None:
        members = await self.repository.get_members(project_id, member_ids)
        if len(members) != len(member_ids):
            raise AppError(
                code="invalid_task_assignee",
                message="Every assignee must be a member of this project.",
                status_code=422,
            )

    @staticmethod
    def _set_assignees(task: Task, member_ids: list[UUID]) -> None:
        task.assignees[:] = [
            TaskAssignee(
                project_id=task.project_id,
                task_id=task.id,
                project_member_id=member_id,
            )
            for member_id in member_ids
        ]

    async def _notify_task_assignees(
        self, project_id: UUID, task: Task, member_ids: list[UUID]
    ) -> None:
        if not member_ids:
            return
        recipients = list(
            (
                await self.session.scalars(
                    select(ProjectMembership.user_id)
                    .join(
                        ProjectMember,
                        (ProjectMember.project_id == ProjectMembership.project_id)
                        & (ProjectMember.person_id == ProjectMembership.person_id),
                    )
                    .where(
                        ProjectMembership.project_id == project_id,
                        ProjectMembership.status == MembershipStatus.ACTIVE,
                        ProjectMembership.user_id != self.owner_user_id,
                        ProjectMember.id.in_(member_ids),
                    )
                    .limit(100)
                )
            ).all()
        )
        for recipient in recipients:
            self.session.add(
                Notification(
                    user_id=recipient,
                    project_id=project_id,
                    type=NotificationType.TASK_ASSIGNED,
                    title="Task assigned",
                    message="You were assigned to a project task.",
                    entity_type="TASK",
                    entity_id=task.id,
                )
            )

    async def create_task(self, project_id: UUID, data: TaskCreate) -> Task:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_task_links(
            project_id,
            task_id=None,
            parent_task_id=data.parent_task_id,
            milestone_id=data.milestone_id,
        )
        values = data.model_dump()
        assignee_ids = values.pop("assignee_ids")
        await self._validate_assignees(project_id, assignee_ids)
        task = Task(project_id=project_id, **values)
        task.assignees = []
        self.session.add(task)
        await self.session.flush()
        self._set_assignees(task, assignee_ids)
        await self._notify_task_assignees(project_id, task, assignee_ids)
        self.audit.record(
            project_id=project_id,
            action="task.created",
            entity_type="task",
            entity_id=task.id,
            changes={"title": task.title, "status": task.status.value},
        )
        if assignee_ids:
            self.audit.record(
                project_id=project_id,
                action="task.assignee_changed",
                entity_type="task",
                entity_id=task.id,
                changes={"from": [], "to": sorted(str(value) for value in assignee_ids)},
            )
        await self._commit()
        await self.session.refresh(task)
        await self.session.refresh(task, attribute_names=["assignees"])
        return task

    async def get_task(self, project_id: UUID, task_id: UUID) -> Task:
        await self._project_or_404(project_id)
        return await self._task_or_404(project_id, task_id, include_archived=True)

    async def list_tasks(self, project_id: UUID, **filters) -> TaskList:
        await self._project_or_404(project_id)
        tasks, total = await self.repository.list_tasks(project_id, **filters)
        return TaskList(items=tasks, total=total)

    async def update_task(self, project_id: UUID, task_id: UUID, data: TaskUpdate) -> Task:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        task = await self._task_or_404(project_id, task_id)
        changes = data.model_dump(exclude_unset=True)
        assignee_ids = changes.pop("assignee_ids", None)
        if not changes and assignee_ids is None:
            return task
        if assignee_ids is not None:
            await self._validate_assignees(project_id, assignee_ids)
        final_start = changes.get("start_date", task.start_date)
        final_due = changes.get("due_date", task.due_date)
        if final_start and final_due and final_due < final_start:
            raise AppError(
                code="invalid_task_dates",
                message="Due date must not precede start date.",
                status_code=422,
            )
        await self._validate_task_links(
            project_id,
            task_id=task_id,
            parent_task_id=changes.get("parent_task_id", task.parent_task_id),
            milestone_id=changes.get("milestone_id", task.milestone_id),
        )
        if changes.get("status") == TaskStatus.DONE:
            changes["completion_percentage"] = 100
        before_status = task.status
        before = {
            key: str(getattr(task, key)) if getattr(task, key) is not None else None
            for key in changes
        }
        for key, value in changes.items():
            setattr(task, key, value)
        if assignee_ids is not None:
            previous_ids = set(task.assignee_ids)
            before_assignees = sorted(str(value) for value in previous_ids)
            next_assignees = sorted(str(value) for value in assignee_ids)
            if before_assignees != next_assignees:
                self._set_assignees(task, assignee_ids)
                await self._notify_task_assignees(
                    project_id, task, [value for value in assignee_ids if value not in previous_ids]
                )
                self.audit.record(
                    project_id=project_id,
                    action="task.assignee_changed",
                    entity_type="task",
                    entity_id=task.id,
                    changes={"from": before_assignees, "to": next_assignees},
                )
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="task.updated",
            entity_type="task",
            entity_id=task.id,
            changes={"before": before, "fields": list(changes)},
        )
        if task.status != before_status:
            self.audit.record(
                project_id=project_id,
                action="task.status_changed",
                entity_type="task",
                entity_id=task.id,
                changes={"from": before_status.value, "to": task.status.value},
            )
        await self._commit()
        await self.session.refresh(task)
        await self.session.refresh(task, attribute_names=["assignees"])
        return task

    async def archive_task(self, project_id: UUID, task_id: UUID) -> Task:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        task = await self._task_or_404(project_id, task_id, include_archived=True)
        if task.archived_at is None:
            if await self.repository.task_has_children(project_id, task_id):
                raise AppError(
                    code="task_has_subtasks",
                    message="Archive active subtasks before archiving their parent.",
                    status_code=409,
                )
            task.archived_at = datetime.now(UTC)
            self.audit.record(
                project_id=project_id,
                action="task.archived",
                entity_type="task",
                entity_id=task.id,
            )
            await self._commit()
        await self.session.refresh(task)
        await self.session.refresh(task, attribute_names=["assignees"])
        return task

    @staticmethod
    def _milestone_read(milestone: Milestone, tasks: list[Task]) -> MilestoneRead:
        linked = [
            task
            for task in tasks
            if task.milestone_id == milestone.id and task.status != TaskStatus.CANCELLED
        ]
        completed = [task for task in linked if task.status == TaskStatus.DONE]
        today = date.today()
        overdue = [
            task
            for task in linked
            if task.due_date and task.due_date < today and task.status != TaskStatus.DONE
        ]
        progress = (
            round(sum(task.completion_percentage for task in linked) / len(linked), 1)
            if linked
            else None
        )
        return MilestoneRead(
            id=milestone.id,
            project_id=milestone.project_id,
            title=milestone.title,
            description=milestone.description,
            due_date=milestone.due_date,
            status=milestone.status,
            notes=milestone.notes,
            progress=progress,
            linked_task_count=len(linked),
            completed_task_count=len(completed),
            overdue_task_count=len(overdue),
            created_at=milestone.created_at,
            updated_at=milestone.updated_at,
        )

    async def list_milestones(self, project_id: UUID) -> list[MilestoneRead]:
        await self._project_or_404(project_id)
        milestones = await self.repository.list_milestones(project_id)
        tasks, _ = await self.repository.list_tasks(project_id)
        return [self._milestone_read(milestone, tasks) for milestone in milestones]

    async def create_milestone(self, project_id: UUID, data: MilestoneCreate) -> MilestoneRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        milestone = Milestone(project_id=project_id, **data.model_dump())
        self.session.add(milestone)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="milestone.created",
            entity_type="milestone",
            entity_id=milestone.id,
            changes={"title": milestone.title},
        )
        await self._commit()
        await self.session.refresh(milestone)
        return self._milestone_read(milestone, [])

    async def update_milestone(
        self, project_id: UUID, milestone_id: UUID, data: MilestoneUpdate
    ) -> MilestoneRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        milestone = await self._milestone_or_404(project_id, milestone_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            tasks, _ = await self.repository.list_tasks(project_id)
            return self._milestone_read(milestone, tasks)
        before_status = milestone.status
        for key, value in changes.items():
            setattr(milestone, key, value)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="milestone.updated",
            entity_type="milestone",
            entity_id=milestone.id,
            changes={"fields": list(changes)},
        )
        if milestone.status == MilestoneStatus.COMPLETED and before_status != milestone.status:
            self.audit.record(
                project_id=project_id,
                action="milestone.completed",
                entity_type="milestone",
                entity_id=milestone.id,
            )
            MemoryService.record_system_log(
                self.session,
                actor_user_id=self.owner_user_id,
                project_id=project_id,
                entry_type=ProjectLogType.MILESTONE,
                title=f"Milestone completed: {milestone.title}",
                description=milestone.description,
                entity_type=MemoryEntityType.MILESTONE,
                entity_id=milestone.id,
            )
        await self._commit()
        await self.session.refresh(milestone)
        tasks, _ = await self.repository.list_tasks(project_id)
        return self._milestone_read(milestone, tasks)

    @staticmethod
    def _normalized_dependency(data: DependencyCreate) -> tuple[UUID, UUID, DependencyType]:
        source, target = data.source_task_id, data.target_task_id
        if data.dependency_type == DependencyType.RELATED_TO and source.int > target.int:
            source, target = target, source
        return source, target, data.dependency_type

    @staticmethod
    def _schedule_edge(dependency: TaskDependency | tuple[UUID, UUID, DependencyType]):
        if isinstance(dependency, TaskDependency):
            source, target, dependency_type = (
                dependency.source_task_id,
                dependency.target_task_id,
                dependency.dependency_type,
            )
        else:
            source, target, dependency_type = dependency
        if dependency_type == DependencyType.BLOCKS:
            return source, target
        if dependency_type == DependencyType.DEPENDS_ON:
            return target, source
        return None

    async def _would_create_cycle(
        self, project_id: UUID, candidate: tuple[UUID, UUID, DependencyType]
    ) -> bool:
        edge = self._schedule_edge(candidate)
        if edge is None:
            return False
        graph: dict[UUID, set[UUID]] = defaultdict(set)
        for dependency in await self.repository.list_dependencies(project_id):
            existing = self._schedule_edge(dependency)
            if existing:
                graph[existing[0]].add(existing[1])
        source, target = edge
        stack = [target]
        visited: set[UUID] = set()
        while stack:
            current = stack.pop()
            if current == source:
                return True
            if current not in visited:
                visited.add(current)
                stack.extend(graph[current])
        return False

    async def list_dependencies(self, project_id: UUID) -> list[TaskDependency]:
        await self._project_or_404(project_id)
        return await self.repository.list_dependencies(project_id)

    async def create_dependency(self, project_id: UUID, data: DependencyCreate) -> TaskDependency:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        source, target, dependency_type = self._normalized_dependency(data)
        if source == target:
            raise AppError(
                code="self_dependency",
                message="A task cannot depend on itself.",
                status_code=422,
            )
        if (
            await self.repository.get_task(project_id, source) is None
            or await self.repository.get_task(project_id, target) is None
        ):
            raise AppError(
                code="dependency_task_not_found",
                message="Both dependency tasks must belong to this project.",
                status_code=422,
            )
        if await self.repository.dependency_exists(project_id, source, target, dependency_type):
            raise AppError(
                code="dependency_exists",
                message="This task dependency already exists.",
                status_code=409,
            )
        candidate = (source, target, dependency_type)
        candidate_edge = self._schedule_edge(candidate)
        if candidate_edge and any(
            self._schedule_edge(existing) == candidate_edge
            for existing in await self.repository.list_dependencies(project_id)
        ):
            raise AppError(
                code="dependency_exists",
                message="This scheduling dependency already exists.",
                status_code=409,
            )
        if await self._would_create_cycle(project_id, candidate):
            raise AppError(
                code="dependency_cycle",
                message="This scheduling dependency would create a cycle.",
                status_code=409,
            )
        dependency = TaskDependency(
            project_id=project_id,
            source_task_id=source,
            target_task_id=target,
            dependency_type=dependency_type,
        )
        self.session.add(dependency)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="dependency.created",
            entity_type="task_dependency",
            entity_id=dependency.id,
            changes={
                "source_task_id": str(source),
                "target_task_id": str(target),
                "dependency_type": dependency_type.value,
            },
        )
        await self._commit(duplicate_dependency=True)
        await self.session.refresh(dependency)
        return dependency

    async def delete_dependency(self, project_id: UUID, dependency_id: UUID) -> None:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        dependency = await self.repository.get_dependency(project_id, dependency_id)
        if dependency is None:
            raise AppError(
                code="dependency_not_found", message="Dependency not found.", status_code=404
            )
        self.audit.record(
            project_id=project_id,
            action="dependency.removed",
            entity_type="task_dependency",
            entity_id=dependency.id,
        )
        await self.session.delete(dependency)
        await self._commit()

    async def summary(self, project_id: UUID) -> WorkPlanningSummary:
        await self._project_or_404(project_id)
        tasks, _ = await self.repository.list_tasks(project_id)
        today = date.today()
        completed = [task for task in tasks if task.status == TaskStatus.DONE]
        overdue = [
            task
            for task in tasks
            if task.due_date
            and task.due_date < today
            and task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
        ]
        eligible = [task for task in tasks if task.status != TaskStatus.CANCELLED]
        milestones = await self.repository.list_milestones(project_id)
        horizon = today + timedelta(days=30)
        upcoming = [
            milestone
            for milestone in milestones
            if milestone.due_date
            and today <= milestone.due_date <= horizon
            and milestone.status != MilestoneStatus.COMPLETED
        ]
        progress = (
            round(sum(task.completion_percentage for task in eligible) / len(eligible), 1)
            if eligible
            else None
        )
        return WorkPlanningSummary(
            total_tasks=len(tasks),
            completed_tasks=len(completed),
            overdue_tasks=len(overdue),
            upcoming_milestones=len(upcoming),
            progress=progress,
        )
