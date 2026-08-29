from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.control import Issue, Risk
from app.models.people import Person, ProjectMember, Stakeholder, TaskAssignee
from app.models.project import Project
from app.models.task import Task


class PeopleRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def get_project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id, Project.owner_user_id == self.owner_user_id
                )
            )
        ).scalar_one_or_none()

    async def get_person(self, person_id: UUID) -> Person | None:
        return (
            await self.session.execute(
                select(Person).where(
                    Person.id == person_id, Person.owner_user_id == self.owner_user_id
                )
            )
        ).scalar_one_or_none()

    async def list_people(self, search: str | None = None) -> list[Person]:
        query = select(Person).where(Person.owner_user_id == self.owner_user_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(or_(Person.name.ilike(term), Person.email.ilike(term)))
        result = await self.session.execute(query.order_by(Person.name, Person.id))
        return list(result.scalars())

    async def get_member(self, project_id: UUID, member_id: UUID) -> ProjectMember | None:
        return (
            await self.session.execute(
                select(ProjectMember)
                .join(Project, Project.id == ProjectMember.project_id)
                .options(selectinload(ProjectMember.person))
                .where(
                    ProjectMember.id == member_id,
                    ProjectMember.project_id == project_id,
                    Project.owner_user_id == self.owner_user_id,
                )
            )
        ).scalar_one_or_none()

    async def get_members(self, project_id: UUID, member_ids: list[UUID]) -> list[ProjectMember]:
        if not member_ids:
            return []
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.id.in_(member_ids)
            )
        )
        return list(result.scalars())

    async def list_members(self, project_id: UUID) -> list[ProjectMember]:
        result = await self.session.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.person))
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at, ProjectMember.id)
        )
        return list(result.scalars())

    async def membership_exists(self, project_id: UUID, person_id: UUID) -> bool:
        count = (
            await self.session.execute(
                select(func.count(ProjectMember.id)).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.person_id == person_id,
                )
            )
        ).scalar_one()
        return bool(count)

    async def get_stakeholder(self, project_id: UUID, stakeholder_id: UUID) -> Stakeholder | None:
        return (
            await self.session.execute(
                select(Stakeholder)
                .join(Project, Project.id == Stakeholder.project_id)
                .options(selectinload(Stakeholder.person))
                .where(
                    Stakeholder.id == stakeholder_id,
                    Stakeholder.project_id == project_id,
                    Project.owner_user_id == self.owner_user_id,
                )
            )
        ).scalar_one_or_none()

    async def list_stakeholders(self, project_id: UUID) -> list[Stakeholder]:
        result = await self.session.execute(
            select(Stakeholder)
            .options(selectinload(Stakeholder.person))
            .where(Stakeholder.project_id == project_id)
            .order_by(Stakeholder.created_at, Stakeholder.id)
        )
        return list(result.scalars())

    async def list_assigned_tasks(self, project_id: UUID) -> list[tuple[TaskAssignee, Task]]:
        result = await self.session.execute(
            select(TaskAssignee, Task)
            .join(
                Task,
                (Task.project_id == TaskAssignee.project_id) & (Task.id == TaskAssignee.task_id),
            )
            .where(TaskAssignee.project_id == project_id, Task.archived_at.is_(None))
        )
        return list(result.tuples())

    async def list_member_assignments(
        self, project_id: UUID, member_id: UUID
    ) -> list[TaskAssignee]:
        result = await self.session.execute(
            select(TaskAssignee)
            .options(selectinload(TaskAssignee.task).selectinload(Task.assignees))
            .where(
                TaskAssignee.project_id == project_id,
                TaskAssignee.project_member_id == member_id,
            )
        )
        return list(result.scalars())

    async def member_owns_control_records(self, project_id: UUID, member_id: UUID) -> bool:
        risk_count = (
            await self.session.execute(
                select(func.count(Risk.id)).where(
                    Risk.project_id == project_id, Risk.owner_member_id == member_id
                )
            )
        ).scalar_one()
        issue_count = (
            await self.session.execute(
                select(func.count(Issue.id)).where(
                    Issue.project_id == project_id, Issue.owner_member_id == member_id
                )
            )
        ).scalar_one()
        return bool(risk_count or issue_count)

    async def stakeholder_count(self, project_id: UUID) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count(Stakeholder.id)).where(Stakeholder.project_id == project_id)
                )
            ).scalar_one()
        )
