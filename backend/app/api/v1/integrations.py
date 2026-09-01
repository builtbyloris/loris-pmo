from datetime import datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models.integrations import IntegrationProvider
from app.schemas.integrations import (
    CalendarEventQuery,
    CalendarEventRead,
    CalendarMeetingConfirmRequest,
    CalendarMeetingPreviewRead,
    CalendarMeetingPreviewRequest,
    CalendarRead,
    EmailLinkCreate,
    EmailSearchRead,
    ExternalLinkRead,
    GitHubTaskLinkCreate,
    ImportedMeetingRead,
    IntegrationAccountRead,
    IntegrationsStatusRead,
    OAuthStartRead,
    OAuthStartRequest,
    ProjectIntegrationCreate,
    ProjectIntegrationRead,
    RepositoryRead,
    SourceObjectRead,
)
from app.services.integrations import IntegrationService

router = APIRouter(tags=["integrations"])
Session = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
csrf = [Depends(require_csrf)]


def _provider(value: str) -> IntegrationProvider:
    try:
        return IntegrationProvider(value.upper())
    except ValueError as exc:
        raise AppError(
            code="integration_provider_not_found",
            message="Integration provider not found.",
            status_code=404,
        ) from exc


def _service(session: AsyncSession, user, settings: Settings) -> IntegrationService:
    return IntegrationService(session, user.id, settings)


@router.get("/integrations/status", response_model=IntegrationsStatusRead)
async def integration_status(user: CurrentUser, session: Session, settings: AppSettings):
    service = _service(session, user, settings)
    return IntegrationsStatusRead(
        encryption_configured=service.cipher.available,
        providers=service.provider_statuses(),
    )


@router.get("/integrations/accounts", response_model=list[IntegrationAccountRead])
async def accounts(user: CurrentUser, session: Session, settings: AppSettings):
    return await _service(session, user, settings).accounts()


@router.post(
    "/integrations/oauth/{provider}/start", response_model=OAuthStartRead, dependencies=csrf
)
async def start_oauth(
    provider: str,
    data: OAuthStartRequest,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).start_oauth(
        _provider(provider), data.return_path
    )


@router.get("/integrations/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    state: Annotated[str, Query(min_length=20, max_length=500)],
    code: Annotated[str, Query(min_length=1, max_length=2000)],
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    _account, return_path = await _service(session, user, settings).complete_oauth(
        _provider(provider), state, code
    )
    separator = "&" if "?" in return_path else "?"
    destination = (
        f"{settings.frontend_url.rstrip('/')}{return_path}{separator}"
        f"integration={quote(provider.lower())}&status=connected"
    )
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)


@router.delete(
    "/integrations/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=csrf,
)
async def disconnect_account(
    account_id: UUID, user: CurrentUser, session: Session, settings: AppSettings
):
    await _service(session, user, settings).disconnect_account(account_id)


@router.get("/integrations/accounts/{account_id}/calendars", response_model=list[CalendarRead])
async def calendars(account_id: UUID, user: CurrentUser, session: Session, settings: AppSettings):
    values = await _service(session, user, settings).calendars(account_id)
    return [CalendarRead(**value.__dict__) for value in values]


@router.get(
    "/integrations/accounts/{account_id}/github/repositories",
    response_model=list[RepositoryRead],
)
async def repositories(
    account_id: UUID, user: CurrentUser, session: Session, settings: AppSettings
):
    values = await _service(session, user, settings).repositories(account_id)
    return [RepositoryRead(**value.__dict__) for value in values]


@router.get("/projects/{project_id}/integrations", response_model=list[ProjectIntegrationRead])
async def project_integrations(
    project_id: UUID, user: CurrentUser, session: Session, settings: AppSettings
):
    return await _service(session, user, settings).project_integrations(project_id)


@router.post(
    "/projects/{project_id}/integrations",
    response_model=ProjectIntegrationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=csrf,
)
async def connect_project_integration(
    project_id: UUID,
    data: ProjectIntegrationCreate,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).create_project_integration(project_id, data)


