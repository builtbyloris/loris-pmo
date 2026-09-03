# Integrations

Status: V2.4 complete on unreleased `v2-development`

V2.4 adds optional, read-only Google and GitHub integrations. PostgreSQL remains the factual source of truth. External data is browsed only on an explicit user action, and an operational Meeting is created only after a separate preview and confirmation. Provider content cannot mutate tasks, issues, milestones, finance, or other project records.

## Supported providers

- Google Calendar: list calendars and bounded upcoming events; explicitly link an event or preview/confirm a Meeting import.
- Gmail: explicit bounded message search using metadata and snippets; explicitly link a selected message.
- GitHub: list accessible repositories and bounded issues, pull requests, and commits; explicitly link a selected object to a task.

No provider is contacted during startup, page refresh, health checks, AI context construction, or background polling. Provider status remains safely unavailable until its server-side configuration is complete.

## Security model

OAuth accounts are owned by the authenticated application user. A user cannot attach or use another user's provider account. Project connections additionally require active project membership and `integrations.manage`; browsing linked sources requires `integrations.read` plus ownership of the underlying OAuth account.

Access and refresh tokens are encrypted with a dedicated Fernet key before storage. They are never returned through API schemas, included in audit events, placed in frontend storage, or sent to Gemini. OAuth state is random, persisted only as a SHA-256 digest, expires after ten minutes, is bound to the initiating user/provider, and is single use. Google and GitHub use PKCE S256.

External content is untrusted. The application stores only bounded metadata selected by its provider adapters. AI receives only explicit, authorized, currently available external links through the backend-owned evidence catalog; it never receives an inbox dump, live provider access, credentials, or tools. Unknown or cross-project evidence remains invalid.

## Configuration

Copy `.env.example` to the ignored `.env` file. Generate a dedicated encryption key:

```bash
backend/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Set the result only in `INTEGRATION_TOKEN_ENCRYPTION_KEY`. Do not reuse `SECRET_KEY`, commit `.env`, or place provider credentials in source, screenshots, logs, or documentation.

Common settings:

```dotenv
INTEGRATION_TOKEN_ENCRYPTION_KEY=<generated-fernet-key>
INTEGRATION_TIMEOUT_SECONDS=15

GOOGLE_OAUTH_CLIENT_ID=<google-oauth-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/integrations/oauth/google/callback
GOOGLE_OAUTH_SCOPES=openid email https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/gmail.readonly

GITHUB_OAUTH_CLIENT_ID=<github-oauth-client-id>
GITHUB_OAUTH_CLIENT_SECRET=<github-oauth-client-secret>
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/integrations/oauth/github/callback
GITHUB_OAUTH_SCOPES=read:user
```

Leaving a provider's client id/secret empty is supported and keeps that provider unavailable without affecting the core application.

## OAuth application setup

For Google, create a Web application OAuth client and register the exact redirect URI shown above. Configure the consent screen and authorize only the centralized scopes. Calendar and Gmail access are read-only. The Gmail adapter uses explicit bounded search, which requires `gmail.readonly`; it does not request Gmail write scopes.

For GitHub, create an OAuth App and register the exact callback URL. The default `read:user` scope deliberately limits the provider to public repositories visible to the user. An operator may explicitly configure `repo` when private-repository read access is required, but GitHub OAuth App scopes make that a broad repository scope. Loris PMO still exposes no provider write operation.

Redirect URIs must exactly match both the provider application and backend environment. The callback requires the initiating user to remain authenticated. Successful callbacks redirect only to a validated path under `FRONTEND_URL`.

## Connection and sync lifecycle

1. The user starts OAuth from the Integrations workspace.
2. The backend creates bounded state/PKCE records and redirects to the provider.
3. The authenticated callback exchanges the code server-side and stores encrypted credentials.
4. A manager selects a provider-owned calendar, Gmail account, or repository from a server-fetched list and attaches it to a project.
5. Users browse or refresh only through explicit actions. Successful calls update safe last-used/last-sync timestamps.
6. Selected provider objects may be linked. Links are idempotent and do not copy unrestricted provider payloads.

Calendar Meeting import is a two-step operation. Preview is non-mutating and returns a short-lived token bound to the current provider event fingerprint. Confirmation refetches the event, rejects stale previews, and creates at most one Meeting/link pair.

Gmail links default to `PRIVATE`, visible only to their creator. The user must explicitly choose `PROJECT` sharing or `FINANCE`; finance-scoped links additionally require finance permission. GitHub task links record only an explicit descriptive relation and never close, update, or schedule the task.

## Disconnect and recovery

Disconnect attempts provider revocation and always removes local encrypted credentials. It marks related project connections unavailable and external links unavailable, while preserving Meetings, tasks, issues, and other local records. Reconnection is explicit; the application never silently reauthorizes or falls back to another account.

Authentication failures mark the account `REAUTH_REQUIRED`. Rate limits, provider outages, malformed responses, and timeouts map to stable safe application errors without including upstream bodies or credentials. A missing external object marks its link unavailable; deleting or changing it at the provider does not delete local project data.

Encryption-key rotation is an operator-controlled maintenance operation. Existing ciphertext cannot be decrypted after replacing the key. Before rotation, disconnect configured accounts or perform an audited offline re-encryption procedure that decrypts with the old key and encrypts with the new key. If the previous key is lost, provider accounts must be disconnected locally and explicitly reconnected.

## Auditing and privacy

Connection, disconnection, project attachment, refresh, link, unlink, and confirmed Meeting import actions create append-only audit events, with selected project-visible link/import activity also represented in the Project Log. Audit metadata contains safe identifiers and provider/kind status only—never access tokens, refresh tokens, authorization codes, request headers, email bodies, prompts, or raw provider responses.

V2.4 intentionally has no webhook ingestion, background synchronization, Gmail body/attachment ingestion, write-back, autonomous AI action, ownership transfer, or cloud secret manager. Provider calls require live network access and configured operator-owned OAuth applications; automated tests use deterministic provider doubles.

Production deployments must use HTTPS callback URLs and must pass `python -m app.cli check-config` before migration/startup. The integration key is an operational recovery dependency: if it is lost, stored OAuth credentials cannot be decrypted and users must reconnect. See [Production operations](PRODUCTION.md) and [Backup and Restore](BACKUP_RESTORE.md).
