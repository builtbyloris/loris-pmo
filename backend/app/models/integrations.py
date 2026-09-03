"""User-owned provider accounts and explicit project external links."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDTimestampMixin


class IntegrationProvider(StrEnum):
    GOOGLE = "GOOGLE"
    GITHUB = "GITHUB"


class IntegrationAccountStatus(StrEnum):
    CONNECTED = "CONNECTED"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"
    ERROR = "ERROR"
    DISCONNECTED = "DISCONNECTED"


class ProjectIntegrationKind(StrEnum):
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    GMAIL = "GMAIL"
    GITHUB_REPOSITORY = "GITHUB_REPOSITORY"


class ProjectIntegrationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class ExternalObjectType(StrEnum):
    CALENDAR_EVENT = "CALENDAR_EVENT"
    EMAIL_MESSAGE = "EMAIL_MESSAGE"
    GITHUB_ISSUE = "GITHUB_ISSUE"
    GITHUB_PULL_REQUEST = "GITHUB_PULL_REQUEST"
    GITHUB_COMMIT = "GITHUB_COMMIT"


class ExternalLinkVisibility(StrEnum):
    PRIVATE = "PRIVATE"
    PROJECT = "PROJECT"
    FINANCE = "FINANCE"


provider_enum = Enum(IntegrationProvider, name="integration_provider", native_enum=False)
account_status_enum = Enum(
    IntegrationAccountStatus, name="integration_account_status", native_enum=False
)
integration_kind_enum = Enum(
    ProjectIntegrationKind, name="project_integration_kind", native_enum=False
)
integration_status_enum = Enum(
    ProjectIntegrationStatus, name="project_integration_status", native_enum=False
)
external_object_type_enum = Enum(ExternalObjectType, name="external_object_type", native_enum=False)
external_visibility_enum = Enum(
    ExternalLinkVisibility, name="external_link_visibility", native_enum=False
)


class IntegrationAccount(UUIDTimestampMixin, Base):
    __tablename__ = "integration_accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider", "provider_account_id", name="uq_integration_account_identity"
        ),
        Index("ix_integration_accounts_user_provider", "user_id", "provider"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[IntegrationProvider] = mapped_column(provider_enum, nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[IntegrationAccountStatus] = mapped_column(
        account_status_enum, default=IntegrationAccountStatus.CONNECTED, nullable=False
    )
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    safe_provider_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationOAuthState(UUIDTimestampMixin, Base):
    __tablename__ = "integration_oauth_states"
    __table_args__ = (
        UniqueConstraint("state_digest", name="uq_integration_oauth_state_digest"),
        Index("ix_integration_oauth_states_expiry", "expires_at", "consumed_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[IntegrationProvider] = mapped_column(provider_enum, nullable=False)
    state_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_code_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    return_path: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectIntegration(UUIDTimestampMixin, Base):
    __tablename__ = "project_integrations"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "kind", "external_resource_id", name="uq_project_integration_resource"
        ),
        Index("ix_project_integrations_project_kind", "project_id", "kind", "status"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    integration_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("integration_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[ProjectIntegrationKind] = mapped_column(integration_kind_enum, nullable=False)
    external_resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ProjectIntegrationStatus] = mapped_column(
        integration_status_enum, default=ProjectIntegrationStatus.ACTIVE, nullable=False
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalLink(UUIDTimestampMixin, Base):
    __tablename__ = "external_links"
    __table_args__ = (
        UniqueConstraint(
            "project_integration_id",
            "object_type",
            "external_id",
            "target_entity_type",
            "target_entity_id",
            name="uq_external_link_target",
        ),
        Index("ix_external_links_project_created", "project_id", "created_at"),
        Index("ix_external_links_target", "project_id", "target_entity_type", "target_entity_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project_integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_integrations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    object_type: Mapped[ExternalObjectType] = mapped_column(
        external_object_type_enum, nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    external_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    safe_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    visibility: Mapped[ExternalLinkVisibility] = mapped_column(
        external_visibility_enum, default=ExternalLinkVisibility.PROJECT, nullable=False
    )
    target_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_entity_id: Mapped[UUID] = mapped_column(nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    available: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
