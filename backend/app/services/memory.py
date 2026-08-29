from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.memory import (
    ActionItemStatus,
    Decision,
    DecisionLink,
    DecisionStatus,
    Meeting,
    MeetingActionItem,
    MeetingParticipant,
    MeetingStatus,
    MemoryEntityType,
    MemorySource,
    ProjectLogEntry,
    ProjectLogLink,
    ProjectLogType,
)
from app.models.project import Project
from app.repositories.memory import MemoryRepository
from app.schemas.memory import (
    ActionItemCreate,
    ActionItemRead,
    ActionItemUpdate,
    ActivityList,
    ActivityRead,
    DecisionCreate,
    DecisionList,
    DecisionRead,
    DecisionUpdate,
    EntityLink,
    EntityLinkRead,
    MeetingCreate,
    MeetingList,
    MeetingRead,
    MeetingUpdate,
    MemorySummary,
    MemorySummaryItem,
    ProjectLogCreate,
    ProjectLogList,
    ProjectLogRead,
    ProjectLogUpdate,
)
from app.services.audit import AuditService

ACTION_TRANSITIONS = {
    ActionItemStatus.PROPOSED: {ActionItemStatus.CONFIRMED, ActionItemStatus.DISMISSED},
    ActionItemStatus.CONFIRMED: {ActionItemStatus.COMPLETED, ActionItemStatus.DISMISSED},
    ActionItemStatus.COMPLETED: set(),
    ActionItemStatus.DISMISSED: set(),
}
DECISION_TRANSITIONS = {
    DecisionStatus.PROPOSED: {DecisionStatus.DECIDED},
    DecisionStatus.DECIDED: {DecisionStatus.REVERSED, DecisionStatus.SUPERSEDED},
    DecisionStatus.REVERSED: set(),
    DecisionStatus.SUPERSEDED: set(),
}