@router.delete(
    "/projects/{project_id}/integrations/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=csrf,
)
async def disconnect_project_integration(
    project_id: UUID,
    integration_id: UUID,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    await _service(session, user, settings).delete_project_integration(project_id, integration_id)


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/refresh",
    response_model=ProjectIntegrationRead,
    dependencies=csrf,
)
async def refresh_project_integration(
    project_id: UUID,
    integration_id: UUID,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).refresh_project_integration(
        project_id, integration_id
    )


@router.get(
    "/projects/{project_id}/integrations/{integration_id}/calendar/events",
    response_model=list[CalendarEventRead],
)
async def calendar_events(
    project_id: UUID,
    integration_id: UUID,
    time_min: datetime,
    time_max: datetime,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    query = CalendarEventQuery(time_min=time_min, time_max=time_max)
    values = await _service(session, user, settings).calendar_events(
        project_id, integration_id, query.time_min, query.time_max
    )
    return [
        CalendarEventRead(**{**value.__dict__, "attendees": list(value.attendees)})
        for value in values
    ]


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/calendar/meeting-preview",
    response_model=CalendarMeetingPreviewRead,
    dependencies=csrf,
)
async def preview_calendar_meeting(
    project_id: UUID,
    integration_id: UUID,
    data: CalendarMeetingPreviewRequest,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).preview_calendar_meeting(
        project_id, integration_id, data.event_id
    )


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/calendar/import-meeting",
    response_model=ImportedMeetingRead,
    dependencies=csrf,
)
async def import_calendar_meeting(
    project_id: UUID,
    integration_id: UUID,
    data: CalendarMeetingConfirmRequest,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).confirm_calendar_meeting(
        project_id, integration_id, data.confirmation_token
    )


@router.get(
    "/projects/{project_id}/integrations/{integration_id}/gmail/search",
    response_model=list[EmailSearchRead],
)
async def search_email(
    project_id: UUID,
    integration_id: UUID,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    values = await _service(session, user, settings).search_email(project_id, integration_id, q)
    return [EmailSearchRead(**value.__dict__) for value in values]


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/gmail/links",
    response_model=ExternalLinkRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=csrf,
)
async def link_email(
    project_id: UUID,
    integration_id: UUID,
    data: EmailLinkCreate,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).link_email(project_id, integration_id, data)


@router.get(
    "/projects/{project_id}/integrations/{integration_id}/github/{collection}",
    response_model=list[SourceObjectRead],
)
async def github_objects(
    project_id: UUID,
    integration_id: UUID,
    collection: str,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    values = await _service(session, user, settings).github_objects(
        project_id, integration_id, collection
    )
    return [SourceObjectRead(**value.__dict__) for value in values]


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/github/task-links",
    response_model=ExternalLinkRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=csrf,
)
async def link_github_task(
    project_id: UUID,
    integration_id: UUID,
    data: GitHubTaskLinkCreate,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).link_github_task(
        project_id, integration_id, data
    )


@router.get("/projects/{project_id}/external-links", response_model=list[ExternalLinkRead])
async def external_links(
    project_id: UUID, user: CurrentUser, session: Session, settings: AppSettings
):
    return await _service(session, user, settings).external_links(project_id)


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/calendar/links",
    response_model=ExternalLinkRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=csrf,
)
async def link_calendar_event(
    project_id: UUID,
    integration_id: UUID,
    data: CalendarMeetingPreviewRequest,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).link_calendar_event(
        project_id, integration_id, data.event_id
    )


@router.post(
    "/projects/{project_id}/external-links/{link_id}/refresh",
    response_model=ExternalLinkRead,
    dependencies=csrf,
)
async def refresh_external_link(
    project_id: UUID,
    link_id: UUID,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    return await _service(session, user, settings).refresh_external_link(project_id, link_id)


@router.delete(
    "/projects/{project_id}/external-links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=csrf,
)
async def delete_external_link(
    project_id: UUID,
    link_id: UUID,
    user: CurrentUser,
    session: Session,
    settings: AppSettings,
):
    await _service(session, user, settings).delete_external_link(project_id, link_id)
