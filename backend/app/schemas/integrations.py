from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.integrations import (
    ExternalLinkVisibility,
    ExternalObjectType,
    IntegrationAccountStatus,
    IntegrationProvider,
    ProjectIntegrationKind,
    ProjectIntegrationStatus,
)


class ProviderStatusRead(BaseModel):
    provider: IntegrationProvider
    configured: bool
    reason: str | None = None


class IntegrationsStatusRead(BaseModel):
    encryption_configured: bool
    providers: list[ProviderStatusRead]


class OAuthStartRequest(BaseModel):
    return_path: str = Field(default="/projects", min_length=1, max_length=500)

    @field_validator("return_path")
    @classmethod
    def local_return_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("return_path must be a local application path")
        return value


class OAuthStartRead(BaseModel):
    authorization_url: str
    expires_at: datetime


class IntegrationAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: IntegrationProvider
    provider_account_id: str
    display_name: str
    status: IntegrationAccountStatus
    scopes: list[str]
    safe_provider_metadata: dict
    token_expires_at: datetime | None
    last_used_at: datetime | None
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectIntegrationCreate(BaseModel):
    integration_account_id: UUID
    kind: ProjectIntegrationKind
    external_resource_id: str = Field(min_length=1, max_length=500)
    display_name: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def account_provider_matches_kind(self) -> "ProjectIntegrationCreate":
        self.external_resource_id = self.external_resource_id.strip()
        self.display_name = self.display_name.strip()
        return self


class ProjectIntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    integration_account_id: UUID
    created_by_user_id: UUID
    kind: ProjectIntegrationKind
    external_resource_id: str
    display_name: str
    status: ProjectIntegrationStatus
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CalendarRead(BaseModel):
    id: str
    name: str
    primary: bool


class CalendarEventRead(BaseModel):
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None
    description: str | None
    location: str | None
    attendees: list[str]
    url: str
    updated_at: datetime | None


class CalendarEventQuery(BaseModel):
    time_min: datetime
    time_max: datetime

    @model_validator(mode="after")
    def bounded_window(self) -> "CalendarEventQuery":
        if self.time_min.tzinfo is None or self.time_max.tzinfo is None:
            raise ValueError("calendar query times must include a timezone")
        if self.time_max <= self.time_min:
            raise ValueError("time_max must follow time_min")
        if (self.time_max - self.time_min).days > 93:
            raise ValueError("calendar query window cannot exceed 93 days")
        return self


class CalendarMeetingPreviewRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=500)


class CalendarMeetingPreviewRead(BaseModel):
    event: CalendarEventRead
    confirmation_token: str
    expires_at: datetime


class CalendarMeetingConfirmRequest(BaseModel):
    confirmation_token: str = Field(min_length=1, max_length=10000)


class ImportedMeetingRead(BaseModel):
    meeting_id: UUID
    external_link_id: UUID
    already_imported: bool


class EmailSearchRead(BaseModel):
    id: str
    thread_id: str | None
    subject: str
    sender: str | None
    sent_at: str | None
    snippet: str | None
    url: str


class EmailLinkCreate(BaseModel):
    message_id: str = Field(min_length=1, max_length=500)
    visibility: ExternalLinkVisibility = ExternalLinkVisibility.PRIVATE
    target_entity_type: Literal["PROJECT", "MEETING", "TASK", "ISSUE"] = "PROJECT"
    target_entity_id: UUID = None

    @model_validator(mode="after")
    def target_required(self) -> "EmailLinkCreate":
        if self.target_entity_type != "PROJECT" and self.target_entity_id is None:
            raise ValueError("target_entity_id is required for a non-project target")
        if self.target_entity_type == "PROJECT" and self.target_entity_id is not None:
            raise ValueError("project links do not accept target_entity_id")
        return self


class RepositoryRead(BaseModel):
    id: str
    full_name: str
    private: bool
    url: str
    default_branch: str | None


class SourceObjectRead(BaseModel):
    id: str
    number: int | None
    title: str
    state: str | None
    url: str
    summary: str | None
    metadata: dict[str, object]


class GitHubTaskLinkCreate(BaseModel):
    object_type: Literal["GITHUB_ISSUE", "GITHUB_PULL_REQUEST", "GITHUB_COMMIT"]
    external_id: str = Field(min_length=1, max_length=500)
    task_id: UUID
    relationship_type: Literal["IMPLEMENTS", "TRACKS", "RELATES_TO"] = "RELATES_TO"


class ExternalLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_integration_id: UUID
    created_by_user_id: UUID
    object_type: ExternalObjectType
    external_id: str
    external_url: str
    title: str
    summary: str | None
    safe_metadata: dict
    visibility: ExternalLinkVisibility
    target_entity_type: str
    target_entity_id: UUID
    relationship_type: str | None
    available: bool
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime
