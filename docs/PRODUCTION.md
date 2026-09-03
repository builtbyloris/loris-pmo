# Production operations

Status: V2.5 production-readiness guide  
Last reviewed: 2026-09-04

Loris PMO remains local-first. This guide describes an optional production deployment; it does not create infrastructure, deploy the application, or replace the local Docker Compose workflow.

Final validation: the three previously verified logging, health-probe, and same-origin configuration blockers are resolved. Rebuilt non-root/read-only containers passed health/readiness, synthetic error-log redaction, and authenticated smoke checks against disposable TLS-enabled PostgreSQL. See [V2 feature audit](V2_FEATURE_AUDIT.md). This is technical readiness, not a cloud deployment, release, or production SLA.

## Runtime topology

The supported production topology is:

```text
TLS gateway / hosting edge
  |-- /             -> static React build
  `-- /api, /health, /ready -> FastAPI
                                  |-- managed PostgreSQL
                                  `-- private local or S3-compatible document storage
```

A same-origin gateway is recommended. Same-site subdomains are also supported when `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `TRUSTED_HOSTS`, and `COOKIE_DOMAIN` are configured deliberately. Unrelated frontend and backend provider domains are not compatible with the current double-submit CSRF cookie flow because frontend JavaScript cannot read a cookie belonging to an unrelated site.

TLS terminates at the gateway or hosting provider. The application does not manage certificates. Forwarded headers must be accepted only from the known gateway address; never configure Uvicorn's forwarded-allow list as `*` on a directly reachable backend.

## Environment model

| Mode | Database | Cookies | API docs | Storage | Intended use |
|---|---|---|---|---|---|
| `development` | Local PostgreSQL | HTTP-compatible | Enabled | Local by default | Docker/local work |
| `test` | Isolated SQLite plus optional PostgreSQL test | HTTP-compatible | Enabled | Temporary local/fake S3 | Automated tests |
| `production` | PostgreSQL only, TLS required | `Secure` | Disabled | Absolute local path or configured S3 | Hosted runtime |

Configuration is centralized in `backend/app/core/config.py`. Production startup fails when critical configuration is unsafe. Use the tracked template only as a checklist:

```bash
cp .env.production.example .env.production
# Replace every deployment placeholder.
docker compose --env-file .env.production -f docker-compose.prod.yml \
  run --rm migrate python -m app.cli check-config
```

The check reports only safe booleans/counts and database driver information. It never prints credentials or complete URLs.

## Required production settings

- `SECRET_KEY`: random, at least 48 characters, not a documented placeholder.
- `DATABASE_URL`: `postgresql+asyncpg://...` with non-placeholder credentials.
- `DATABASE_SSL_MODE`: `require`, `verify-ca`, or `verify-full` according to the database provider.
- `FRONTEND_URL` and every `CORS_ALLOWED_ORIGINS` value: explicit HTTPS origins.
- `TRUSTED_HOSTS`: comma-separated API host names, never `*`.
- `DEBUG=false` and `API_DOCS_ENABLED=false`.
- `DOCUMENT_STORAGE_BACKEND=local|s3`; local paths must be absolute.
- `INTEGRATION_TOKEN_ENCRYPTION_KEY`: required when either OAuth provider is enabled.
- OAuth client ID/secret pairs and HTTPS callback URLs: required together only for enabled providers.

Gemini, Google, and GitHub remain optional. Their absence does not block startup or core readiness. Never use a `VITE_*` variable for a server secret.

## Authentication, cookies, CORS, and CSRF

Access tokens remain in `HttpOnly` cookies. Production cookies are always `Secure`; mutating requests still require the readable CSRF cookie value in `X-CSRF-Token`.

Recommended same-origin gateway:

```text
https://pmo.example.com/       -> frontend
https://pmo.example.com/api/*  -> backend
VITE_API_BASE_URL=
COOKIE_DOMAIN=
COOKIE_SAME_SITE=lax
CORS_ALLOWED_ORIGINS=https://pmo.example.com
```

Supported same-site subdomains:

```text
https://pmo.example.com
https://api.example.com
VITE_API_BASE_URL=https://api.example.com
COOKIE_DOMAIN=.example.com
COOKIE_SAME_SITE=lax
CORS_ALLOWED_ORIGINS=https://pmo.example.com
```

Do not use wildcard credentialed CORS. Do not set `SameSite=None` merely to connect unrelated provider domains: it does not make the CSRF cookie readable by the frontend.

There is no process-local rate limiter in V2.5. Apply rate limits at the trusted gateway for login, OAuth callbacks, AI generation, uploads, and imports. A gateway is the correct shared enforcement point when multiple backend replicas exist.

## PostgreSQL and migrations

The same SQLAlchemy/Alembic path supports local and managed PostgreSQL. Pool size, overflow, timeout, recycle interval, and TLS mode are centralized environment settings.

Run migrations once before starting or rolling out application replicas:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml \
  --profile migration run --rm migrate
docker compose --env-file .env.production -f docker-compose.prod.yml up -d backend frontend
curl --fail https://api.example.com/health
curl --fail https://api.example.com/ready
```

Do not put `alembic upgrade head` in every production replica's startup command. For rollback, restore a verified database backup or deploy the preceding application image; do not automatically downgrade a live database unless that exact downgrade has been rehearsed and data-loss implications are accepted.

## Health, readiness, and shutdown

- `GET /health` proves the process is alive and returns only status/version.
- `GET /ready` verifies database connectivity and returns a safe `503 service_not_ready` on failure.
- Optional AI and OAuth providers do not affect readiness.
- Uvicorn handles termination signals; the application disposes the SQLAlchemy engine during lifespan shutdown.

## Logging and errors

Production application/access logs are structured console JSON. Safe request fields are request ID, method, route template, status, duration, and project ID when it is already a path parameter. Query strings, bodies, cookies, tokens, provider payloads, prompts, document text, and email content are never access-logged.

Production Uvicorn and asyncio exception-bearing records pass through a redaction filter before handlers: only a stable runtime event, exception type, and OS error number where applicable are retained. Already-formatted lifespan tracebacks are also redacted. Ordinary startup/shutdown messages and operational failure signals remain enabled. The application error event retains its request ID; development/test runtime logging is restored without this production filter.

Unexpected errors return stable redacted JSON. The application error logger records request ID and exception type only. Uvicorn's duplicate exception path is now sanitized before logging; controlled runtime tests confirm no exception marker or raw traceback reaches production output. Operators still receive structured error events and ordinary server operational messages.

## Document storage

`local` keeps the established private volume behavior. `s3` uses server-side credentials and private S3 API operations; no public URL or presigned permanent URL is emitted.

For S3-compatible storage configure:

```text
DOCUMENT_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://provider-endpoint.example
S3_BUCKET=private-bucket
S3_REGION=provider-region
S3_ACCESS_KEY_ID=<injected secret>
S3_SECRET_ACCESS_KEY=<injected secret>
```

On platforms with an attached IAM role, explicit access-key variables may remain empty. Storage failures fail the affected operation and never fall back to local storage.

Existing local documents are not migrated automatically. A future controlled migration must:

1. freeze document writes;
2. copy every stored key to the private bucket;
3. verify object count, byte size, and preferably a cryptographic hash;
4. test authorized downloads;
5. switch `DOCUMENT_STORAGE_BACKEND`;
6. retain the source backup until a documented rollback window expires.

## Production containers

`backend/Dockerfile` contains runtime dependencies only, runs as UID/GID 10001, exposes health metadata, and does not run migrations automatically. `frontend/Dockerfile.prod` creates a static Vite build served by non-root Nginx with SPA fallback and safe headers.

`docker-compose.prod.yml` is a production-like reference, not an orchestration service or cloud deployment. Secrets enter through the untracked `.env.production` file or the hosting platform's secret manager. For hosted static frontend builds, set only `VITE_API_BASE_URL`; it is public by definition.

The backend image healthcheck connects internally to `127.0.0.1:8000`, but explicitly sends the first configured `TRUSTED_HOSTS` entry as its HTTP Host. The transport target is internal; the Host remains an approved public hostname. No extra globally trusted hostname, wildcard, DNS lookup, or health-route authorization bypass is introduced. Normal untrusted Host requests remain rejected.

In production Compose and Vite, an empty or unset `VITE_API_BASE_URL` intentionally selects same-origin relative `/api/...` paths. Set an explicit HTTPS origin for split hosting. One shared build/runtime validator rejects malformed origins, credentials, paths, query strings, fragments, and non-HTTPS production origins. Development's existing Vite proxy remains unchanged. Same-origin deployment still requires the documented gateway to route `/api` to the backend; static Nginx alone is not that gateway. OAuth remains on backend endpoints.

## Account creation

There is no public signup. After the migration and backend startup, run the CLI in the backend execution environment:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec backend python -m app.cli create-user --email administrator@example.com
```

The password prompt does not echo input. Prefer an environment console or one-off job whose command history does not contain the password.

## Operations checklist

- Pin and retain the application image/revision being deployed.
- Run `python -m app.cli check-config`.
- Verify a recent PostgreSQL backup and object-storage recovery procedure.
- Run Alembic once and confirm head.
- Start one backend replica; check `/health` and `/ready`.
- Start/activate the frontend and verify login, CSRF mutation, download, and OAuth callback routing.
- Apply gateway request-size and rate limits.
- Monitor 5xx rate, readiness, database pool pressure, and storage failures.
- Roll forward with a corrected image when possible.

See `docs/BACKUP_RESTORE.md` for local versus cloud recovery responsibilities and `docs/CLOUD_FREE_DEPLOYMENT.md` for a non-SLA demonstration topology.
