from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.objective import Objective
from app.models.project import Project, ProjectPriority, ProjectStatus
from app.models.success_criterion import SuccessCriterion
from app.schemas.projects import ProjectSort, SortOrder


class ProjectRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    def _owned(self) -> Select[tuple[Project]]:
        return select(Project).where(Project.owner_user_id == self.owner_user_id)

    async def get(self, project_id: UUID, *, with_children: bool = False) -> Project | None:
        query = self._owned().where(Project.id == project_id)
        if with_children:
            query = query.options(
                selectinload(Project.objectives), selectinload(Project.success_criteria)
            )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def code_exists(self, code: str, *, exclude_project_id: UUID | None = None) -> bool:
        query = select(func.count(Project.id)).where(
            Project.owner_user_id == self.owner_user_id, Project.code == code
        )
        if exclude_project_id:
            query = query.where(Project.id != exclude_project_id)
        return bool((await self.session.execute(query)).scalar_one())

    async def list(
        self,
        *,
        search: str | None,
        status: ProjectStatus | None,
        priority: ProjectPriority | None,
        include_archived: bool,
        sort_by: ProjectSort,
        sort_order: SortOrder,
    ) -> tuple[list[Project], int]:
        filters = [Project.owner_user_id == self.owner_user_id]
        if not include_archived:
            filters.append(Project.archived_at.is_(None))
        if status:
            filters.append(Project.status == status)
        if priority:
            filters.append(Project.priority == priority)
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(or_(Project.name.ilike(term), Project.code.ilike(term)))
        count = (
            await self.session.execute(select(func.count(Project.id)).where(*filters))
        ).scalar_one()
        sort_column = {
            ProjectSort.UPDATED_AT: Project.updated_at,
            ProjectSort.CREATED_AT: Project.created_at,
            ProjectSort.NAME: Project.name,
            ProjectSort.START_DATE: Project.start_date,
            ProjectSort.TARGET_END_DATE: Project.target_end_date,
        }[sort_by]
        ordering = sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()
        result = await self.session.execute(
            select(Project).where(*filters).order_by(ordering, Project.id)
        )
        return list(result.scalars()), count

    async def portfolio_counts(self) -> tuple[int, int, int, int]:
        base = [Project.owner_user_id == self.owner_user_id, Project.archived_at.is_(None)]
        query = select(
            func.count(Project.id),
            func.count(Project.id).filter(Project.status == ProjectStatus.ACTIVE),
            func.count(Project.id).filter(Project.status == ProjectStatus.ON_HOLD),
            func.count(Project.id).filter(Project.status == ProjectStatus.COMPLETED),
        ).where(*base)
        row = (await self.session.execute(query)).one()
        return tuple(int(value) for value in row)  # type: ignore[return-value]

    async def get_objective(self, project_id: UUID, objective_id: UUID) -> Objective | None:
        result = await self.session.execute(
            select(Objective)
            .join(Project, Project.id == Objective.project_id)
            .where(
                Objective.id == objective_id,
                Objective.project_id == project_id,
                Project.owner_user_id == self.owner_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_objectives(self, project_id: UUID) -> list[Objective]:
        result = await self.session.execute(
            select(Objective)
            .where(Objective.project_id == project_id)
            .order_by(Objective.created_at)
        )
        return list(result.scalars())

    async def unlink_objective_criteria(self, project_id: UUID, objective_id: UUID) -> None:
        await self.session.execute(
            update(SuccessCriterion)
            .where(
                SuccessCriterion.project_id == project_id,
                SuccessCriterion.objective_id == objective_id,
            )
            .values(objective_id=None)
        )

    async def get_criterion(self, project_id: UUID, criterion_id: UUID) -> SuccessCriterion | None:
        result = await self.session.execute(
            select(SuccessCriterion)
            .join(Project, Project.id == SuccessCriterion.project_id)
            .where(
                SuccessCriterion.id == criterion_id,
                SuccessCriterion.project_id == project_id,
                Project.owner_user_id == self.owner_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_criteria(self, project_id: UUID) -> list[SuccessCriterion]:
        result = await self.session.execute(
            select(SuccessCriterion)
            .where(SuccessCriterion.project_id == project_id)
            .order_by(SuccessCriterion.created_at)
        )
        return list(result.scalars())