class MemoryService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = MemoryRepository(session, owner_user_id)
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
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )

    async def _validate_members(self, project_id: UUID, ids: list[UUID]) -> None:
        if not await self.repository.member_ids_exist(project_id, ids):
            raise AppError(
                code="invalid_project_member",
                message="Every referenced person must be a member of this project.",
                status_code=422,
            )

    async def _validate_links(self, project_id: UUID, links: list[EntityLink]) -> None:
        unique = {(link.entity_type, link.entity_id) for link in links}
        if len(unique) != len(links):
            raise AppError(
                code="duplicate_entity_link",
                message="Entity links must be unique.",
                status_code=422,
            )
        if not await self.repository.entity_links_exist(project_id, links):
            raise AppError(
                code="invalid_entity_link",
                message="Every linked record must belong to this project.",
                status_code=422,
            )

    @staticmethod
    def record_system_log(
        session: AsyncSession,
        *,
        actor_user_id: UUID,
        project_id: UUID,
        entry_type: ProjectLogType,
        title: str,
        description: str | None,
        entity_type: MemoryEntityType,
        entity_id: UUID,
    ) -> ProjectLogEntry:
        entry = ProjectLogEntry(
            project_id=project_id,
            type=entry_type,
            title=title,
            description=description,
            source=MemorySource.SYSTEM,
            created_by_user_id=actor_user_id,
        )
        entry.links = [
            ProjectLogLink(project_id=project_id, entity_type=entity_type, entity_id=entity_id)
        ]
        session.add(entry)
        return entry

    async def _link_reads(self, project_id: UUID, links) -> list[EntityLinkRead]:
        names = await self.repository.entity_names(project_id, links)
        return [
            EntityLinkRead(
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                entity_name=names.get((link.entity_type, link.entity_id)),
            )
            for link in links
        ]

    async def _log_read(self, entry: ProjectLogEntry) -> ProjectLogRead:
        return ProjectLogRead(
            id=entry.id,
            project_id=entry.project_id,
            type=entry.type,
            title=entry.title,
            description=entry.description,
            source=entry.source,
            created_by_user_id=entry.created_by_user_id,
            links=await self._link_reads(entry.project_id, entry.links),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    @staticmethod
    def _meeting_read(meeting: Meeting) -> MeetingRead:
        return MeetingRead(
            id=meeting.id,
            project_id=meeting.project_id,
            title=meeting.title,
            scheduled_at=meeting.scheduled_at,
            duration_minutes=meeting.duration_minutes,
            agenda=meeting.agenda,
            notes=meeting.notes,
            status=meeting.status,
            participant_ids=[item.project_member_id for item in meeting.participants],
            action_items=[
                ActionItemRead.model_validate(item, from_attributes=True)
                for item in meeting.action_items
            ],
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )

    async def _decision_read(self, item: Decision) -> DecisionRead:
        return DecisionRead(
            id=item.id,
            project_id=item.project_id,
            meeting_id=item.meeting_id,
            title=item.title,
            decision=item.decision,
            decision_date=item.decision_date,
            decision_maker_member_id=item.decision_maker_member_id,
            reason=item.reason,
            alternatives=item.alternatives,
            selected_option=item.selected_option,
            expected_impact=item.expected_impact,
            actual_impact=item.actual_impact,
            status=item.status,
            notes=item.notes,
            links=await self._link_reads(item.project_id, item.links),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _set_log_links(entry: ProjectLogEntry, links: list[EntityLink]) -> None:
        entry.links[:] = [
            ProjectLogLink(
                project_id=entry.project_id,
                log_entry_id=entry.id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
            )
            for link in links
        ]

    async def create_log(self, project_id: UUID, data: ProjectLogCreate) -> ProjectLogRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_links(project_id, data.links)
        entry = ProjectLogEntry(
            project_id=project_id,
            type=data.type,
            title=data.title,
            description=data.description,
            source=MemorySource.MANUAL,
            created_by_user_id=self.owner_user_id,
        )
        entry.links = [
            ProjectLogLink(
                project_id=project_id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
            )
            for link in data.links
        ]
        self.session.add(entry)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="project_log.created",
            entity_type="project_log_entry",
            entity_id=entry.id,
            changes={"type": entry.type.value, "title": entry.title},
        )
        await self.session.commit()
        return await self._log_read(await self.repository.get_log(project_id, entry.id))

    async def update_log(
        self, project_id: UUID, entry_id: UUID, data: ProjectLogUpdate
    ) -> ProjectLogRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        entry = await self.repository.get_log(project_id, entry_id)
        if entry is None:
            raise AppError(
                code="project_log_not_found",
                message="Project log entry not found.",
                status_code=404,
            )
        if entry.source != MemorySource.MANUAL:
            raise AppError(
                code="system_log_read_only",
                message="Automatic project log entries are read-only.",
                status_code=409,
            )
        changes = data.model_dump(exclude_unset=True)
        links = changes.pop("links", None)
        if links is not None:
            await self._validate_links(project_id, links)
            self._set_log_links(entry, links)
        for key, value in changes.items():
            setattr(entry, key, value)
        self.audit.record(
            project_id=project_id,
            action="project_log.updated",
            entity_type="project_log_entry",
            entity_id=entry.id,
            changes={"fields": list(data.model_fields_set)},
        )
        await self.session.commit()
        return await self._log_read(await self.repository.get_log(project_id, entry.id))

    async def list_logs(self, project_id: UUID, **filters) -> ProjectLogList:
        await self._project_or_404(project_id)
        rows, total = await self.repository.list_logs(project_id, **filters)
        return ProjectLogList(items=[await self._log_read(row) for row in rows], total=total)

    async def create_meeting(self, project_id: UUID, data: MeetingCreate) -> MeetingRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_members(project_id, data.participant_ids)
        values = data.model_dump(exclude={"participant_ids"})
        meeting = Meeting(project_id=project_id, **values)
        meeting.participants = [
            MeetingParticipant(project_id=project_id, project_member_id=value)
            for value in dict.fromkeys(data.participant_ids)
        ]
        meeting.action_items = []
        self.session.add(meeting)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="meeting.created",
            entity_type="meeting",
            entity_id=meeting.id,
            changes={"title": meeting.title},
        )
        if meeting.status == MeetingStatus.COMPLETED:
            self._record_meeting_completed(meeting)
        await self.session.commit()
        return self._meeting_read(await self.repository.get_meeting(project_id, meeting.id))

    def _record_meeting_completed(self, meeting: Meeting) -> None:
        self.audit.record(
            project_id=meeting.project_id,
            action="meeting.completed",
            entity_type="meeting",
            entity_id=meeting.id,
        )
        self.record_system_log(
            self.session,
            actor_user_id=self.owner_user_id,
            project_id=meeting.project_id,
            entry_type=ProjectLogType.MEETING,
            title=f"Meeting completed: {meeting.title}",
            description=meeting.notes,
            entity_type=MemoryEntityType.MEETING,
            entity_id=meeting.id,
        )

    async def update_meeting(
        self, project_id: UUID, meeting_id: UUID, data: MeetingUpdate
    ) -> MeetingRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        meeting = await self.repository.get_meeting(project_id, meeting_id)
        if meeting is None:
            raise AppError(code="meeting_not_found", message="Meeting not found.", status_code=404)
        changes = data.model_dump(exclude_unset=True)
        participant_ids = changes.pop("participant_ids", None)
        if participant_ids is not None:
            await self._validate_members(project_id, participant_ids)
            meeting.participants[:] = [
                MeetingParticipant(
                    project_id=project_id, meeting_id=meeting.id, project_member_id=value
                )
                for value in dict.fromkeys(participant_ids)
            ]
        old_status = meeting.status
        target = changes.get("status", old_status)
        if target != old_status and old_status != MeetingStatus.PLANNED:
            raise AppError(
                code="meeting_status_locked",
                message="Completed and cancelled meetings cannot change lifecycle state.",
                status_code=409,
            )
        for key, value in changes.items():
            setattr(meeting, key, value)
        self.audit.record(
            project_id=project_id,
            action="meeting.updated",
            entity_type="meeting",
            entity_id=meeting.id,
            changes={"fields": list(data.model_fields_set)},
        )
        if target == MeetingStatus.COMPLETED and old_status != target:
            self._record_meeting_completed(meeting)
        await self.session.commit()
        return self._meeting_read(await self.repository.get_meeting(project_id, meeting.id))

    async def list_meetings(self, project_id: UUID, **filters) -> MeetingList:
        await self._project_or_404(project_id)
        rows, total = await self.repository.list_meetings(project_id, **filters)
        return MeetingList(items=[self._meeting_read(row) for row in rows], total=total)

    async def create_action_item(
        self, project_id: UUID, meeting_id: UUID, data: ActionItemCreate
    ) -> ActionItemRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        if await self.repository.get_meeting(project_id, meeting_id) is None:
            raise AppError(code="meeting_not_found", message="Meeting not found.", status_code=404)
        if data.owner_member_id:
            await self._validate_members(project_id, [data.owner_member_id])
        links = (
            [EntityLink(entity_type=MemoryEntityType.TASK, entity_id=data.task_id)]
            if data.task_id
            else []
        )
        await self._validate_links(project_id, links)
        item = MeetingActionItem(project_id=project_id, meeting_id=meeting_id, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="meeting_action.created",
            entity_type="meeting_action_item",
            entity_id=item.id,
            changes={"meeting_id": str(meeting_id)},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return ActionItemRead.model_validate(item, from_attributes=True)

    async def update_action_item(
        self, project_id: UUID, meeting_id: UUID, item_id: UUID, data: ActionItemUpdate
    ) -> ActionItemRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        item = await self.repository.get_action_item(project_id, meeting_id, item_id)
        if item is None:
            raise AppError(
                code="action_item_not_found",
                message="Meeting action item not found.",
                status_code=404,
            )
        changes = data.model_dump(exclude_unset=True)
        if "owner_member_id" in changes and changes["owner_member_id"]:
            await self._validate_members(project_id, [changes["owner_member_id"]])
        if "task_id" in changes and changes["task_id"]:
            await self._validate_links(
                project_id,
                [EntityLink(entity_type=MemoryEntityType.TASK, entity_id=changes["task_id"])],
            )
        target = changes.get("status", item.status)
        if target != item.status and target not in ACTION_TRANSITIONS[item.status]:
            raise AppError(
                code="invalid_action_item_transition",
                message=f"Action item cannot move from {item.status.value} to {target.value}.",
                status_code=409,
            )
        before = item.status
        for key, value in changes.items():
            setattr(item, key, value)
        self.audit.record(
            project_id=project_id,
            action="meeting_action.updated",
            entity_type="meeting_action_item",
            entity_id=item.id,
            changes={"from_status": before.value, "to_status": item.status.value},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return ActionItemRead.model_validate(item, from_attributes=True)

    async def create_decision(self, project_id: UUID, data: DecisionCreate) -> DecisionRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        if (
            data.meeting_id
            and await self.repository.get_meeting(project_id, data.meeting_id) is None
        ):
            raise AppError(
                code="invalid_decision_meeting",
                message="The meeting must belong to this project.",
                status_code=422,
            )
        if data.decision_maker_member_id:
            await self._validate_members(project_id, [data.decision_maker_member_id])
        await self._validate_links(project_id, data.links)
        decision = Decision(project_id=project_id, **data.model_dump(exclude={"links"}))
        decision.links = [
            DecisionLink(
                project_id=project_id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
            )
            for link in data.links
        ]
        self.session.add(decision)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="decision.created",
            entity_type="decision",
            entity_id=decision.id,
            changes={"status": decision.status.value, "title": decision.title},
        )
        if decision.status == DecisionStatus.DECIDED:
            self._record_decision(decision)
        await self.session.commit()
        return await self._decision_read(
            await self.repository.get_decision(project_id, decision.id)
        )

    def _record_decision(self, decision: Decision) -> None:
        self.audit.record(
            project_id=decision.project_id,
            action="decision.recorded",
            entity_type="decision",
            entity_id=decision.id,
        )
        self.record_system_log(
            self.session,
            actor_user_id=self.owner_user_id,
            project_id=decision.project_id,
            entry_type=ProjectLogType.DECISION,
            title=f"Decision recorded: {decision.title}",
            description=decision.decision,
            entity_type=MemoryEntityType.DECISION,
            entity_id=decision.id,
        )

    async def update_decision(
        self, project_id: UUID, decision_id: UUID, data: DecisionUpdate
    ) -> DecisionRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        decision = await self.repository.get_decision(project_id, decision_id)
        if decision is None:
            raise AppError(
                code="decision_not_found", message="Decision not found.", status_code=404
            )
        changes = data.model_dump(exclude_unset=True)
        links = changes.pop("links", None)
        if links is not None:
            await self._validate_links(project_id, links)
            decision.links[:] = [
                DecisionLink(
                    project_id=project_id,
                    decision_id=decision.id,
                    entity_type=link.entity_type,
                    entity_id=link.entity_id,
                )
                for link in links
            ]
        if (
            "meeting_id" in changes
            and changes["meeting_id"]
            and await self.repository.get_meeting(project_id, changes["meeting_id"]) is None
        ):
            raise AppError(
                code="invalid_decision_meeting",
                message="The meeting must belong to this project.",
                status_code=422,
            )
        if "decision_maker_member_id" in changes and changes["decision_maker_member_id"]:
            await self._validate_members(project_id, [changes["decision_maker_member_id"]])
        old_status = decision.status
        target = changes.get("status", old_status)
        if target != old_status and target not in DECISION_TRANSITIONS[old_status]:
            raise AppError(
                code="invalid_decision_transition",
                message=f"Decision cannot move from {old_status.value} to {target.value}.",
                status_code=409,
            )
        for key, value in changes.items():
            setattr(decision, key, value)
        self.audit.record(
            project_id=project_id,
            action="decision.updated",
            entity_type="decision",
            entity_id=decision.id,
            changes={
                "from_status": old_status.value,
                "to_status": decision.status.value,
                "fields": list(data.model_fields_set),
            },
        )
        if target == DecisionStatus.DECIDED and old_status != target:
            self._record_decision(decision)
        await self.session.commit()
        return await self._decision_read(
            await self.repository.get_decision(project_id, decision.id)
        )

    async def list_decisions(self, project_id: UUID, **filters) -> DecisionList:
        await self._project_or_404(project_id)
        rows, total = await self.repository.list_decisions(project_id, **filters)
        return DecisionList(items=[await self._decision_read(row) for row in rows], total=total)

    async def activity(self, project_id: UUID, **filters) -> ActivityList:
        await self._project_or_404(project_id)
        rows, total = await self.repository.list_activity(project_id, **filters)
        links = []
        mapped = {}
        for event, _ in rows:
            try:
                kind = MemoryEntityType(event.entity_type.upper())
            except ValueError:
                continue
            link = EntityLink(entity_type=kind, entity_id=event.entity_id)
            links.append(link)
            mapped[event.id] = link
        names = await self.repository.entity_names(project_id, links)
        items = [
            ActivityRead(
                id=event.id,
                actor_user_id=event.actor_user_id,
                actor_email=email,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                entity_name=names.get((mapped[event.id].entity_type, event.entity_id))
                if event.id in mapped
                else None,
                changes=event.changes,
                created_at=event.created_at,
            )
            for event, email in rows
        ]
        return ActivityList(items=items, total=total)

    async def summary(self, project_id: UUID) -> MemorySummary:
        await self._project_or_404(project_id)
        meetings, _ = await self.repository.list_meetings(
            project_id, search=None, status=None, sort_order="desc"
        )
        decisions, _ = await self.repository.list_decisions(
            project_id, search=None, status=None, sort_order="desc"
        )
        logs, _ = await self.repository.list_logs(
            project_id, search=None, entry_type=None, source=None, sort_order="desc"
        )
        return MemorySummary(
            recent_meetings=[
                MemorySummaryItem(
                    id=item.id,
                    title=item.title,
                    status=item.status.value,
                    occurred_at=item.scheduled_at,
                )
                for item in meetings[:3]
            ],
            recent_decisions=[
                MemorySummaryItem(
                    id=item.id,
                    title=item.title,
                    status=item.status.value,
                    occurred_at=item.decision_date,
                )
                for item in decisions[:3]
            ],
            recent_log_entries=[
                MemorySummaryItem(
                    id=item.id,
                    title=item.title,
                    status=item.type.value,
                    occurred_at=item.created_at,
                )
                for item in logs[:3]
            ],
            pending_action_items=await self.repository.pending_action_count(project_id),
        )
