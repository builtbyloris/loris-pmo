from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.integrations.crypto import IntegrationTokenCipher
from app.integrations.github import GitHubAdapter
from app.integrations.google import GoogleAdapter
from app.integrations.provider import ProviderError, ProviderFailureKind
from app.models.control import Issue
from app.models.integrations import (
    ExternalLink,
    ExternalLinkVisibility,
    ExternalObjectType,
    IntegrationAccount,
    IntegrationAccountStatus,
    IntegrationOAuthState,
    IntegrationProvider,
    ProjectIntegration,
    ProjectIntegrationKind,
    ProjectIntegrationStatus,
)
from app.models.memory import MemoryEntityType, ProjectLogType
from app.models.task import Task
from app.schemas.integrations import (
    CalendarEventRead,
    CalendarMeetingPreviewRead,
    EmailLinkCreate,
    ExternalLinkRead,
    GitHubTaskLinkCreate,
    ImportedMeetingRead,
    IntegrationAccountRead,
    OAuthStartRead,
    ProjectIntegrationCreate,
    ProjectIntegrationRead,
    ProviderStatusRead,
)
from app.schemas.memory import MeetingCreate
from app.services.audit import AuditService
from app.services.authorization import AuthorizationService, Capability
from app.services.memory import MemoryService

OAUTH_STATE_MINUTES = 10
CALENDAR_CONFIRM_MINUTES = 10
EXTERNAL_TEXT_LIMIT = 1000


