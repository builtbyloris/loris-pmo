from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.scheduling import ScheduleTask, calculate_cpm, propagate_finish_to_start
from app.core.errors import AppError
from app.models.memory import MemorySource, ProjectLogEntry, ProjectLogType
from app.models.project import Project
from app.models.scheduling import ScheduleBaseline, ScheduleBaselineMilestone, ScheduleBaselineTask
from app.models.task import Task, TaskStatus
from app.models.task_dependency import DependencyType, TaskDependency
from app.repositories.work_planning import WorkPlanningRepository
from app.schemas.scheduling import (
    AffectedTaskRead,
    BaselineRead,
    CriticalPathRead,
    DeadlineImpactRead,
    DeadlineStatus,
    ScheduleApplyRead,
    ScheduleApplyRequest,
    ScheduleChangeRequest,
    ScheduleDependency,
    ScheduleMilestoneRead,
    SchedulePreviewRead,
    ScheduleRead,
    ScheduleTaskRead,
)
from app.services.audit import AuditService


class SchedulingService:
    """Backend-owned V2.2 scheduling calculations and confirmed transactional apply."""

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self.work = WorkPlanningRepository(session, user_id)
        self.audit = AuditService(session, user_id)

    async def _project(self, project_id: UUID) -> Project:
        project = await self.work.get_project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return project

    async def _data(self, project_id: UUID):
        project = await self._project(project_id)
        tasks, _ = await self.work.list_tasks(project_id)
        milestones = await self.work.list_milestones(project_id)
        dependencies = await self.work.list_dependencies(project_id)
        baseline = (
            await self.session.execute(
                select(ScheduleBaseline)
                .options(
                    selectinload(ScheduleBaseline.tasks), selectinload(ScheduleBaseline.milestones)
                )
                .where(ScheduleBaseline.project_id == project_id)
            )
        ).scalar_one_or_none()
        return project, tasks, milestones, dependencies, baseline

    @staticmethod
    def edges(dependencies: list[TaskDependency]) -> set[tuple[UUID, UUID]]:
        result = set()
        for item in dependencies:
            if item.dependency_type == DependencyType.BLOCKS:
                result.add((item.source_task_id, item.target_task_id))
            elif item.dependency_type == DependencyType.DEPENDS_ON:
                result.add((item.target_task_id, item.source_task_id))
        return result

    @staticmethod
    def _schedule_tasks(tasks: list[Task]) -> list[ScheduleTask]:
        return [
            ScheduleTask(item.id, item.start_date, item.due_date, item.milestone_id)
            for item in tasks
            if item.status != TaskStatus.CANCELLED
        ]

    @staticmethod
    def _fingerprint(project: Project, tasks, milestones, dependencies, baseline) -> str:
        payload = {
            "project": [
                str(project.id),
                str(project.target_end_date),
                project.updated_at.isoformat(),
            ],
            "tasks": sorted(
                (str(t.id), str(t.start_date), str(t.due_date), t.updated_at.isoformat())
                for t in tasks
            ),
            "milestones": sorted(
                (str(m.id), str(m.due_date), m.updated_at.isoformat()) for m in milestones
            ),
            "dependencies": sorted(
                (str(d.source_task_id), str(d.target_task_id), d.dependency_type.value)
                for d in dependencies
            ),
            "baseline": baseline.updated_at.isoformat() if baseline else None,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _deadline(projected_finish: date | None, deadline: date | None) -> DeadlineImpactRead:
        if projected_finish is None or deadline is None:
            return DeadlineImpactRead(
                projected_finish=projected_finish,
                deadline=deadline,
                variance_days=None,
                status=DeadlineStatus.UNAVAILABLE,
            )
        variance = (projected_finish - deadline).days
        if variance > 0:
            status = DeadlineStatus.LATE
        elif (deadline - projected_finish).days <= 7:
            status = DeadlineStatus.AT_RISK
        else:
            status = DeadlineStatus.ON_TRACK
        return DeadlineImpactRead(
            projected_finish=projected_finish,
            deadline=deadline,
            variance_days=variance,
            status=status,
        )

    @staticmethod
    def _critical_read(cpm) -> CriticalPathRead:
        return CriticalPathRead(
            complete=cpm.complete,
            reasons=cpm.reasons,
            project_duration_days=cpm.project_duration_days,
            critical_task_ids=cpm.critical_task_ids,
            critical_sequences=cpm.critical_sequences,
        )

    def _milestones(
        self, milestones, schedule_tasks, baseline, projected=None
    ) -> list[ScheduleMilestoneRead]:
        baseline_dates = (
            {item.milestone_id: item.due_date for item in baseline.milestones} if baseline else {}
        )
        projected = projected or {}
        result = []
        for milestone in milestones:
            linked = [task for task in schedule_tasks if task.milestone_id == milestone.id]
            linked_finishes = [
                projected.get(task.id, (task.start, task.finish))[1] for task in linked
            ]
            linked_finishes = [value for value in linked_finishes if value]
            projected_date = max(
                [milestone.due_date, *linked_finishes] if milestone.due_date else linked_finishes,
                default=milestone.due_date,
            )
            baseline_date = baseline_dates.get(milestone.id)
            variance = (
                (projected_date - baseline_date).days if projected_date and baseline_date else None
            )
            impact = self._deadline(projected_date, milestone.due_date)
            result.append(
                ScheduleMilestoneRead(
                    id=milestone.id,
                    title=milestone.title,
                    current_date=milestone.due_date,
                    projected_date=projected_date,
                    baseline_date=baseline_date,
                    variance_days=variance,
                    status=impact.status,
                    affected_task_ids=[task.id for task in linked if task.id in projected],
                )
            )
        return result

    async def schedule(self, project_id: UUID) -> ScheduleRead:
        project, tasks, milestones, dependencies, baseline = await self._data(project_id)
        schedule_tasks = self._schedule_tasks(tasks)
        edges = self.edges(dependencies)
        try:
            cpm = calculate_cpm(schedule_tasks, edges)
        except ValueError as exc:
            raise AppError(
                code="dependency_cycle",
                message="The schedule graph contains a cycle.",
                status_code=409,
            ) from exc
        metrics = cpm.tasks
        baseline_tasks = {item.task_id: item for item in baseline.tasks} if baseline else {}
        predecessors: dict[UUID, list[UUID]] = {task.id: [] for task in schedule_tasks}
        for source, target in edges:
            predecessors.setdefault(target, []).append(source)
        rows = []
        for task in tasks:
            schedule_task = next((item for item in schedule_tasks if item.id == task.id), None)
            metric = metrics.get(task.id)
            old = baseline_tasks.get(task.id)
            warnings = []
            if not schedule_task or schedule_task.duration_days is None:
                warnings.append("missing_valid_dates")
            rows.append(
                ScheduleTaskRead(
                    id=task.id,
                    title=task.title,
                    start=task.start_date,
                    finish=task.due_date,
                    duration_days=schedule_task.duration_days if schedule_task else None,
                    progress=task.completion_percentage,
                    milestone_id=task.milestone_id,
                    dependencies=sorted(predecessors.get(task.id, []), key=str),
                    critical=metric.critical if metric else None,
                    earliest_start_offset=metric.earliest_start if metric else None,
                    earliest_finish_offset=metric.earliest_finish if metric else None,
                    latest_start_offset=metric.latest_start if metric else None,
                    latest_finish_offset=metric.latest_finish if metric else None,
                    total_float=metric.total_float if metric else None,
                    free_float=metric.free_float if metric else None,
                    baseline_start=old.start_date if old else None,
                    baseline_finish=old.due_date if old else None,
                    start_variance=(task.start_date - old.start_date).days
                    if old and old.start_date and task.start_date
                    else None,
                    finish_variance=(task.due_date - old.due_date).days
                    if old and old.due_date and task.due_date
                    else None,
                    warnings=warnings,
                )
            )
        milestone_rows = self._milestones(milestones, schedule_tasks, baseline)
        finishes = [item.finish for item in schedule_tasks if item.finish]
        finishes += [item.projected_date for item in milestone_rows if item.projected_date]
        projected_finish = max(finishes, default=None)
        schedulable = sum(item.duration_days is not None for item in schedule_tasks)
        return ScheduleRead(
            project_id=project_id,
            generated_at=datetime.now(UTC),
            fingerprint=self._fingerprint(project, tasks, milestones, dependencies, baseline),
            calculation_complete=cpm.complete,
            scheduling_completeness_percent=round(schedulable / len(schedule_tasks) * 100, 1)
            if schedule_tasks
            else 0,
            tasks=rows,
            milestones=milestone_rows,
            dependencies=[
                ScheduleDependency(predecessor_id=s, successor_id=t)
                for s, t in sorted(edges, key=lambda value: (str(value[0]), str(value[1])))
            ],
            critical_path=self._critical_read(cpm),
            deadline_impact=self._deadline(projected_finish, project.target_end_date),
            baseline_variance_days=(
                (projected_finish - baseline.target_end_date).days
                if baseline and baseline.target_end_date and projected_finish
                else None
            ),
            baseline_created_at=baseline.updated_at if baseline else None,
        )

    async def baseline(self, project_id: UUID) -> BaselineRead | None:
        _, _, _, _, baseline = await self._data(project_id)
        return self._baseline_read(baseline) if baseline else None

    @staticmethod
    def _baseline_read(item: ScheduleBaseline) -> BaselineRead:
        return BaselineRead(
            id=item.id,
            project_id=item.project_id,
            target_end_date=item.target_end_date,
            created_at=item.created_at,
            updated_at=item.updated_at,
            task_count=len(item.tasks),
            milestone_count=len(item.milestones),
        )

    async def create_baseline(self, project_id: UUID, *, replace: bool) -> BaselineRead:
        project, tasks, milestones, _, baseline = await self._data(project_id)
        if project.archived_at:
            raise AppError(
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )
        if baseline and not replace:
            raise AppError(
                code="schedule_baseline_exists",
                message="A baseline already exists; explicit replacement is required.",
                status_code=409,
            )
        now = datetime.now(UTC)
        action = "schedule.baseline_replaced" if baseline else "schedule.baseline_created"
        if baseline:
            await self.session.execute(
                delete(ScheduleBaselineTask).where(ScheduleBaselineTask.baseline_id == baseline.id)
            )
            await self.session.execute(
                delete(ScheduleBaselineMilestone).where(
                    ScheduleBaselineMilestone.baseline_id == baseline.id
                )
            )
            baseline.target_end_date = project.target_end_date
            baseline.created_by_user_id = self.user_id
            baseline.replaced_at = now
        else:
            baseline = ScheduleBaseline(
                project_id=project_id,
                target_end_date=project.target_end_date,
                created_by_user_id=self.user_id,
            )
            self.session.add(baseline)
            await self.session.flush()
        self.session.add_all(
            [
                ScheduleBaselineTask(
                    baseline_id=baseline.id,
                    project_id=project_id,
                    task_id=t.id,
                    start_date=t.start_date,
                    due_date=t.due_date,
                )
                for t in tasks
            ]
            + [
                ScheduleBaselineMilestone(
                    baseline_id=baseline.id,
                    project_id=project_id,
                    milestone_id=m.id,
                    due_date=m.due_date,
                )
                for m in milestones
            ]
        )
        self.audit.record(
            project_id=project_id,
            action=action,
            entity_type="schedule_baseline",
            entity_id=baseline.id,
            changes={"tasks": len(tasks), "milestones": len(milestones)},
        )
        self.session.add(
            ProjectLogEntry(
                project_id=project_id,
                type=ProjectLogType.NOTE,
                title="Schedule baseline replaced" if replace else "Schedule baseline established",
                description=f"Frozen {len(tasks)} tasks and {len(milestones)} milestones.",
                source=MemorySource.SYSTEM,
                created_by_user_id=self.user_id,
            )
        )
        await self.session.commit()
        loaded = (
            await self.session.execute(
                select(ScheduleBaseline)
                .options(
                    selectinload(ScheduleBaseline.tasks), selectinload(ScheduleBaseline.milestones)
                )
                .where(ScheduleBaseline.id == baseline.id)
            )
        ).scalar_one()
        return self._baseline_read(loaded)

    async def preview(self, project_id: UUID, change: ScheduleChangeRequest) -> SchedulePreviewRead:
        project, tasks, milestones, dependencies, baseline = await self._data(project_id)
        schedule_tasks = self._schedule_tasks(tasks)
        edges = self.edges(dependencies)
        projected: dict[UUID, tuple[date, date]] = {}
        warnings: list[str] = []
        if change.entity_type == "TASK":
            if not any(item.id == change.task_id for item in schedule_tasks):
                raise AppError(code="task_not_found", message="Task not found.", status_code=404)
            projected = propagate_finish_to_start(
                schedule_tasks, edges, change.task_id, change.start_date, change.due_date
            )
            unscheduled_successors = [
                target
                for source, target in edges
                if source in projected
                and next(item for item in schedule_tasks if item.id == target).duration_days is None
            ]
            if unscheduled_successors:
                warnings.append("downstream_tasks_missing_dates")
        else:
            if not any(item.id == change.milestone_id for item in milestones):
                raise AppError(
                    code="milestone_not_found", message="Milestone not found.", status_code=404
                )
        projected_schedule = [
            ScheduleTask(
                item.id, *(projected.get(item.id, (item.start, item.finish))), item.milestone_id
            )
            for item in schedule_tasks
        ]
        cpm = calculate_cpm(projected_schedule, edges)
        milestone_rows = self._milestones(milestones, schedule_tasks, baseline, projected)
        if change.entity_type == "MILESTONE":
            milestone_rows = [
                item.model_copy(
                    update={
                        "projected_date": change.due_date,
                        "variance_days": (change.due_date - item.baseline_date).days
                        if item.baseline_date
                        else None,
                        "status": self._deadline(change.due_date, item.current_date).status,
                    }
                )
                if item.id == change.milestone_id
                else item
                for item in milestone_rows
            ]
        by_id = {task.id: task for task in tasks}
        affected = [
            AffectedTaskRead(
                id=task_id,
                title=by_id[task_id].title,
                before_start=by_id[task_id].start_date,
                before_finish=by_id[task_id].due_date,
                projected_start=dates[0],
                projected_finish=dates[1],
                shift_days=(dates[1] - by_id[task_id].due_date).days
                if by_id[task_id].due_date
                else None,
                source=task_id == change.task_id,
            )
            for task_id, dates in sorted(
                projected.items(), key=lambda value: (value[1][0], str(value[0]))
            )
        ]
        finishes = [item.finish for item in projected_schedule if item.finish] + [
            item.projected_date for item in milestone_rows if item.projected_date
        ]
        fingerprint = self._fingerprint(project, tasks, milestones, dependencies, baseline)
        token_payload = {
            "fingerprint": fingerprint,
            "change": change.model_dump(mode="json"),
            "affected": [
                (str(item.id), str(item.projected_start), str(item.projected_finish))
                for item in affected
            ],
        }
        token = hashlib.sha256(json.dumps(token_payload, sort_keys=True).encode()).hexdigest()
        impacted_milestones = [
            item
            for item in milestone_rows
            if item.affected_task_ids
            or (change.entity_type == "MILESTONE" and item.id == change.milestone_id)
        ]
        return SchedulePreviewRead(
            preview_token=token,
            schedule_fingerprint=fingerprint,
            proposed_change=change,
            affected_tasks=affected,
            milestone_impacts=impacted_milestones,
            deadline_impact=self._deadline(max(finishes, default=None), project.target_end_date),
            critical_path=self._critical_read(cpm),
            warnings=warnings,
        )

    async def apply(self, project_id: UUID, request: ScheduleApplyRequest) -> ScheduleApplyRead:
        project = await self._project(project_id)
        if project.archived_at:
            raise AppError(
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )
        preview = await self.preview(project_id, request.change)
        if preview.preview_token != request.preview_token:
            raise AppError(
                code="stale_schedule_preview",
                message="The schedule changed; create a fresh preview.",
                status_code=409,
            )
        affected_ids = []
        for item in preview.affected_tasks:
            task = await self.work.get_task(project_id, item.id)
            task.start_date, task.due_date = item.projected_start, item.projected_finish
            affected_ids.append(task.id)
        milestone_id = None
        if request.change.entity_type == "MILESTONE":
            milestone = await self.work.get_milestone(project_id, request.change.milestone_id)
            milestone.due_date = request.change.due_date
            milestone_id = milestone.id
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="schedule.change_applied",
            entity_type="project_schedule",
            entity_id=project_id,
            changes={
                "source_type": request.change.entity_type,
                "source_id": str(request.change.task_id or request.change.milestone_id),
                "affected_task_ids": [str(item) for item in affected_ids],
            },
        )
        if len(affected_ids) > 1:
            self.audit.record(
                project_id=project_id,
                action="schedule.recursive_reschedule_applied",
                entity_type="project_schedule",
                entity_id=project_id,
                changes={"affected_count": len(affected_ids)},
            )
        if preview.deadline_impact.status == DeadlineStatus.LATE:
            self.session.add(
                ProjectLogEntry(
                    project_id=project_id,
                    type=ProjectLogType.MILESTONE,
                    title="Project schedule now exceeds target date",
                    description=(
                        "Projected finish variance is "
                        f"+{preview.deadline_impact.variance_days} days."
                    ),
                    source=MemorySource.SYSTEM,
                    created_by_user_id=self.user_id,
                )
            )
        await self.session.commit()
        return ScheduleApplyRead(
            applied_at=datetime.now(UTC),
            affected_task_ids=affected_ids,
            milestone_id=milestone_id,
            schedule=await self.schedule(project_id),
        )
