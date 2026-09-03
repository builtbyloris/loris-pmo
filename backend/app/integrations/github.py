from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

import httpx

from app.core.config import Settings
from app.integrations.provider import (
    OAuthToken,
    ProviderError,
    ProviderFailureKind,
    ProviderIdentity,
    RepositoryInfo,
    SourceObjectInfo,
)

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"


class GitHubAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client
        self.configured = bool(
            settings.github_oauth_client_id
            and settings.github_oauth_client_secret
            and settings.integration_token_encryption_key
        )

    def authorization_url(self, *, state: str, code_challenge: str, redirect_uri: str) -> str:
        if not self.configured:
            raise ProviderError(ProviderFailureKind.UNAVAILABLE, "GitHub is not configured.")
        params = {
            "client_id": self.settings.github_oauth_client_id,
            "redirect_uri": redirect_uri,
            "scope": self.settings.github_oauth_scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> OAuthToken:
        data = await self._request(
            "POST",
            GITHUB_TOKEN_URL,
            data={
                "client_id": self.settings.github_oauth_client_id,
                "client_secret": self.settings.github_oauth_client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
        )
        return self._token(data)

    async def refresh(self, refresh_token: str) -> OAuthToken:
        data = await self._request(
            "POST",
            GITHUB_TOKEN_URL,
            data={
                "client_id": self.settings.github_oauth_client_id,
                "client_secret": self.settings.github_oauth_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return self._token(data, refresh_token=refresh_token)

    async def identity(self, access_token: str) -> ProviderIdentity:
        data = await self._request("GET", f"{GITHUB_API}/user", token=access_token)
        account_id = data.get("id")
        login = data.get("login")
        if account_id is None or not isinstance(login, str):
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid GitHub identity.")
        return ProviderIdentity(account_id=str(account_id), display_name=login[:255])

    async def revoke(self, access_token: str) -> None:
        # OAuth App revocation requires basic-auth client credentials and a token payload.
        await self._request(
            "DELETE",
            f"{GITHUB_API}/applications/{self.settings.github_oauth_client_id}/token",
            auth=(
                self.settings.github_oauth_client_id or "",
                self.settings.github_oauth_client_secret or "",
            ),
            json={"access_token": access_token},
        )

    async def repositories(self, access_token: str) -> list[RepositoryInfo]:
        data = await self._request_list(
            "GET",
            f"{GITHUB_API}/user/repos",
            token=access_token,
            params={
                "per_page": "100",
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        return [
            RepositoryInfo(
                id=str(item["id"]),
                full_name=str(item["full_name"])[:500],
                private=bool(item.get("private")),
                url=str(item.get("html_url") or "")[:2000],
                default_branch=str(item["default_branch"])[:255]
                if item.get("default_branch")
                else None,
            )
            for item in data
            if item.get("id") is not None and item.get("full_name")
        ]

    async def issues(self, access_token: str, repository: str) -> list[SourceObjectInfo]:
        data = await self._repository_list(access_token, repository, "issues", {"state": "all"})
        return [self._issue(item) for item in data if "pull_request" not in item][:50]

    async def pull_requests(self, access_token: str, repository: str) -> list[SourceObjectInfo]:
        data = await self._repository_list(access_token, repository, "pulls", {"state": "all"})
        return [self._pull_request(item) for item in data][:50]

    async def commits(self, access_token: str, repository: str) -> list[SourceObjectInfo]:
        data = await self._repository_list(access_token, repository, "commits", {})
        return [self._commit(item) for item in data][:50]

    async def source_object(
        self, access_token: str, repository: str, object_type: str, external_id: str
    ) -> SourceObjectInfo:
        owner_repo = self._repository_path(repository)
        if object_type == "GITHUB_ISSUE":
            data = await self._request(
                "GET",
                f"{GITHUB_API}/repos/{owner_repo}/issues/{quote(external_id, safe='')}",
                token=access_token,
            )
            if "pull_request" in data:
                raise ProviderError(ProviderFailureKind.NOT_FOUND, "GitHub issue not found.")
            return self._issue(data)
        if object_type == "GITHUB_PULL_REQUEST":
            data = await self._request(
                "GET",
                f"{GITHUB_API}/repos/{owner_repo}/pulls/{quote(external_id, safe='')}",
                token=access_token,
            )
            return self._pull_request(data)
        if object_type == "GITHUB_COMMIT":
            data = await self._request(
                "GET",
                f"{GITHUB_API}/repos/{owner_repo}/commits/{quote(external_id, safe='')}",
                token=access_token,
            )
            return self._commit(data)
        raise ProviderError(ProviderFailureKind.NOT_FOUND, "Unsupported GitHub object.")

    async def _repository_list(
        self, token: str, repository: str, collection: str, params: dict
    ) -> list[dict]:
        return await self._request_list(
            "GET",
            f"{GITHUB_API}/repos/{self._repository_path(repository)}/{collection}",
            token=token,
            params={**params, "per_page": "50"},
        )

    @staticmethod
    def _repository_path(repository: str) -> str:
        parts = repository.split("/")
        if len(parts) != 2 or not all(parts):
            raise ProviderError(ProviderFailureKind.NOT_FOUND, "Repository not found.")
        return f"{quote(parts[0], safe='')}/{quote(parts[1], safe='')}"

    @staticmethod
    def _issue(data: dict) -> SourceObjectInfo:
        return SourceObjectInfo(
            id=str(data.get("number")),
            number=int(data["number"]) if data.get("number") is not None else None,
            title=str(data.get("title") or "Untitled issue")[:500],
            state=str(data.get("state"))[:50] if data.get("state") else None,
            url=str(data.get("html_url") or "")[:2000],
            summary=str(data.get("body") or "")[:1000] or None,
            metadata={
                "labels": [
                    str(item.get("name"))[:100]
                    for item in data.get("labels", [])[:20]
                    if isinstance(item, dict) and item.get("name")
                ]
            },
        )

    @staticmethod
    def _pull_request(data: dict) -> SourceObjectInfo:
        return SourceObjectInfo(
            id=str(data.get("number")),
            number=int(data["number"]) if data.get("number") is not None else None,
            title=str(data.get("title") or "Untitled pull request")[:500],
            state=str(data.get("state"))[:50] if data.get("state") else None,
            url=str(data.get("html_url") or "")[:2000],
            summary=str(data.get("body") or "")[:1000] or None,
            metadata={"draft": bool(data.get("draft")), "merged": bool(data.get("merged"))},
        )

    @staticmethod
    def _commit(data: dict) -> SourceObjectInfo:
        sha = str(data.get("sha") or "")
        commit = data.get("commit") if isinstance(data.get("commit"), dict) else {}
        message = str(commit.get("message") or "Untitled commit")
        title = message.splitlines()[0][:500]
        return SourceObjectInfo(
            id=sha,
            number=None,
            title=title,
            state=None,
            url=str(data.get("html_url") or "")[:2000],
            summary=message[:1000],
            metadata={"sha": sha[:40]},
        )

    def _token(self, data: dict, refresh_token: str | None = None) -> OAuthToken:
        access = data.get("access_token")
        if not isinstance(access, str):
            raise ProviderError(ProviderFailureKind.AUTHENTICATION, "Token exchange failed.")
        expires = data.get("expires_in")
        scopes = str(data.get("scope", self.settings.github_oauth_scopes)).replace(",", " ").split()
        return OAuthToken(
            access_token=access,
            refresh_token=data.get("refresh_token") or refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=int(expires))
            if expires is not None
            else None,
            scopes=tuple(scopes),
        )

    def _headers(self, token: str | None) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _request(self, method: str, url: str, *, token: str | None = None, **kwargs) -> dict:
        response = await self._send(method, url, token=token, **kwargs)
        if response.status_code >= 400:
            raise self._http_error(response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(
                ProviderFailureKind.INVALID_RESPONSE, "Invalid GitHub response."
            ) from exc
        if not isinstance(data, dict):
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid GitHub response.")
        if data.get("error"):
            raise ProviderError(ProviderFailureKind.AUTHENTICATION, "GitHub authorization failed.")
        return data

    async def _request_list(
        self, method: str, url: str, *, token: str | None = None, **kwargs
    ) -> list[dict]:
        response = await self._send(method, url, token=token, **kwargs)
        if response.status_code >= 400:
            raise self._http_error(response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(
                ProviderFailureKind.INVALID_RESPONSE, "Invalid GitHub response."
            ) from exc
        if not isinstance(data, list):
            raise ProviderError(ProviderFailureKind.INVALID_RESPONSE, "Invalid GitHub list.")
        return [item for item in data if isinstance(item, dict)]

    async def _send(
        self, method: str, url: str, *, token: str | None = None, **kwargs
    ) -> httpx.Response:
        headers = {**self._headers(token), **kwargs.pop("headers", {})}
        try:
            if self.client:
                return await self.client.request(method, url, headers=headers, **kwargs)
            async with httpx.AsyncClient(
                timeout=self.settings.integration_timeout_seconds
            ) as client:
                return await client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                ProviderFailureKind.UNAVAILABLE, "Provider request timed out."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                ProviderFailureKind.UNAVAILABLE, "Provider is unavailable."
            ) from exc

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
        return ProviderError(kind, "GitHub request failed.")
