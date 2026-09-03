from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class ProviderFailureKind(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    RATE_LIMIT = "RATE_LIMIT"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class ProviderError(Exception):
    def __init__(self, kind: ProviderFailureKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class ProviderIdentity:
    account_id: str
    display_name: str


@dataclass(frozen=True)
class CalendarInfo:
    id: str
    name: str
    primary: bool = False


@dataclass(frozen=True)
class CalendarEventInfo:
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None
    description: str | None
    location: str | None
    attendees: tuple[str, ...]
    url: str
    updated_at: datetime | None


@dataclass(frozen=True)
class EmailInfo:
    id: str
    thread_id: str | None
    subject: str
    sender: str | None
    sent_at: str | None
    snippet: str | None
    url: str


@dataclass(frozen=True)
class RepositoryInfo:
    id: str
    full_name: str
    private: bool
    url: str
    default_branch: str | None


@dataclass(frozen=True)
class SourceObjectInfo:
    id: str
    number: int | None
    title: str
    state: str | None
    url: str
    summary: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class OAuthProvider(Protocol):
    configured: bool

    def authorization_url(self, *, state: str, code_challenge: str, redirect_uri: str) -> str: ...
    async def exchange_code(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> OAuthToken: ...
    async def refresh(self, refresh_token: str) -> OAuthToken: ...
    async def identity(self, access_token: str) -> ProviderIdentity: ...
    async def revoke(self, access_token: str) -> None: ...


class CalendarProvider(Protocol):
    async def calendars(self, access_token: str) -> list[CalendarInfo]: ...
    async def events(
        self, access_token: str, calendar_id: str, *, time_min: datetime, time_max: datetime
    ) -> list[CalendarEventInfo]: ...
    async def event(
        self, access_token: str, calendar_id: str, event_id: str
    ) -> CalendarEventInfo: ...


class EmailProvider(Protocol):
    async def search_email(
        self, access_token: str, query: str, *, limit: int
    ) -> list[EmailInfo]: ...
    async def email(self, access_token: str, message_id: str) -> EmailInfo: ...


class SourceControlProvider(Protocol):
    async def repositories(self, access_token: str) -> list[RepositoryInfo]: ...
    async def issues(self, access_token: str, repository: str) -> list[SourceObjectInfo]: ...
    async def pull_requests(self, access_token: str, repository: str) -> list[SourceObjectInfo]: ...
    async def commits(self, access_token: str, repository: str) -> list[SourceObjectInfo]: ...
    async def source_object(
        self, access_token: str, repository: str, object_type: str, external_id: str
    ) -> SourceObjectInfo: ...
