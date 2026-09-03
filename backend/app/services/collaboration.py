"""Project collaboration workflows with server-side authorization."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.collaboration import (
    CollaborationComment,
    CommentEntityType,
    MembershipStatus,
    Notification,
    NotificationType,
    ProjectAccessRole,
    ProjectMembership,
)
from app.models.control import ChangeRequest, Issue, Risk
from app.models.memory import Decision, Meeting
from app.models.people import Person, ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.collaboration import (
    CollaboratorCreate,
    CollaboratorRead,
    CollaboratorUpdate,
    CommentCreate,
    CommentRead,
    CommentUpdate,
    NotificationList,
    NotificationRead,
    ProjectAccessRead,
)
from app.services.audit import AuditService
from app.services.authorization import AuthorizationService, Capability

TARGET_MODELS = {
    CommentEntityType.TASK: Task,
    CommentEntityType.RISK: Risk,
    CommentEntityType.ISSUE: Issue,
    CommentEntityType.CHANGE_REQUEST: ChangeRequest,
    CommentEntityType.MEETING: Meeting,
    CommentEntityType.DECISION: Decision,
}


class CollaborationService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self.authorization = AuthorizationService(session, user_id)
        self.audit = AuditService(session, user_id)

    async def access(self, project_id: UUID) -> ProjectAccessRead:
        membership = await self.authorization.membership(project_id)
        return ProjectAccessRead(
            project_id=project_id,
            role=membership.role,
            status=membership.status,
            capabilities=self.authorization.capabilities(membership.role),
        )

    async def _validate_person(self, project_id: UUID, person_id: UUID | None) -> None:
        if person_id is None:
            return
        exists = await self.session.scalar(
            select(func.count(ProjectMember.id)).where(
                ProjectMember.project_id == project_id, ProjectMember.person_id == person_id
            )
        )
        if not exists:
            raise AppError(
                code="project_person_not_found",
                message="Project person not found.",
                status_code=422,
            )

    async def _collaborator_read(self, membership: ProjectMembership) -> CollaboratorRead:
        row = (
            await self.session.execute(
                select(User.email, User.display_name, Person.name)
                .select_from(User)
                .outerjoin(Person, Person.id == membership.person_id)
                .where(User.id == membership.user_id)
            )
        ).one()
        return CollaboratorRead(
            id=membership.id,
            project_id=membership.project_id,
            user_id=membership.user_id,
            email=row.email,
            display_name=row.display_name,
            role=membership.role,
            status=membership.status,
            person_id=membership.person_id,
            person_name=row.name,
            joined_at=membership.joined_at,
            invited_at=membership.invited_at,
            created_at=membership.created_at,
        )

    async def list_collaborators(self, project_id: UUID) -> list[CollaboratorRead]:
        await self.authorization.require(project_id, Capability.MEMBERS_READ)
        memberships = list(
            (
                await self.session.scalars(
                    select(ProjectMembership)
                    .where(ProjectMembership.project_id == project_id)
                    .order_by(ProjectMembership.created_at, ProjectMembership.id)
                )
            ).all()
        )
        return [await self._collaborator_read(item) for item in memberships]

    async def add_collaborator(
        self, project_id: UUID, data: CollaboratorCreate
    ) -> CollaboratorRead:
        actor = await self.authorization.require(project_id, Capability.MEMBERS_MANAGE)
        if (
            actor.role == ProjectAccessRole.PROJECT_ADMIN
            and data.role == ProjectAccessRole.PROJECT_ADMIN
        ):
            raise AppError(
                code="role_elevation_forbidden",
                message="Only the project owner may add project administrators.",
                status_code=403,
            )
        user = (
            await self.session.execute(select(User).where(User.email == str(data.email).lower()))
        ).scalar_one_or_none()
        if user is None:
            raise AppError(
                code="user_not_found",
                message="No existing user matches that email.",
                status_code=404,
            )
        existing = (
            await self.session.execute(
                select(ProjectMembership).where(
                    ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AppError(
                code="project_member_exists",
                message="This user already has project access.",
                status_code=409,
            )
        await self._validate_person(project_id, data.person_id)
        now = datetime.now(UTC)
        membership = ProjectMembership(
            project_id=project_id,
            user_id=user.id,
            person_id=data.person_id,
            role=data.role,
            status=MembershipStatus.ACTIVE,
            joined_at=now,
            created_by_user_id=self.user_id,
        )
        self.session.add(membership)
        await self.session.flush()
        self.session.add(
            Notification(
                user_id=user.id,
                project_id=project_id,
                type=NotificationType.MEMBER_ADDED,
                title="Project access granted",
                message=f"You were added as {data.role.value}.",
                entity_type="PROJECT_MEMBERSHIP",
                entity_id=membership.id,
            )
        )
        self.audit.record(
            project_id=project_id,
            action="project_membership.created",
            entity_type="project_membership",
            entity_id=membership.id,
            changes={"user_id": str(user.id), "role": data.role.value},
        )
        await self.session.commit()
        await self.session.refresh(membership)
        return await self._collaborator_read(membership)

    async def update_collaborator(
        self, project_id: UUID, membership_id: UUID, data: CollaboratorUpdate
    ) -> CollaboratorRead:
        actor = await self.authorization.require(project_id, Capability.MEMBERS_MANAGE)
        membership = await self.session.get(ProjectMembership, membership_id)
        if membership is None or membership.project_id != project_id:
            raise AppError(
                code="project_member_not_found",
                message="Project member not found.",
                status_code=404,
            )
        if membership.role == ProjectAccessRole.OWNER:
            raise AppError(
                code="owner_membership_immutable",
                message="The owner membership cannot be changed.",
                status_code=409,
            )
        values = data.model_dump(exclude_unset=True)
        if "role" in values:
            await self.authorization.require(project_id, Capability.MEMBERS_CHANGE_ROLE)
            if actor.role == ProjectAccessRole.PROJECT_ADMIN and (
                membership.role == ProjectAccessRole.PROJECT_ADMIN
                or values["role"] == ProjectAccessRole.PROJECT_ADMIN
            ):
                raise AppError(
                    code="role_elevation_forbidden",
                    message="Only the project owner may manage project administrators.",
                    status_code=403,
                )
        if "person_id" in values:
            await self._validate_person(project_id, values["person_id"])
        before_role = membership.role
        for key, value in values.items():
            setattr(membership, key, value)
        if membership.status == MembershipStatus.ACTIVE and membership.joined_at is None:
            membership.joined_at = datetime.now(UTC)
        await self.session.flush()
        if membership.role != before_role:
            self.session.add(
                Notification(
                    user_id=membership.user_id,
                    project_id=project_id,
                    type=NotificationType.ROLE_CHANGED,
                    title="Project role changed",
                    message=f"Your role is now {membership.role.value}.",
                    entity_type="PROJECT_MEMBERSHIP",
                    entity_id=membership.id,
                )
            )
        self.audit.record(
            project_id=project_id,
            action="project_membership.updated",
            entity_type="project_membership",
            entity_id=membership.id,
            changes={"fields": sorted(values)},
        )
        await self.session.commit()
        await self.session.refresh(membership)
        return await self._collaborator_read(membership)

    async def remove_collaborator(self, project_id: UUID, membership_id: UUID) -> None:
        await self.authorization.require(project_id, Capability.MEMBERS_MANAGE)
        membership = await self.session.get(ProjectMembership, membership_id)
        if membership is None or membership.project_id != project_id:
            raise AppError(
                code="project_member_not_found",
                message="Project member not found.",
                status_code=404,
            )
        if membership.role == ProjectAccessRole.OWNER:
            raise AppError(
                code="owner_membership_immutable",
                message="The owner membership cannot be removed.",
                status_code=409,
            )
        actor = await self.authorization.membership(project_id)
        if (
            actor.role == ProjectAccessRole.PROJECT_ADMIN
            and membership.role == ProjectAccessRole.PROJECT_ADMIN
        ):
            raise AppError(
                code="role_elevation_forbidden",
                message="Only the project owner may remove project administrators.",
                status_code=403,
            )
        self.audit.record(
            project_id=project_id,
            action="project_membership.removed",
            entity_type="project_membership",
            entity_id=membership.id,
            changes={"user_id": str(membership.user_id), "role": membership.role.value},
        )
        await self.session.delete(membership)
        await self.session.commit()

    async def _validate_target(
        self, project_id: UUID, entity_type: CommentEntityType, entity_id: UUID
    ) -> None:
        model = TARGET_MODELS[entity_type]
        exists = await self.session.scalar(
            select(func.count(model.id)).where(
                model.id == entity_id, model.project_id == project_id
            )
        )
        if not exists:
            raise AppError(
                code="comment_target_not_found",
                message="Comment target not found.",
                status_code=404,
            )

    async def _comment_read(self, item: CollaborationComment, can_manage: bool) -> CommentRead:
        author = await self.session.get(User, item.author_user_id)
        assert author is not None
        return CommentRead(
            id=item.id,
            project_id=item.project_id,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            author_user_id=item.author_user_id,
            author_email=author.email,
            author_display_name=author.display_name,
            body=item.body,
            created_at=item.created_at,
            updated_at=item.updated_at,
            can_edit=item.author_user_id == self.user_id or can_manage,
        )

    async def list_comments(
        self, project_id: UUID, entity_type: CommentEntityType, entity_id: UUID
    ) -> list[CommentRead]:
        await self.authorization.require(project_id, Capability.COMMENTS_READ)
        await self._validate_target(project_id, entity_type, entity_id)
        items = list(
            (
                await self.session.scalars(
                    select(CollaborationComment)
                    .where(
                        CollaborationComment.project_id == project_id,
                        CollaborationComment.entity_type == entity_type,
                        CollaborationComment.entity_id == entity_id,
                        CollaborationComment.deleted_at.is_(None),
                    )
                    .order_by(CollaborationComment.created_at)
                    .limit(200)
                )
            ).all()
        )
        can_manage = await self.authorization.can(project_id, Capability.MEMBERS_MANAGE)
        return [await self._comment_read(item, can_manage) for item in items]

    async def create_comment(self, project_id: UUID, data: CommentCreate) -> CommentRead:
        await self.authorization.require(project_id, Capability.COMMENTS_WRITE)
        await self._validate_target(project_id, data.entity_type, data.entity_id)
        item = CollaborationComment(
            project_id=project_id, author_user_id=self.user_id, **data.model_dump()
        )
        self.session.add(item)
        await self.session.flush()
        recipients = list(
            (
                await self.session.scalars(
                    select(ProjectMembership.user_id)
                    .where(
                        ProjectMembership.project_id == project_id,
                        ProjectMembership.status == MembershipStatus.ACTIVE,
                        ProjectMembership.user_id != self.user_id,
                    )
                    .limit(100)
                )
            ).all()
        )
        target_label = data.entity_type.value.lower().replace("_", " ")
        for recipient in recipients:
            self.session.add(
                Notification(
                    user_id=recipient,
                    project_id=project_id,
                    type=NotificationType.COMMENT_ADDED,
                    title="New project comment",
                    message=f"A comment was added to {target_label}.",
                    entity_type=data.entity_type.value,
                    entity_id=data.entity_id,
                )
            )
        self.audit.record(
            project_id=project_id,
            action="comment.created",
            entity_type="comment",
            entity_id=item.id,
            changes={"target_type": data.entity_type.value, "target_id": str(data.entity_id)},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return await self._comment_read(item, False)

    async def update_comment(
        self, project_id: UUID, comment_id: UUID, data: CommentUpdate
    ) -> CommentRead:
        await self.authorization.require(project_id, Capability.COMMENTS_WRITE)
        item = await self.session.get(CollaborationComment, comment_id)
        if item is None or item.project_id != project_id or item.deleted_at is not None:
            raise AppError(code="comment_not_found", message="Comment not found.", status_code=404)
        can_manage = await self.authorization.can(project_id, Capability.MEMBERS_MANAGE)
        if item.author_user_id != self.user_id and not can_manage:
            raise AppError(
                code="comment_forbidden",
                message="Only the author or project administration may edit this comment.",
                status_code=403,
            )
        item.body = data.body
        self.audit.record(
            project_id=project_id,
            action="comment.updated",
            entity_type="comment",
            entity_id=item.id,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return await self._comment_read(item, can_manage)

    async def delete_comment(self, project_id: UUID, comment_id: UUID) -> None:
        await self.authorization.require(project_id, Capability.COMMENTS_WRITE)
        item = await self.session.get(CollaborationComment, comment_id)
        if item is None or item.project_id != project_id or item.deleted_at is not None:
            raise AppError(code="comment_not_found", message="Comment not found.", status_code=404)
        can_manage = await self.authorization.can(project_id, Capability.MEMBERS_MANAGE)
        if item.author_user_id != self.user_id and not can_manage:
            raise AppError(
                code="comment_forbidden",
                message="Only the author or project administration may delete this comment.",
                status_code=403,
            )
        item.deleted_at = datetime.now(UTC)
        self.audit.record(
            project_id=project_id,
            action="comment.deleted",
            entity_type="comment",
            entity_id=item.id,
        )
        await self.session.commit()


class NotificationService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    async def list(self, limit: int = 50) -> NotificationList:
        items = list(
            (
                await self.session.scalars(
                    select(Notification)
                    .where(Notification.user_id == self.user_id)
                    .order_by(Notification.created_at.desc())
                    .limit(min(limit, 100))
                )
            ).all()
        )
        unread = int(
            await self.session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == self.user_id, Notification.read_at.is_(None)
                )
            )
            or 0
        )
        return NotificationList(
            items=[NotificationRead.model_validate(item) for item in items], unread_count=unread
        )

    async def mark_read(self, notification_id: UUID) -> NotificationRead:
        item = await self.session.get(Notification, notification_id)
        if item is None or item.user_id != self.user_id:
            raise AppError(
                code="notification_not_found", message="Notification not found.", status_code=404
            )
        item.read_at = item.read_at or datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(item)
        return NotificationRead.model_validate(item)

    async def mark_all_read(self) -> None:
        items = list(
            (
                await self.session.scalars(
                    select(Notification).where(
                        Notification.user_id == self.user_id, Notification.read_at.is_(None)
                    )
                )
            ).all()
        )
        now = datetime.now(UTC)
        for item in items:
            item.read_at = now
        await self.session.commit()
