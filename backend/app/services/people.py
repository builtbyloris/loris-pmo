from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.people import Person, ProjectMember, Stakeholder
from app.models.project import Project
from app.models.task import TaskStatus
from app.repositories.people import PeopleRepository
from app.schemas.people import (
    MemberCreate,
    MemberUpdate,
    MemberWorkload,
    PeopleSummary,
    PersonCreate,
    PersonUpdate,
    StakeholderCreate,
    StakeholderRead,
    StakeholderUpdate,
    WorkloadStatus,
)
from app.services.audit import AuditService


class PeopleService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = PeopleRepository(session, owner_user_id)
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

    async def _person_or_404(self, person_id: UUID) -> Person:
        person = await self.repository.get_person(person_id)
        if person is None:
            raise AppError(code="person_not_found", message="Person not found.", status_code=404)
        return person

    async def create_person(self, data: PersonCreate) -> Person:
        person = Person(owner_user_id=self.owner_user_id, **data.model_dump(mode="json"))
        self.session.add(person)
        await self.session.flush()
        self.audit.record(
            project_id=None,
            action="person.created",
            entity_type="person",
            entity_id=person.id,
            changes={"name": person.name},
        )
        await self.session.commit()
        await self.session.refresh(person)
        return person

    async def list_people(self, search: str | None = None) -> list[Person]:
        return await self.repository.list_people(search)

    async def update_person(self, person_id: UUID, data: PersonUpdate) -> Person:
        person = await self._person_or_404(person_id)
        changes = data.model_dump(exclude_unset=True, mode="json")
        for key, value in changes.items():
            setattr(person, key, value)
        if changes:
            await self.session.commit()
            await self.session.refresh(person)
        return person

    async def list_members(self, project_id: UUID) -> list[ProjectMember]:
        await self._project_or_404(project_id)
        return await self.repository.list_members(project_id)

    async def add_member(self, project_id: UUID, data: MemberCreate) -> ProjectMember:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        person = await self.repository.get_person(data.person_id)
        if person is None:
            raise AppError(
                code="person_not_found",
                message="Person not found for this owner.",
                status_code=422,
            )
        if await self.repository.membership_exists(project_id, person.id):
            raise AppError(
                code="member_exists",
                message="This person is already a project member.",
                status_code=409,
            )
        member = ProjectMember(project_id=project_id, **data.model_dump())
        self.session.add(member)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="project_member.added",
            entity_type="project_member",
            entity_id=member.id,
            changes={"person_id": str(person.id), "role": member.role.value},
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                code="member_exists",
                message="This person is already a project member.",
                status_code=409,
            ) from exc
        return await self.repository.get_member(project_id, member.id)  # type: ignore[return-value]

    async def update_member(
        self, project_id: UUID, member_id: UUID, data: MemberUpdate
    ) -> ProjectMember:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        member = await self.repository.get_member(project_id, member_id)
        if member is None:
            raise AppError(code="member_not_found", message="Member not found.", status_code=404)
        changes = data.model_dump(exclude_unset=True)
        if changes:
            before = {key: str(getattr(member, key)) for key in changes}
            for key, value in changes.items():
                setattr(member, key, value)
            self.audit.record(
                project_id=project_id,
                action="project_member.updated",
                entity_type="project_member",
                entity_id=member.id,
                changes={"before": before, "fields": list(changes)},
            )
            await self.session.commit()
        return await self.repository.get_member(project_id, member_id)  # type: ignore[return-value]

    async def remove_member(self, project_id: UUID, member_id: UUID) -> None:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        member = await self.repository.get_member(project_id, member_id)
        if member is None:
            raise AppError(code="member_not_found", message="Member not found.", status_code=404)
        if await self.repository.member_owns_control_records(project_id, member_id):
            raise AppError(
                code="member_in_use",
                message="This member owns project control records and cannot be removed.",
                status_code=409,
            )
        assignments = await self.repository.list_member_assignments(project_id, member_id)
        for assignment in assignments:
            task = assignment.task
            before = sorted(str(value) for value in task.assignee_ids)
            task.assignees.remove(assignment)
            after = sorted(str(value) for value in task.assignee_ids)
            self.audit.record(
                project_id=project_id,
                action="task.assignee_changed",
                entity_type="task",
                entity_id=assignment.task_id,
                changes={"from": before, "to": after, "reason": "project_member.removed"},
            )
        self.audit.record(
            project_id=project_id,
            action="project_member.removed",
            entity_type="project_member",
            entity_id=member.id,
            changes={"person_id": str(member.person_id)},
        )
        await self.session.delete(member)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                code="member_in_use",
                message="This member owns project control records and cannot be removed.",
                status_code=409,
            ) from exc

    @staticmethod
    def _stakeholder_read(stakeholder: Stakeholder) -> StakeholderRead:
        return StakeholderRead(
            id=stakeholder.id,
            project_id=stakeholder.project_id,
            person_id=stakeholder.person_id,
            name=stakeholder.name,
            display_name=stakeholder.person.name if stakeholder.person else stakeholder.name or "",
            organization=stakeholder.organization,
            role=stakeholder.role,
            influence=stakeholder.influence,
            interest=stakeholder.interest,
            communication_frequency=stakeholder.communication_frequency,
            communication_channel=stakeholder.communication_channel,
            notes=stakeholder.notes,
            created_at=stakeholder.created_at,
            updated_at=stakeholder.updated_at,
        )

    async def list_stakeholders(self, project_id: UUID) -> list[StakeholderRead]:
        await self._project_or_404(project_id)
        return [
            self._stakeholder_read(item)
            for item in await self.repository.list_stakeholders(project_id)
        ]

    async def _validate_stakeholder_person(self, person_id: UUID | None) -> None:
        if person_id is not None and await self.repository.get_person(person_id) is None:
            raise AppError(
                code="person_not_found",
                message="Linked person not found for this owner.",
                status_code=422,
            )

    async def create_stakeholder(
        self, project_id: UUID, data: StakeholderCreate
    ) -> StakeholderRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_stakeholder_person(data.person_id)
        stakeholder = Stakeholder(project_id=project_id, **data.model_dump())
        self.session.add(stakeholder)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="stakeholder.created",
            entity_type="stakeholder",
            entity_id=stakeholder.id,
        )
        await self.session.commit()
        item = await self.repository.get_stakeholder(project_id, stakeholder.id)
        return self._stakeholder_read(item)  # type: ignore[arg-type]

    async def update_stakeholder(
        self, project_id: UUID, stakeholder_id: UUID, data: StakeholderUpdate
    ) -> StakeholderRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        stakeholder = await self.repository.get_stakeholder(project_id, stakeholder_id)
        if stakeholder is None:
            raise AppError(
                code="stakeholder_not_found", message="Stakeholder not found.", status_code=404
            )
        changes = data.model_dump(exclude_unset=True)
        await self._validate_stakeholder_person(changes.get("person_id", stakeholder.person_id))
        final_person = changes.get("person_id", stakeholder.person_id)
        final_name = changes.get("name", stakeholder.name)
        if final_person is None and not (final_name and final_name.strip()):
            raise AppError(
                code="stakeholder_identity_required",
                message="A standalone stakeholder requires a name.",
                status_code=422,
            )
        for key, value in changes.items():
            setattr(stakeholder, key, value)
        if changes:
            self.audit.record(
                project_id=project_id,
                action="stakeholder.updated",
                entity_type="stakeholder",
                entity_id=stakeholder.id,
                changes={"fields": list(changes)},
            )
            await self.session.commit()
        item = await self.repository.get_stakeholder(project_id, stakeholder.id)
        return self._stakeholder_read(item)  # type: ignore[arg-type]

    async def remove_stakeholder(self, project_id: UUID, stakeholder_id: UUID) -> None:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        stakeholder = await self.repository.get_stakeholder(project_id, stakeholder_id)
        if stakeholder is None:
            raise AppError(
                code="stakeholder_not_found", message="Stakeholder not found.", status_code=404
            )
        self.audit.record(
            project_id=project_id,
            action="stakeholder.removed",
            entity_type="stakeholder",
            entity_id=stakeholder.id,
        )
        await self.session.delete(stakeholder)
        await self.session.commit()

    @staticmethod
    def _status(
        *, active_tasks: int, overdue_tasks: int, availability_percent: int
    ) -> WorkloadStatus:
        if active_tasks == 0:
            return WorkloadStatus.NO_DATA
        if availability_percent == 0 or overdue_tasks > 0:
            return WorkloadStatus.HIGH
        capacity_slots = max(1.0, availability_percent / 20)
        ratio = active_tasks / capacity_slots
        if ratio > 1:
            return WorkloadStatus.HIGH
        if ratio >= 0.6:
            return WorkloadStatus.MEDIUM
        return WorkloadStatus.LOW

    async def workload(self, project_id: UUID) -> list[MemberWorkload]:
        await self._project_or_404(project_id)
        members = await self.repository.list_members(project_id)
        assignments = await self.repository.list_assigned_tasks(project_id)
        today = date.today()
        due_soon_horizon = today + timedelta(days=14)
        rows: list[MemberWorkload] = []
        for member in members:
            tasks = [
                task
                for assignment, task in assignments
                if assignment.project_member_id == member.id
            ]
            active = [
                task for task in tasks if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
            ]
            overdue = [task for task in active if task.due_date and task.due_date < today]
            due_soon = [
                task
                for task in active
                if task.due_date and today <= task.due_date <= due_soon_horizon
            ]
            rows.append(
                MemberWorkload(
                    member_id=member.id,
                    person_id=member.person_id,
                    name=member.person.name,
                    role=member.role,
                    availability_percent=member.availability_percent,
                    active_task_count=len(active),
                    overdue_task_count=len(overdue),
                    due_soon_task_count=len(due_soon),
                    estimated_effort=sum(
                        (task.estimated_effort for task in active), Decimal("0.00")
                    ),
                    actual_effort=sum((task.actual_effort for task in active), Decimal("0.00")),
                    effort_data_complete=all(task.estimated_effort > 0 for task in active),
                    workload_status=self._status(
                        active_tasks=len(active),
                        overdue_tasks=len(overdue),
                        availability_percent=member.availability_percent,
                    ),
                )
            )
        return rows

    async def summary(self, project_id: UUID) -> PeopleSummary:
        workloads = await self.workload(project_id)
        return PeopleSummary(
            team_size=len(workloads),
            stakeholder_count=await self.repository.stakeholder_count(project_id),
            workload_warning_count=sum(
                item.workload_status == WorkloadStatus.HIGH for item in workloads
            ),
        )