class IntegrationService:
    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID,
        settings: Settings,
        *,
        google: GoogleAdapter | None = None,
        github: GitHubAdapter | None = None,
    ) -> None:
        self.session = session
        self.user_id = user_id
        self.settings = settings
        self.cipher = IntegrationTokenCipher(settings.integration_token_encryption_key)
        self.google = google or GoogleAdapter(settings)
        self.github = github or GitHubAdapter(settings)
        self.authorization = AuthorizationService(session, user_id)
        self.audit = AuditService(session, user_id)

    def provider_statuses(self) -> list[ProviderStatusRead]:
        return [
            ProviderStatusRead(
                provider=IntegrationProvider.GOOGLE,
                configured=self.google.configured,
                reason=None if self.google.configured else "Google OAuth is not configured.",
            ),
            ProviderStatusRead(
                provider=IntegrationProvider.GITHUB,
                configured=self.github.configured,
                reason=None if self.github.configured else "GitHub OAuth is not configured.",
            ),
        ]

    async def accounts(self) -> list[IntegrationAccountRead]:
        items = list(
            (
                await self.session.scalars(
                    select(IntegrationAccount)
                    .where(IntegrationAccount.user_id == self.user_id)
                    .order_by(IntegrationAccount.provider, IntegrationAccount.display_name)
                )
            ).all()
        )
        return [IntegrationAccountRead.model_validate(item) for item in items]

    async def start_oauth(self, provider: IntegrationProvider, return_path: str) -> OAuthStartRead:
        adapter, redirect_uri = self._oauth_adapter(provider)
        if not self.cipher.available or not adapter.configured:
            raise AppError(
                code="integrations_not_configured",
                message="This integration provider is not configured.",
                status_code=503,
            )
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        expires_at = datetime.now(UTC) + timedelta(minutes=OAUTH_STATE_MINUTES)
        self.session.add(
            IntegrationOAuthState(
                user_id=self.user_id,
                provider=provider,
                state_digest=self._digest(state),
                encrypted_code_verifier=self.cipher.encrypt(verifier),
                redirect_uri=redirect_uri,
                return_path=return_path,
                expires_at=expires_at,
            )
        )
        await self.session.commit()
        try:
            authorization_url = adapter.authorization_url(
                state=state, code_challenge=challenge, redirect_uri=redirect_uri
            )
        except ProviderError as exc:
            raise self._app_error(exc) from exc
        return OAuthStartRead(authorization_url=authorization_url, expires_at=expires_at)

    async def complete_oauth(
        self, provider: IntegrationProvider, state: str, code: str
    ) -> tuple[IntegrationAccountRead, str]:
        now = datetime.now(UTC)
        oauth_state = await self.session.scalar(
            select(IntegrationOAuthState).where(
                IntegrationOAuthState.state_digest == self._digest(state),
                IntegrationOAuthState.provider == provider,
                IntegrationOAuthState.user_id == self.user_id,
                IntegrationOAuthState.consumed_at.is_(None),
            )
        )
        if oauth_state is None or self._as_utc(oauth_state.expires_at) <= now:
            raise AppError(
                code="invalid_oauth_state",
                message="The integration authorization has expired or is invalid.",
                status_code=400,
            )
        # Consume before making the provider request: state is single-use even when exchange fails.
        if not oauth_state.encrypted_code_verifier:
            raise AppError(
                code="invalid_oauth_state",
                message="The integration authorization has expired or is invalid.",
                status_code=400,
            )
        code_verifier = self.cipher.decrypt(oauth_state.encrypted_code_verifier)
        oauth_state.encrypted_code_verifier = None
        oauth_state.consumed_at = now
        await self.session.commit()
        adapter, _ = self._oauth_adapter(provider)
        try:
            token = await adapter.exchange_code(
                code=code,
                code_verifier=code_verifier,
                redirect_uri=oauth_state.redirect_uri,
            )
            identity = await adapter.identity(token.access_token)
        except ProviderError as exc:
            raise self._app_error(exc) from exc
        account = await self.session.scalar(
            select(IntegrationAccount).where(
                IntegrationAccount.user_id == self.user_id,
                IntegrationAccount.provider == provider,
                IntegrationAccount.provider_account_id == identity.account_id,
            )
        )
        if account is None:
            account = IntegrationAccount(
                user_id=self.user_id,
                provider=provider,
                provider_account_id=identity.account_id,
                display_name=identity.display_name,
                encrypted_access_token=self.cipher.encrypt(token.access_token),
            )
            self.session.add(account)
            await self.session.flush()
        account.display_name = identity.display_name
        account.status = IntegrationAccountStatus.CONNECTED
        account.scopes = list(token.scopes)
        account.safe_provider_metadata = {"identity_verified": True}
        account.encrypted_access_token = self.cipher.encrypt(token.access_token)
        if token.refresh_token:
            account.encrypted_refresh_token = self.cipher.encrypt(token.refresh_token)
        account.token_expires_at = token.expires_at
        self.audit.record(
            project_id=None,
            action="integration.account_connected",
            entity_type="integration_account",
            entity_id=account.id,
            changes={"provider": provider.value},
        )
        await self.session.commit()
        await self.session.refresh(account)
        return IntegrationAccountRead.model_validate(account), oauth_state.return_path

    async def disconnect_account(self, account_id: UUID) -> None:
        account = await self._account(account_id)
        try:
            adapter, _ = self._oauth_adapter(account.provider)
            if account.encrypted_access_token:
                await adapter.revoke(self.cipher.decrypt(account.encrypted_access_token))
        except (ProviderError, AppError):
            # Local credential deletion must still succeed if remote revocation is unavailable.
            pass
        self.audit.record(
            project_id=None,
            action="integration.account_disconnected",
            entity_type="integration_account",
            entity_id=account.id,
            changes={"provider": account.provider.value},
        )
        account.status = IntegrationAccountStatus.DISCONNECTED
        account.encrypted_access_token = None
        account.encrypted_refresh_token = None
        account.token_expires_at = None
        project_connections = list(
            (
                await self.session.scalars(
                    select(ProjectIntegration).where(
                        ProjectIntegration.integration_account_id == account.id
                    )
                )
            ).all()
        )
        for connection in project_connections:
            connection.status = ProjectIntegrationStatus.UNAVAILABLE
        connection_ids = [connection.id for connection in project_connections]
        if connection_ids:
            external_links = list(
                (
                    await self.session.scalars(
                        select(ExternalLink).where(
                            ExternalLink.project_integration_id.in_(connection_ids)
                        )
                    )
                ).all()
            )
            for link in external_links:
                link.available = False
                link.last_checked_at = datetime.now(UTC)
        await self.session.commit()

    async def create_project_integration(
        self, project_id: UUID, data: ProjectIntegrationCreate
    ) -> ProjectIntegrationRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        account = await self._account(data.integration_account_id)
        expected = {
            ProjectIntegrationKind.GOOGLE_CALENDAR: IntegrationProvider.GOOGLE,
            ProjectIntegrationKind.GMAIL: IntegrationProvider.GOOGLE,
            ProjectIntegrationKind.GITHUB_REPOSITORY: IntegrationProvider.GITHUB,
        }[data.kind]
        if account.provider != expected:
            raise AppError(
                code="integration_provider_mismatch",
                message="The selected account does not support this project integration.",
                status_code=422,
            )
        resource_id = data.external_resource_id
        display_name = data.display_name
        if data.kind == ProjectIntegrationKind.GOOGLE_CALENDAR:
            calendars = await self._provider_call(account, self.google.calendars)
            selected = next((value for value in calendars if value.id == resource_id), None)
            if selected is None:
                raise AppError(
                    code="integration_resource_not_found",
                    message="The selected external resource is unavailable.",
                    status_code=404,
                )
            display_name = selected.name
        elif data.kind == ProjectIntegrationKind.GMAIL:
            if resource_id != "me":
                raise AppError(
                    code="integration_resource_not_found",
                    message="The selected external resource is unavailable.",
                    status_code=404,
                )
            display_name = f"Gmail · {account.display_name}"
        else:
            repositories = await self._provider_call(account, self.github.repositories)
            selected = next(
                (value for value in repositories if value.full_name == resource_id), None
            )
            if selected is None:
                raise AppError(
                    code="integration_resource_not_found",
                    message="The selected external resource is unavailable.",
                    status_code=404,
                )
            display_name = selected.full_name
        existing = await self.session.scalar(
            select(ProjectIntegration).where(
                ProjectIntegration.project_id == project_id,
                ProjectIntegration.kind == data.kind,
                ProjectIntegration.external_resource_id == resource_id,
            )
        )
        if existing:
            return ProjectIntegrationRead.model_validate(existing)
        item = ProjectIntegration(
            project_id=project_id,
            integration_account_id=account.id,
            created_by_user_id=self.user_id,
            kind=data.kind,
            external_resource_id=resource_id,
            display_name=display_name,
        )
        self.session.add(item)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="integration.project_connected",
            entity_type="project_integration",
            entity_id=item.id,
            changes={"kind": item.kind.value},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return ProjectIntegrationRead.model_validate(item)

    async def project_integrations(self, project_id: UUID) -> list[ProjectIntegrationRead]:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_READ)
        items = list(
            (
                await self.session.scalars(
                    select(ProjectIntegration)
                    .where(ProjectIntegration.project_id == project_id)
                    .order_by(ProjectIntegration.kind, ProjectIntegration.display_name)
                )
            ).all()
        )
        return [ProjectIntegrationRead.model_validate(item) for item in items]

    async def delete_project_integration(self, project_id: UUID, integration_id: UUID) -> None:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        item = await self._project_integration(project_id, integration_id, require_owner=False)
        self.audit.record(
            project_id=project_id,
            action="integration.project_disconnected",
            entity_type="project_integration",
            entity_id=item.id,
            changes={"kind": item.kind.value},
        )
        await self.session.delete(item)
        await self.session.commit()

    async def calendars(self, account_id: UUID):
        account = await self._account(account_id, IntegrationProvider.GOOGLE)
        return await self._provider_call(account, self.google.calendars)

    async def calendar_events(
        self, project_id: UUID, integration_id: UUID, time_min: datetime, time_max: datetime
    ):
        await self.authorization.require(project_id, Capability.INTEGRATIONS_SYNC)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GOOGLE_CALENDAR
        )
        account = await self._account(item.integration_account_id, IntegrationProvider.GOOGLE)
        return await self._provider_call(
            account,
            self.google.events,
            item.external_resource_id,
            time_min=time_min,
            time_max=time_max,
        )

    async def preview_calendar_meeting(
        self, project_id: UUID, integration_id: UUID, event_id: str
    ) -> CalendarMeetingPreviewRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_SYNC)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GOOGLE_CALENDAR
        )
        account = await self._account(item.integration_account_id, IntegrationProvider.GOOGLE)
        event = await self._provider_call(
            account, self.google.event, item.external_resource_id, event_id
        )
        expires_at = datetime.now(UTC) + timedelta(minutes=CALENDAR_CONFIRM_MINUTES)
        fingerprint = self._event_fingerprint(event)
        confirmation = jwt.encode(
            {
                "typ": "calendar_meeting_preview",
                "sub": str(self.user_id),
                "project_id": str(project_id),
                "integration_id": str(integration_id),
                "event_id": event.id,
                "fingerprint": fingerprint,
                "exp": expires_at,
            },
            self.settings.secret_key,
            algorithm="HS256",
        )
        return CalendarMeetingPreviewRead(
            event=CalendarEventRead(**{**event.__dict__, "attendees": list(event.attendees)}),
            confirmation_token=confirmation,
            expires_at=expires_at,
        )

    async def link_calendar_event(
        self, project_id: UUID, integration_id: UUID, event_id: str
    ) -> ExternalLinkRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GOOGLE_CALENDAR
        )
        account = await self._account(item.integration_account_id, IntegrationProvider.GOOGLE)
        event = await self._provider_call(
            account, self.google.event, item.external_resource_id, event_id
        )
        link = await self._upsert_link(
            item,
            object_type=ExternalObjectType.CALENDAR_EVENT,
            external_id=event.id,
            url=event.url,
            title=event.title,
            summary=event.description,
            metadata={
                "starts_at": event.starts_at.isoformat(),
                "ends_at": event.ends_at.isoformat() if event.ends_at else None,
                "location": event.location,
                "attendee_count": len(event.attendees),
            },
            visibility=ExternalLinkVisibility.PROJECT,
            target_entity_type="PROJECT",
            target_entity_id=project_id,
            relationship_type="REFERENCE",
        )
        return ExternalLinkRead.model_validate(link)

    async def confirm_calendar_meeting(
        self, project_id: UUID, integration_id: UUID, confirmation_token: str
    ) -> ImportedMeetingRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        try:
            payload = jwt.decode(confirmation_token, self.settings.secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise AppError(
                code="invalid_preview",
                message="The meeting preview is invalid or expired.",
                status_code=409,
            ) from exc
        expected = (str(self.user_id), str(project_id), str(integration_id))
        actual = (payload.get("sub"), payload.get("project_id"), payload.get("integration_id"))
        if payload.get("typ") != "calendar_meeting_preview" or actual != expected:
            raise AppError(
                code="invalid_preview",
                message="The meeting preview is invalid or expired.",
                status_code=409,
            )
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GOOGLE_CALENDAR
        )
        existing = await self.session.scalar(
            select(ExternalLink).where(
                ExternalLink.project_integration_id == item.id,
                ExternalLink.object_type == ExternalObjectType.CALENDAR_EVENT,
                ExternalLink.external_id == payload.get("event_id"),
                ExternalLink.target_entity_type == "MEETING",
            )
        )
        if existing and existing.target_entity_id:
            return ImportedMeetingRead(
                meeting_id=existing.target_entity_id,
                external_link_id=existing.id,
                already_imported=True,
            )
        account = await self._account(item.integration_account_id, IntegrationProvider.GOOGLE)
        event = await self._provider_call(
            account, self.google.event, item.external_resource_id, str(payload.get("event_id", ""))
        )
        if not secrets.compare_digest(
            str(payload.get("fingerprint", "")), self._event_fingerprint(event)
        ):
            raise AppError(
                code="stale_preview",
                message="The calendar event changed. Preview it again.",
                status_code=409,
            )
        duration = None
        if event.ends_at:
            duration = max(
                1, min(1440, int((event.ends_at - event.starts_at).total_seconds() // 60))
            )
        location_note = f" · {event.location}" if event.location else ""
        meeting = await MemoryService(self.session, self.user_id).create_meeting(
            project_id,
            MeetingCreate(
                title=event.title,
                scheduled_at=event.starts_at,
                duration_minutes=duration,
                agenda=event.description,
                notes=f"Imported from Google Calendar{location_note}",
                participant_ids=[],
            ),
        )
        link = ExternalLink(
            project_id=project_id,
            project_integration_id=item.id,
            created_by_user_id=self.user_id,
            object_type=ExternalObjectType.CALENDAR_EVENT,
            external_id=event.id,
            external_url=event.url,
            title=event.title,
            summary=self._safe_text(event.description),
            safe_metadata={
                "starts_at": event.starts_at.isoformat(),
                "ends_at": event.ends_at.isoformat() if event.ends_at else None,
                "location": self._safe_text(event.location, 500),
                "attendee_count": len(event.attendees),
            },
            visibility=ExternalLinkVisibility.PROJECT,
            target_entity_type="MEETING",
            target_entity_id=meeting.id,
            relationship_type="IMPORTED_FROM",
            last_checked_at=datetime.now(UTC),
        )
        self.session.add(link)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="integration.calendar_event_imported",
            entity_type="external_link",
            entity_id=link.id,
            changes={"meeting_id": str(meeting.id)},
        )
        MemoryService.record_system_log(
            self.session,
            actor_user_id=self.user_id,
            project_id=project_id,
            entry_type=ProjectLogType.MEETING,
            title=f"Meeting imported from calendar: {event.title}",
            description="Created after explicit calendar-event preview and confirmation.",
            entity_type=MemoryEntityType.MEETING,
            entity_id=meeting.id,
        )
        await self.session.commit()
        await self.session.refresh(link)
        return ImportedMeetingRead(
            meeting_id=meeting.id, external_link_id=link.id, already_imported=False
        )

    async def search_email(self, project_id: UUID, integration_id: UUID, query: str):
        await self.authorization.require(project_id, Capability.INTEGRATIONS_SYNC)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GMAIL
        )
        account = await self._account(item.integration_account_id, IntegrationProvider.GOOGLE)
        return await self._provider_call(account, self.google.search_email, query, limit=10)

    async def link_email(
        self, project_id: UUID, integration_id: UUID, data: EmailLinkCreate
    ) -> ExternalLinkRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GMAIL
        )
        account = await self._account(item.integration_account_id, IntegrationProvider.GOOGLE)
        await self._validate_target(project_id, data.target_entity_type, data.target_entity_id)
        email = await self._provider_call(account, self.google.email, data.message_id)
        link = await self._upsert_link(
            item,
            object_type=ExternalObjectType.EMAIL_MESSAGE,
            external_id=email.id,
            url=email.url,
            title=email.subject,
            summary=email.snippet,
            metadata={
                "sender": self._safe_text(email.sender, 500),
                "sent_at": email.sent_at,
                "thread_id": email.thread_id,
            },
            visibility=data.visibility,
            target_entity_type=data.target_entity_type,
            target_entity_id=project_id
            if data.target_entity_type == "PROJECT"
            else data.target_entity_id,
            relationship_type="REFERENCE",
        )
        return ExternalLinkRead.model_validate(link)

    async def repositories(self, account_id: UUID):
        account = await self._account(account_id, IntegrationProvider.GITHUB)
        return await self._provider_call(account, self.github.repositories)

    async def github_objects(self, project_id: UUID, integration_id: UUID, collection: str):
        await self.authorization.require(project_id, Capability.INTEGRATIONS_SYNC)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GITHUB_REPOSITORY
        )
        account = await self._account(item.integration_account_id, IntegrationProvider.GITHUB)
        operation = {
            "issues": self.github.issues,
            "pull-requests": self.github.pull_requests,
            "commits": self.github.commits,
        }.get(collection)
        if operation is None:
            raise AppError(
                code="integration_object_not_found",
                message="External object not found.",
                status_code=404,
            )
        return await self._provider_call(account, operation, item.external_resource_id)

    async def link_github_task(
        self, project_id: UUID, integration_id: UUID, data: GitHubTaskLinkCreate
    ) -> ExternalLinkRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        item = await self._project_integration(
            project_id, integration_id, kind=ProjectIntegrationKind.GITHUB_REPOSITORY
        )
        await self._validate_target(project_id, "TASK", data.task_id)
        account = await self._account(item.integration_account_id, IntegrationProvider.GITHUB)
        source = await self._provider_call(
            account,
            self.github.source_object,
            item.external_resource_id,
            data.object_type,
            data.external_id,
        )
        link = await self._upsert_link(
            item,
            object_type=ExternalObjectType(data.object_type),
            external_id=source.id,
            url=source.url,
            title=source.title,
            summary=source.summary,
            metadata={"state": source.state, "number": source.number, **source.metadata},
            visibility=ExternalLinkVisibility.PROJECT,
            target_entity_type="TASK",
            target_entity_id=data.task_id,
            relationship_type=data.relationship_type,
        )
        MemoryService.record_system_log(
            self.session,
            actor_user_id=self.user_id,
            project_id=project_id,
            entry_type=ProjectLogType.TASK_UPDATE,
            title=f"External GitHub reference linked: {source.title}",
            description=f"Relationship: {data.relationship_type}",
            entity_type=MemoryEntityType.TASK,
            entity_id=data.task_id,
        )
        await self.session.commit()
        return ExternalLinkRead.model_validate(link)

    async def external_links(self, project_id: UUID) -> list[ExternalLinkRead]:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_READ)
        can_finance = await self.authorization.can(project_id, Capability.FINANCE_READ)
        visibility = [
            ExternalLink.visibility == ExternalLinkVisibility.PROJECT,
            ExternalLink.created_by_user_id == self.user_id,
        ]
        if can_finance:
            visibility.append(ExternalLink.visibility == ExternalLinkVisibility.FINANCE)
        items = list(
            (
                await self.session.scalars(
                    select(ExternalLink)
                    .where(ExternalLink.project_id == project_id, or_(*visibility))
                    .order_by(ExternalLink.created_at.desc())
                )
            ).all()
        )
        return [ExternalLinkRead.model_validate(item) for item in items]

    async def refresh_project_integration(
        self, project_id: UUID, integration_id: UUID
    ) -> ProjectIntegrationRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_SYNC)
        item = await self._project_integration(project_id, integration_id)
        account = await self._account(item.integration_account_id)
        if item.kind == ProjectIntegrationKind.GOOGLE_CALENDAR:
            values = await self._provider_call(account, self.google.calendars)
            exists = any(value.id == item.external_resource_id for value in values)
        elif item.kind == ProjectIntegrationKind.GITHUB_REPOSITORY:
            values = await self._provider_call(account, self.github.repositories)
            exists = any(value.full_name == item.external_resource_id for value in values)
        else:
            await self._provider_call(account, self.google.identity)
            exists = True
        item.status = (
            ProjectIntegrationStatus.ACTIVE if exists else ProjectIntegrationStatus.UNAVAILABLE
        )
        item.last_synced_at = datetime.now(UTC)
        self.audit.record(
            project_id=project_id,
            action="integration.project_refreshed",
            entity_type="project_integration",
            entity_id=item.id,
            changes={"status": item.status.value},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return ProjectIntegrationRead.model_validate(item)

    async def refresh_external_link(self, project_id: UUID, link_id: UUID) -> ExternalLinkRead:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_SYNC)
        link = await self.session.scalar(
            select(ExternalLink).where(
                ExternalLink.id == link_id,
                ExternalLink.project_id == project_id,
            )
        )
        if link is None:
            raise AppError(
                code="external_link_not_found", message="External link not found.", status_code=404
            )
        item = await self._project_integration(project_id, link.project_integration_id)
        account = await self._account(item.integration_account_id)
        try:
            if link.object_type == ExternalObjectType.CALENDAR_EVENT:
                value = await self._provider_call(
                    account,
                    self.google.event,
                    item.external_resource_id,
                    link.external_id,
                )
                title, summary, url = value.title, value.description, value.url
                metadata = {
                    "starts_at": value.starts_at.isoformat(),
                    "ends_at": value.ends_at.isoformat() if value.ends_at else None,
                    "location": value.location,
                    "attendee_count": len(value.attendees),
                }
            elif link.object_type == ExternalObjectType.EMAIL_MESSAGE:
                value = await self._provider_call(account, self.google.email, link.external_id)
                title, summary, url = value.subject, value.snippet, value.url
                metadata = {
                    "sender": value.sender,
                    "sent_at": value.sent_at,
                    "thread_id": value.thread_id,
                }
            else:
                value = await self._provider_call(
                    account,
                    self.github.source_object,
                    item.external_resource_id,
                    link.object_type.value,
                    link.external_id,
                )
                title, summary, url = value.title, value.summary, value.url
                metadata = {
                    "state": value.state,
                    "number": value.number,
                    **value.metadata,
                }
        except AppError as exc:
            if exc.code != "integration_object_not_found":
                raise
            link.available = False
            link.last_checked_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(link)
            return ExternalLinkRead.model_validate(link)
        link.title = title[:500]
        link.summary = self._safe_text(summary)
        link.external_url = url[:2000]
        link.safe_metadata = self._safe_metadata(metadata)
        link.available = True
        link.last_checked_at = datetime.now(UTC)
        self.audit.record(
            project_id=project_id,
            action="integration.external_link_refreshed",
            entity_type="external_link",
            entity_id=link.id,
            changes={"available": True},
        )
        await self.session.commit()
        await self.session.refresh(link)
        return ExternalLinkRead.model_validate(link)

    async def delete_external_link(self, project_id: UUID, link_id: UUID) -> None:
        await self.authorization.require(project_id, Capability.INTEGRATIONS_MANAGE)
        link = await self.session.scalar(
            select(ExternalLink).where(
                ExternalLink.id == link_id,
                ExternalLink.project_id == project_id,
            )
        )
        if link is None:
            raise AppError(
                code="external_link_not_found", message="External link not found.", status_code=404
            )
        self.audit.record(
            project_id=project_id,
            action="integration.external_link_removed",
            entity_type="external_link",
            entity_id=link.id,
            changes={"object_type": link.object_type.value},
        )
        await self.session.delete(link)
        await self.session.commit()

    async def _upsert_link(
        self,
        item: ProjectIntegration,
        *,
        object_type: ExternalObjectType,
        external_id: str,
        url: str,
        title: str,
        summary: str | None,
        metadata: dict,
        visibility: ExternalLinkVisibility,
        target_entity_type: str | None,
        target_entity_id: UUID | None,
        relationship_type: str | None,
    ) -> ExternalLink:
        link = await self.session.scalar(
            select(ExternalLink).where(
                ExternalLink.project_integration_id == item.id,
                ExternalLink.object_type == object_type,
                ExternalLink.external_id == external_id,
                ExternalLink.target_entity_type == target_entity_type,
                ExternalLink.target_entity_id == target_entity_id,
            )
        )
        if link is None:
            link = ExternalLink(
                project_id=item.project_id,
                project_integration_id=item.id,
                created_by_user_id=self.user_id,
                object_type=object_type,
                external_id=external_id,
                external_url=url[:2000],
                title=title[:500],
                summary=self._safe_text(summary),
                safe_metadata=self._safe_metadata(metadata),
                visibility=visibility,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                last_checked_at=datetime.now(UTC),
            )
            self.session.add(link)
            await self.session.flush()
            self.audit.record(
                project_id=item.project_id,
                action="integration.external_link_created",
                entity_type="external_link",
                entity_id=link.id,
                changes={"object_type": object_type.value, "visibility": visibility.value},
            )
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def _provider_call(self, account: IntegrationAccount, operation, *args, **kwargs):
        token = await self._access_token(account)
        try:
            result = await operation(token, *args, **kwargs)
        except ProviderError as exc:
            if exc.kind == ProviderFailureKind.AUTHENTICATION:
                account.status = IntegrationAccountStatus.REAUTH_REQUIRED
                await self.session.commit()
            raise self._app_error(exc) from exc
        account.last_used_at = datetime.now(UTC)
        account.last_sync_at = account.last_used_at
        if account.status != IntegrationAccountStatus.CONNECTED:
            account.status = IntegrationAccountStatus.CONNECTED
        await self.session.commit()
        return result

    async def _access_token(self, account: IntegrationAccount) -> str:
        if (
            account.status != IntegrationAccountStatus.CONNECTED
            or not account.encrypted_access_token
        ):
            raise AppError(
                code="integration_reauthentication_required",
                message="The integration must be connected again.",
                status_code=401,
            )
        expires = self._as_utc(account.token_expires_at) if account.token_expires_at else None
        if expires and expires <= datetime.now(UTC) + timedelta(seconds=30):
            if not account.encrypted_refresh_token:
                account.status = IntegrationAccountStatus.REAUTH_REQUIRED
                await self.session.commit()
                raise AppError(
                    code="integration_reauthentication_required",
                    message="The integration must be connected again.",
                    status_code=401,
                )
            adapter, _ = self._oauth_adapter(account.provider)
            try:
                token = await adapter.refresh(self.cipher.decrypt(account.encrypted_refresh_token))
            except ProviderError as exc:
                account.status = IntegrationAccountStatus.REAUTH_REQUIRED
                await self.session.commit()
                raise self._app_error(exc) from exc
            account.encrypted_access_token = self.cipher.encrypt(token.access_token)
            if token.refresh_token:
                account.encrypted_refresh_token = self.cipher.encrypt(token.refresh_token)
            account.token_expires_at = token.expires_at
            account.scopes = list(token.scopes) or account.scopes
            await self.session.commit()
            return token.access_token
        return self.cipher.decrypt(account.encrypted_access_token)

    async def _account(
        self, account_id: UUID, provider: IntegrationProvider | None = None
    ) -> IntegrationAccount:
        account = await self.session.scalar(
            select(IntegrationAccount).where(
                IntegrationAccount.id == account_id,
                IntegrationAccount.user_id == self.user_id,
            )
        )
        if account is None or (provider and account.provider != provider):
            raise AppError(
                code="integration_account_not_found",
                message="Integration account not found.",
                status_code=404,
            )
        return account

    async def _project_integration(
        self,
        project_id: UUID,
        integration_id: UUID,
        *,
        kind: ProjectIntegrationKind | None = None,
        require_owner: bool = True,
    ) -> ProjectIntegration:
        item = await self.session.scalar(
            select(ProjectIntegration).where(
                ProjectIntegration.id == integration_id,
                ProjectIntegration.project_id == project_id,
            )
        )
        if item is None or (kind and item.kind != kind):
            raise AppError(
                code="project_integration_not_found",
                message="Project integration not found.",
                status_code=404,
            )
        if require_owner and item.created_by_user_id != self.user_id:
            raise AppError(
                code="integration_account_not_found",
                message="Integration account not found.",
                status_code=404,
            )
        return item

    async def _validate_target(
        self, project_id: UUID, target_type: str, target_id: UUID | None
    ) -> None:
        if target_type == "PROJECT":
            return
        model = {"TASK": Task, "ISSUE": Issue}.get(target_type)
        if target_type == "MEETING":
            from app.models.memory import Meeting

            model = Meeting
        if model is None or target_id is None:
            raise AppError(
                code="external_link_target_not_found",
                message="Link target not found.",
                status_code=404,
            )
        if (
            await self.session.scalar(
                select(model.id).where(model.id == target_id, model.project_id == project_id)
            )
            is None
        ):
            raise AppError(
                code="external_link_target_not_found",
                message="Link target not found.",
                status_code=404,
            )

    def _oauth_adapter(self, provider: IntegrationProvider):
        if provider == IntegrationProvider.GOOGLE:
            return self.google, self.settings.google_oauth_redirect_uri
        return self.github, self.settings.github_oauth_redirect_uri

    @staticmethod
    def _app_error(error: ProviderError) -> AppError:
        mapping = {
            ProviderFailureKind.AUTHENTICATION: ("integration_reauthentication_required", 401),
            ProviderFailureKind.PERMISSION: ("integration_permission_denied", 403),
            ProviderFailureKind.RATE_LIMIT: ("integration_rate_limited", 429),
            ProviderFailureKind.NOT_FOUND: ("integration_object_not_found", 404),
            ProviderFailureKind.UNAVAILABLE: ("integration_provider_unavailable", 503),
            ProviderFailureKind.INVALID_RESPONSE: ("integration_invalid_response", 502),
        }
        code, status = mapping[error.kind]
        return AppError(
            code=code,
            message="The external provider request could not be completed.",
            status_code=status,
        )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _safe_text(value: str | None, limit: int = EXTERNAL_TEXT_LIMIT) -> str | None:
        if not value:
            return None
        return " ".join(value.split())[:limit]

    @classmethod
    def _safe_metadata(cls, value: dict) -> dict:
        result = {}
        for key, item in list(value.items())[:20]:
            if isinstance(item, str):
                result[str(key)[:100]] = cls._safe_text(item, 500)
            elif isinstance(item, (bool, int, float)) or item is None:
                result[str(key)[:100]] = item
            elif isinstance(item, list):
                result[str(key)[:100]] = [cls._safe_text(str(entry), 100) for entry in item[:20]]
        return result

    @classmethod
    def _event_fingerprint(cls, event) -> str:
        payload = {
            "id": event.id,
            "title": event.title,
            "starts_at": event.starts_at.isoformat(),
            "ends_at": event.ends_at.isoformat() if event.ends_at else None,
            "description": event.description,
            "location": event.location,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
