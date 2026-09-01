from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from urllib.parse import quote, urlencode

import httpx

from app.core.config import Settings
from app.integrations.provider import (
    CalendarEventInfo,
    CalendarInfo,
    EmailInfo,
    OAuthToken,
    ProviderError,
    ProviderFailureKind,
    ProviderIdentity,
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_API = "https://www.googleapis.com"
GMAIL_API = "https://gmail.googleapis.com"


class GoogleAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client
        self.configured = bool(
            settings.google_oauth_client_id
            and settings.google_oauth_client_secret
            and settings.integration_token_encryption_key
        )

    def authorization_url(self, *, state: str, code_challenge: str, redirect_uri: str) -> str:
        if not self.configured:
            raise ProviderError(ProviderFailureKind.UNAVAILABLE, "Google is not configured.")
        params = {
            "client_id": self.settings.google_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.settings.google_oauth_scopes,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> OAuthToken:
        data = await self._request(
            "POST",
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self.settings.google_oauth_client_id,
                "client_secret": self.settings.google_oauth_client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        return self._token(data)

    async def refresh(self, refresh_token: str) -> OAuthToken:
        data = await self._request(
            "POST",
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self.settings.google_oauth_client_id,
                "client_secret": self.settings.google_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        return self._token(data, refresh_token=refresh_token)

    async def identity(self, access_token: str) -> ProviderIdentity:
        data = await self._request("GET", f"{GOOGLE_API}/oauth2/v3/userinfo", token=access_token)
        account_id = data.get("sub")
        display_name = data.get("email") or data.get("name")
        if not isinstance(account_id, str) or not isinstance(display_name, str):
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid Google identity.")
        return ProviderIdentity(account_id=account_id, display_name=display_name[:255])

    async def revoke(self, access_token: str) -> None:
        await self._request(
            "POST", "https://oauth2.googleapis.com/revoke", data={"token": access_token}
        )

    async def calendars(self, access_token: str) -> list[CalendarInfo]:
        data = await self._request(
            "GET",
            f"{GOOGLE_API}/calendar/v3/users/me/calendarList",
            token=access_token,
            params={"maxResults": "100", "showDeleted": "false", "showHidden": "false"},
        )
        return [
            CalendarInfo(
                id=str(item["id"]),
                name=str(item.get("summaryOverride") or item.get("summary") or item["id"])[:500],
                primary=bool(item.get("primary")),
            )
            for item in self._items(data)
            if item.get("id")
        ]

    async def events(
        self, access_token: str, calendar_id: str, *, time_min: datetime, time_max: datetime
    ) -> list[CalendarEventInfo]:
        data = await self._request(
            "GET",
            f"{GOOGLE_API}/calendar/v3/calendars/{quote(calendar_id, safe='')}/events",
            token=access_token,
            params={
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
                "showDeleted": "false",
                "maxResults": "50",
            },
        )
        return [self._event(item) for item in self._items(data) if item.get("id")]

    async def event(self, access_token: str, calendar_id: str, event_id: str) -> CalendarEventInfo:
        data = await self._request(
            "GET",
            f"{GOOGLE_API}/calendar/v3/calendars/{quote(calendar_id, safe='')}"
            f"/events/{quote(event_id, safe='')}",
            token=access_token,
        )
        return self._event(data)

    async def search_email(self, access_token: str, query: str, *, limit: int) -> list[EmailInfo]:
        listing = await self._request(
            "GET",
            f"{GMAIL_API}/gmail/v1/users/me/messages",
            token=access_token,
            params={"q": query, "maxResults": str(min(limit, 10))},
        )
        results = []
        for item in self._items(listing)[: min(limit, 10)]:
            if item.get("id"):
                results.append(await self.email(access_token, str(item["id"])))
        return results

    async def email(self, access_token: str, message_id: str) -> EmailInfo:
        data = await self._request(
            "GET",
            f"{GMAIL_API}/gmail/v1/users/me/messages/{quote(message_id, safe='')}",
            token=access_token,
            params=[
                ("format", "metadata"),
                ("metadataHeaders", "Subject"),
                ("metadataHeaders", "From"),
                ("metadataHeaders", "Date"),
            ],
        )
        headers = {
            str(item.get("name", "")).lower(): str(item.get("value", ""))
            for item in data.get("payload", {}).get("headers", [])
            if isinstance(item, dict)
        }
        message_id_value = str(data.get("id") or message_id)
        return EmailInfo(
            id=message_id_value,
            thread_id=str(data["threadId"]) if data.get("threadId") else None,
            subject=(headers.get("subject") or "(no subject)")[:500],
            sender=headers.get("from", "")[:500] or None,
            sent_at=headers.get("date", "")[:200] or None,
            snippet=str(data.get("snippet", ""))[:500] or None,
            url=f"https://mail.google.com/mail/u/0/#all/{quote(message_id_value, safe='')}",
        )

    def _event(self, data: dict) -> CalendarEventInfo:
        starts_at = self._event_datetime(data.get("start", {}))
        ends_at = self._event_datetime(data.get("end", {}), required=False)
        event_id = str(data.get("id", ""))
        if not event_id or starts_at is None:
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid calendar event.")
        attendees = tuple(
            str(item.get("email"))[:320]
            for item in data.get("attendees", [])[:100]
            if isinstance(item, dict) and item.get("email")
        )
        updated = data.get("updated")
        return CalendarEventInfo(
            id=event_id,
            title=str(data.get("summary") or "Untitled event")[:500],
            starts_at=starts_at,
            ends_at=ends_at,
            description=str(data.get("description", ""))[:5000] or None,
            location=str(data.get("location", ""))[:500] or None,
            attendees=attendees,
            url=str(data.get("htmlLink") or "")[:2000],
            updated_at=datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if isinstance(updated, str)
            else None,
        )

    @staticmethod
    def _event_datetime(value: dict, required: bool = True) -> datetime | None:
        raw = value.get("dateTime")
        if isinstance(raw, str):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        raw_date = value.get("date")
        if isinstance(raw_date, str):
            parsed = date.fromisoformat(raw_date)
            return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)
        if required:
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Event start is missing.")
        return None

    @staticmethod
    def _items(data: dict) -> list[dict]:
        items = data.get("items")
        if items is None:
            items = data.get("messages", [])
        if not isinstance(items, list):
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid provider list.")
        return [item for item in items if isinstance(item, dict)]

    def _token(self, data: dict, refresh_token: str | None = None) -> OAuthToken:
        access = data.get("access_token")
        if not isinstance(access, str):
            raise ProviderError(ProviderFailureKind.AUTHENTICATION, "Token exchange failed.")
        expires = data.get("expires_in")
        scope = data.get("scope", self.settings.google_oauth_scopes)
        return OAuthToken(
            access_token=access,
            refresh_token=data.get("refresh_token") or refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=int(expires))
            if expires is not None
            else None,
            scopes=tuple(str(scope).replace(",", " ").split()),
        )

    async def _request(self, method: str, url: str, *, token: str | None = None, **kwargs) -> dict:
        headers = dict(kwargs.pop("headers", {}))
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            if self.client:
                response = await self.client.request(method, url, headers=headers, **kwargs)
            else:
                async with httpx.AsyncClient(
                    timeout=self.settings.integration_timeout_seconds
                ) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                ProviderFailureKind.UNAVAILABLE, "Provider request timed out."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                ProviderFailureKind.UNAVAILABLE, "Provider is unavailable."
            ) from exc
        if response.status_code >= 400:
            raise self._http_error(response.status_code)
        if response.status_code == 204 or not response.content:
            return {}
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(
                ProviderFailureKind.INVALID_RESPONSE, "Invalid provider response."
            ) from exc
        if not isinstance(data, dict):
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid provider response.")
        return data

    @staticmethod
    def _http_error(status: int) -> ProviderError:
        if status == 401:
            kind = ProviderFailureKind.AUTHENTICATION
        elif status == 403:
            kind = ProviderFailureKind.PERMISSION
        elif status == 404:
            kind = ProviderFailureKind.NOT_FOUND
        elif status == 429:
            kind = ProviderFailureKind.RATE_LIMIT
        else:
            kind = ProviderFailureKind.UNAVAILABLE
        return ProviderError(kind, "Google request failed.")
