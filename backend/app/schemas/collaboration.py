"""Schemas for V2.1 memberships, comments, and notifications."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.collaboration import (
    CommentEntityType,
    MembershipStatus,
    NotificationType,
    ProjectAccessRole,
)


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectAccessRead(APIModel):
    project_id: UUID
    role: ProjectAccessRole
    status: MembershipStatus
    capabilities: list[str]


class CollaboratorCreate(APIModel):
    email: EmailStr
    role: ProjectAccessRole
    person_id: UUID | None = None

    @model_validator(mode="after")
    def prohibit_owner_role(self) -> "CollaboratorCreate":
        if self.role == ProjectAccessRole.OWNER:
            raise ValueError("Project ownership cannot be assigned through memberships")
        return self


class CollaboratorUpdate(APIModel):
    role: ProjectAccessRole | None = None
    status: MembershipStatus | None = None
    person_id: UUID | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "CollaboratorUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if self.role == ProjectAccessRole.OWNER:
            raise ValueError("Project ownership cannot be assigned through memberships")
        return self


class CollaboratorRead(APIModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    email: EmailStr
    display_name: str | None
    role: ProjectAccessRole
    status: MembershipStatus
    person_id: UUID | None
    person_name: str | None
    joined_at: datetime | None
    invited_at: datetime | None
    created_at: datetime


class CommentCreate(APIModel):
    entity_type: CommentEntityType
    entity_id: UUID
    body: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def normalize_body(self) -> "CommentCreate":
        self.body = self.body.strip()
        if not self.body:
            raise ValueError("Comment body cannot be blank")
        return self


class CommentUpdate(APIModel):
    body: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def normalize_body(self) -> "CommentUpdate":
        self.body = self.body.strip()
        if not self.body:
            raise ValueError("Comment body cannot be blank")
        return self


class CommentRead(APIModel):
    id: UUID
    project_id: UUID
    entity_type: CommentEntityType
    entity_id: UUID
    author_user_id: UUID
    author_email: EmailStr
    author_display_name: str | None
    body: str
    created_at: datetime
    updated_at: datetime
    can_edit: bool


class NotificationRead(APIModel):
    id: UUID
    project_id: UUID | None
    type: NotificationType
    title: str
    message: str
    entity_type: str | None
    entity_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(APIModel):
    items: list[NotificationRead]
    unread_count: int


class ProfileUpdate(APIModel):
    display_name: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def normalize_display_name(self) -> "ProfileUpdate":
        if self.display_name is not None:
            self.display_name = self.display_name.strip() or None
        return self
