from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditEvent
from app.models.control import ChangeRequest, Issue, Risk
from app.models.memory import (
    ActionItemStatus,
    Decision,
    Meeting,
    MeetingActionItem,
    MemoryEntityType,
    ProjectLogEntry,
    ProjectLogType,
)
from app.models.milestone import Milestone
from app.models.people import ProjectMember
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.memory import SortOrder
from app.services.authorization import accessible_project_ids

ENTITY_MODELS = {
    MemoryEntityType.TASK: (Task, Task.title),
    MemoryEntityType.MILESTONE: (Milestone, Milestone.title),
    MemoryEntityType.RISK: (Risk, Risk.title),
    MemoryEntityType.ISSUE: (Issue, Issue.title),
    MemoryEntityType.CHANGE_REQUEST: (ChangeRequest, ChangeRequest.title),
    MemoryEntityType.MEETING: (Meeting, Meeting.title),
    MemoryEntityType.DECISION: (Decision, Decision.title),
}


class MemoryRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def get_project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
            )
        ).scalar_one_or_none()

    async def member_ids_exist(self, project_id: UUID, ids: list[UUID]) -> bool:
        if not ids:
            return True
        count = await self.session.scalar(
            select(func.count(ProjectMember.id)).where(
                ProjectMember.project_id == project_id, ProjectMember.id.in_(set(ids))
            )
        )
        return count == len(set(ids))

    async def entity_links_exist(self, project_id: UUID, links) -> bool:
        grouped: dict[MemoryEntityType, set[UUID]] = {}
        for link in links:
            grouped.setdefault(link.entity_type, set()).add(link.entity_id)
        for entity_type, ids in grouped.items():
            model, _ = ENTITY_MODELS[entity_type]
            count = await self.session.scalar(
                select(func.count(model.id)).where(
                    model.project_id == project_id, model.id.in_(ids)
                )
            )
            if count != len(ids):
                return False
        return True

    async def entity_names(self, project_id: UUID, links) -> dict[tuple, str]:
        result: dict[tuple, str] = {}
        grouped: dict[MemoryEntityType, set[UUID]] = {}
        for link in links:
            grouped.setdefault(link.entity_type, set()).add(link.entity_id)
        for entity_type, ids in grouped.items():
            model, title = ENTITY_MODELS[entity_type]
            rows = await self.session.execute(
                select(model.id, title).where(model.project_id == project_id, model.id.in_(ids))
            )
            result.update({(entity_type, row[0]): row[1] for row in rows})
        return result

    async def get_log(self, project_id: UUID, entry_id: UUID) -> ProjectLogEntry | None:
        return (
            await self.session.execute(
                select(ProjectLogEntry)
                .options(selectinload(ProjectLogEntry.links))
                .where(ProjectLogEntry.project_id == project_id, ProjectLogEntry.id == entry_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def list_logs(
        self,
        project_id: UUID,
        *,
        search: str | None,
        entry_type: ProjectLogType | None,
        source,
        sort_order: SortOrder,
    ) -> tuple[list[ProjectLogEntry], int]:
        filters = [ProjectLogEntry.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(ProjectLogEntry.title.ilike(term), ProjectLogEntry.description.ilike(term))
            )
        if entry_type:
            filters.append(ProjectLogEntry.type == entry_type)
        if source:
            filters.append(ProjectLogEntry.source == source)
        total = int(
            await self.session.scalar(select(func.count(ProjectLogEntry.id)).where(*filters)) or 0
        )
        ordering = (
            ProjectLogEntry.created_at.asc()
            if sort_order == SortOrder.ASC
            else ProjectLogEntry.created_at.desc()
        )
        result = await self.session.execute(
            select(ProjectLogEntry)
            .options(selectinload(ProjectLogEntry.links))
            .where(*filters)
            .order_by(ordering, ProjectLogEntry.id)
        )
        return list(result.scalars()), total

    async def get_meeting(self, project_id: UUID, meeting_id: UUID) -> Meeting | None:
        return (
            await self.session.execute(
                select(Meeting)
                .options(selectinload(Meeting.participants), selectinload(Meeting.action_items))
                .where(Meeting.project_id == project_id, Meeting.id == meeting_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def list_meetings(
        self, project_id: UUID, *, search: str | None, status, sort_order: SortOrder
    ) -> tuple[list[Meeting], int]:
        filters = [Meeting.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Meeting.title.ilike(term), Meeting.agenda.ilike(term), Meeting.notes.ilike(term)
                )
            )
        if status:
            filters.append(Meeting.status == status)
        total = int(await self.session.scalar(select(func.count(Meeting.id)).where(*filters)) or 0)
        ordering = (
            Meeting.scheduled_at.asc()
            if sort_order == SortOrder.ASC
            else Meeting.scheduled_at.desc()
        )
        rows = await self.session.execute(
            select(Meeting)
            .options(selectinload(Meeting.participants), selectinload(Meeting.action_items))
            .where(*filters)
            .order_by(ordering, Meeting.id)
        )
        return list(rows.scalars()), total

    async def get_action_item(
        self, project_id: UUID, meeting_id: UUID, item_id: UUID
    ) -> MeetingActionItem | None:
        return (
            await self.session.execute(
                select(MeetingActionItem).where(
                    MeetingActionItem.project_id == project_id,
                    MeetingActionItem.meeting_id == meeting_id,
                    MeetingActionItem.id == item_id,
                )
            )
        ).scalar_one_or_none()

    async def get_decision(self, project_id: UUID, decision_id: UUID) -> Decision | None:
        return (
            await self.session.execute(
                select(Decision)
                .options(selectinload(Decision.links))
                .where(Decision.project_id == project_id, Decision.id == decision_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def list_decisions(
        self, project_id: UUID, *, search: str | None, status, sort_order: SortOrder
    ) -> tuple[list[Decision], int]:
        filters = [Decision.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Decision.title.ilike(term),
                    Decision.decision.ilike(term),
                    Decision.reason.ilike(term),
                )
            )
        if status:
            filters.append(Decision.status == status)
        total = int(await self.session.scalar(select(func.count(Decision.id)).where(*filters)) or 0)
        ordering = (
            Decision.decision_date.asc()
            if sort_order == SortOrder.ASC
            else Decision.decision_date.desc()
        )
        rows = await self.session.execute(
            select(Decision)
            .options(selectinload(Decision.links))
            .where(*filters)
            .order_by(ordering, Decision.id)
        )
        return list(rows.scalars()), total

    async def list_activity(
        self,
        project_id: UUID,
        *,
        search: str | None,
        action: str | None,
        entity_type: str | None,
        sort_order: SortOrder,
    ) -> tuple[list[tuple[AuditEvent, str | None, str | None]], int]:
        filters = [AuditEvent.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(or_(AuditEvent.action.ilike(term), AuditEvent.entity_type.ilike(term)))
        if action:
            filters.append(AuditEvent.action == action)
        if entity_type:
            filters.append(AuditEvent.entity_type == entity_type)
        total = int(
            await self.session.scalar(select(func.count(AuditEvent.id)).where(*filters)) or 0
        )
        ordering = (
            AuditEvent.created_at.asc()
            if sort_order == SortOrder.ASC
            else AuditEvent.created_at.desc()
        )
        rows = await self.session.execute(
            select(AuditEvent, User.email, User.display_name)
            .outerjoin(User, User.id == AuditEvent.actor_user_id)
            .where(*filters)
            .order_by(ordering, AuditEvent.id)
        )
        return list(rows.tuples()), total

    async def pending_action_count(self, project_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(MeetingActionItem.id)).where(
                    MeetingActionItem.project_id == project_id,
                    MeetingActionItem.status.in_(
                        (ActionItemStatus.PROPOSED, ActionItemStatus.CONFIRMED)
                    ),
                )
            )
            or 0
        )
