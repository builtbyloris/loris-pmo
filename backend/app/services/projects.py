from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.objective import Objective
from app.models.project import Project, ProjectStatus
from app.models.success_criterion import SuccessCriterion
from app.repositories.projects import ProjectRepository
from app.schemas.projects import (
    ObjectiveCreate,
    ObjectiveUpdate,
    PortfolioSummary,
    ProjectCreate,
    ProjectList,
    ProjectUpdate,
    SuccessCriterionCreate,
    SuccessCriterionUpdate,
)
from app.services.audit import AuditService


class ProjectService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.projects = ProjectRepository(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def _project_or_404(self, project_id: UUID, *, with_children: bool = False) -> Project:
        project = await self.projects.get(project_id, with_children=with_children)
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

    async def _commit(self, *, code_conflict: bool = False) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if code_conflict:
                raise AppError(
                    code="project_code_exists",
                    message="A project with this code already exists.",
                    status_code=409,
                ) from exc
            raise

    async def create(self, data: ProjectCreate) -> Project:
        if await self.projects.code_exists(data.code):
            raise AppError(
                code="project_code_exists",
                message="A project with this code already exists.",
                status_code=409,
            )
        project_data = data.model_dump(exclude={"objectives", "success_criteria"})
        project = Project(owner_user_id=self.owner_user_id, **project_data)
        self.session.add(project)
        await self.session.flush()
        for objective_data in data.objectives:
            objective = Objective(project_id=project.id, **objective_data.model_dump())
            self.session.add(objective)
            await self.session.flush()
            self.audit.record(
                project_id=project.id,
                action="objective.created",
                entity_type="objective",
                entity_id=objective.id,
            )
        for criterion_data in data.success_criteria:
            if criterion_data.objective_id is not None:
                raise AppError(
                    code="objective_not_found",
                    message="A criterion created with a project must be project-level.",
                    status_code=422,
                )
            criterion = SuccessCriterion(project_id=project.id, **criterion_data.model_dump())
            self.session.add(criterion)
            await self.session.flush()
            self.audit.record(
                project_id=project.id,
                action="success_criterion.created",
                entity_type="success_criterion",
                entity_id=criterion.id,
            )
        self.audit.record(
            project_id=project.id,
            action="project.created",
            entity_type="project",
            entity_id=project.id,
            changes={"name": project.name, "code": project.code},
        )
        await self._commit(code_conflict=True)
        return await self._project_or_404(project.id, with_children=True)

    async def get(self, project_id: UUID) -> Project:
        return await self._project_or_404(project_id, with_children=True)

    async def list(self, **filters) -> ProjectList:
        projects, total = await self.projects.list(**filters)
        return ProjectList(items=projects, total=total)

    async def portfolio(self) -> PortfolioSummary:
        total, active, on_hold, completed = await self.projects.portfolio_counts()
        return PortfolioSummary(
            total_projects=total,
            active_projects=active,
            on_hold_projects=on_hold,
            completed_projects=completed,
        )

    async def update(self, project_id: UUID, data: ProjectUpdate) -> Project:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return await self._project_or_404(project_id, with_children=True)
        if changes.get("status") == ProjectStatus.ARCHIVED:
            raise AppError(
                code="use_archive_endpoint",
                message="Use the archive action to archive a project.",
                status_code=409,
            )
        code = changes.get("code")
        if code and await self.projects.code_exists(code, exclude_project_id=project_id):
            raise AppError(
                code="project_code_exists",
                message="A project with this code already exists.",
                status_code=409,
            )
        final_start = changes.get("start_date", project.start_date)
        final_end = changes.get("target_end_date", project.target_end_date)
        if final_start and final_end and final_end < final_start:
            raise AppError(
                code="invalid_project_dates",
                message="Target end date must not precede start date.",
                status_code=422,
            )
        before = {
            key: str(getattr(project, key)) if getattr(project, key) is not None else None
            for key in changes
        }
        for key, value in changes.items():
            setattr(project, key, value)
        await self.session.flush()
        self.audit.record(
            project_id=project.id,
            action="project.updated",
            entity_type="project",
            entity_id=project.id,
            changes={"before": before, "fields": list(changes)},
        )
        await self._commit(code_conflict=bool(code))
        return await self._project_or_404(project.id, with_children=True)

    async def archive(self, project_id: UUID) -> Project:
        project = await self._project_or_404(project_id)
        if project.archived_at is None:
            project.archived_at = datetime.now(UTC)
            project.status = ProjectStatus.ARCHIVED
            await self.session.flush()
            self.audit.record(
                project_id=project.id,
                action="project.archived",
                entity_type="project",
                entity_id=project.id,
            )
            await self._commit()
        return await self._project_or_404(project.id, with_children=True)

    async def create_objective(self, project_id: UUID, data: ObjectiveCreate) -> Objective:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        objective = Objective(project_id=project_id, **data.model_dump())
        self.session.add(objective)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="objective.created",
            entity_type="objective",
            entity_id=objective.id,
        )
        await self._commit()
        await self.session.refresh(objective)
        return objective

    async def list_objectives(self, project_id: UUID) -> list[Objective]:
        await self._project_or_404(project_id)
        return await self.projects.list_objectives(project_id)

    async def update_objective(
        self, project_id: UUID, objective_id: UUID, data: ObjectiveUpdate
    ) -> Objective:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        objective = await self.projects.get_objective(project_id, objective_id)
        if objective is None:
            raise AppError(
                code="objective_not_found", message="Objective not found.", status_code=404
            )
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return objective
        for key, value in changes.items():
            setattr(objective, key, value)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="objective.updated",
            entity_type="objective",
            entity_id=objective.id,
            changes={"fields": list(changes)},
        )
        await self._commit()
        await self.session.refresh(objective)
        return objective

    async def delete_objective(self, project_id: UUID, objective_id: UUID) -> None:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        objective = await self.projects.get_objective(project_id, objective_id)
        if objective is None:
            raise AppError(
                code="objective_not_found", message="Objective not found.", status_code=404
            )
        self.audit.record(
            project_id=project_id,
            action="objective.deleted",
            entity_type="objective",
            entity_id=objective.id,
        )
        await self.projects.unlink_objective_criteria(project_id, objective_id)
        await self.session.delete(objective)
        await self._commit()

    async def create_criterion(
        self, project_id: UUID, data: SuccessCriterionCreate
    ) -> SuccessCriterion:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        if (
            data.objective_id
            and await self.projects.get_objective(project_id, data.objective_id) is None
        ):
            raise AppError(
                code="objective_not_found", message="Objective not found.", status_code=422
            )
        criterion = SuccessCriterion(project_id=project_id, **data.model_dump())
        self.session.add(criterion)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="success_criterion.created",
            entity_type="success_criterion",
            entity_id=criterion.id,
        )
        await self._commit()
        await self.session.refresh(criterion)
        return criterion

    async def list_criteria(self, project_id: UUID) -> list[SuccessCriterion]:
        await self._project_or_404(project_id)
        return await self.projects.list_criteria(project_id)

    async def update_criterion(
        self, project_id: UUID, criterion_id: UUID, data: SuccessCriterionUpdate
    ) -> SuccessCriterion:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        criterion = await self.projects.get_criterion(project_id, criterion_id)
        if criterion is None:
            raise AppError(
                code="criterion_not_found", message="Success criterion not found.", status_code=404
            )
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return criterion
        if "objective_id" in changes and changes["objective_id"] is not None:
            if await self.projects.get_objective(project_id, changes["objective_id"]) is None:
                raise AppError(
                    code="objective_not_found", message="Objective not found.", status_code=422
                )
        for key, value in changes.items():
            setattr(criterion, key, value)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="success_criterion.updated",
            entity_type="success_criterion",
            entity_id=criterion.id,
            changes={"fields": list(changes)},
        )
        await self._commit()
        await self.session.refresh(criterion)
        return criterion

    async def delete_criterion(self, project_id: UUID, criterion_id: UUID) -> None:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        criterion = await self.projects.get_criterion(project_id, criterion_id)
        if criterion is None:
            raise AppError(
                code="criterion_not_found", message="Success criterion not found.", status_code=404
            )
        self.audit.record(
            project_id=project_id,
            action="success_criterion.deleted",
            entity_type="success_criterion",
            entity_id=criterion.id,
        )
        await self.session.delete(criterion)
        await self._commit()
