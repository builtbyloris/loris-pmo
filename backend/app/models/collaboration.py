"""Project access memberships and bounded collaboration records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ProjectAccessRole(StrEnum):
    OWNER = "OWNER"
    PROJECT_ADMIN = "PROJECT_ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    CONTRIBUTOR = "CONTRIBUTOR"
    VIEWER = "VIEWER"


class MembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    DISABLED = "DISABLED"


class CommentEntityType(StrEnum):
    TASK = "TASK"
    RISK = "RISK"
    ISSUE = "ISSUE"
    CHANGE_REQUEST = "CHANGE_REQUEST"
    MEETING = "MEETING"
    DECISION = "DECISION"


class NotificationType(StrEnum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    COMMENT_ADDED = "COMMENT_ADDED"
    MENTIONED = "MENTIONED"
    MEMBER_ADDED = "MEMBER_ADDED"
    ROLE_CHANGED = "ROLE_CHANGED"
    MEETING_ACTION_ASSIGNED = "MEETING_ACTION_ASSIGNED"
    RISK_ASSIGNED = "RISK_ASSIGNED"
    ISSUE_ASSIGNED = "ISSUE_ASSIGNED"


project_access_role_enum = Enum(
    ProjectAccessRole,
    name="project_access_role",
    native_enum=False,
    validate_strings=True,
)
membership_status_enum = Enum(
    MembershipStatus,
    name="membership_status",
    native_enum=False,
    validate_strings=True,
)
comment_entity_type_enum = Enum(
    CommentEntityType,
    name="comment_entity_type",
    native_enum=False,
    validate_strings=True,
)
notification_type_enum = Enum(
    NotificationType,
    name="notification_type",
    native_enum=False,
    validate_strings=True,
)


class ProjectMembership(UUIDTimestampMixin, Base):
    """A user's authorization relationship with one project.

    This is deliberately separate from ``ProjectMember``: the latter links a
    reusable Person to delivery work, while this table grants authenticated
    application access.
    """

    __tablename__ = "project_memberships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "person_id"],
            ["project_members.project_id", "project_members.person_id"],
            name="fk_project_membership_project_person",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("project_id", "user_id", name="uq_project_membership_user"),
        UniqueConstraint("project_id", "person_id", name="uq_project_membership_person"),
        Index("ix_project_memberships_user_status", "user_id", "status"),
        Index("ix_project_memberships_project_role", "project_id", "role", "status"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    person_id: Mapped[UUID | None] = mapped_column(nullable=True)
    role: Mapped[ProjectAccessRole] = mapped_column(project_access_role_enum, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        membership_status_enum, nullable=False, default=MembershipStatus.ACTIVE
    )
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    invited_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])


class CollaborationComment(UUIDTimestampMixin, Base):
    __tablename__ = "collaboration_comments"
    __table_args__ = (
        CheckConstraint("length(body) > 0", name="ck_collaboration_comment_body"),
        Index(
            "ix_collaboration_comments_target",
            "project_id",
            "entity_type",
            "entity_id",
            "created_at",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[CommentEntityType] = mapped_column(comment_entity_type_enum, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    author_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    author: Mapped[User] = relationship(foreign_keys=[author_user_id])


class Notification(UUIDTimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_read", "user_id", "read_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[NotificationType] = mapped_column(notification_type_enum, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
