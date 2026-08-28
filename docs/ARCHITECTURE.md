# Loris PMO architecture

Status: foundation and Projects Core architecture  
Date: 2026-08-28  
Product authority: `PROJECT_INTELLIGENCE_SPEC.md`

## 1. Scope

This document defines the technical foundation for Loris PMO and the Projects Core increment. The application now supplies the shell, authentication, owned project records, objectives, success criteria, real portfolio counts, persistence and migration infrastructure, API conventions, testing, Docker-based local development, and replaceable AI boundaries. Remaining product areas are introduced incrementally.

The application starts empty. No production project, task, financial, risk, or other business fixture is created.

## 2. Architecture

Loris PMO is a modular monolith with independently built frontend and backend applications:

```text
Browser
  |
  | HTTP / JSON
  v
React + TypeScript
  |
  | /api/v1/*
  v
FastAPI application
  |-- API and authentication
  |-- application services
  |-- deterministic analytics (future modules)
  |-- AI service -> provider interface -> Gemini provider
  |-- repositories
  v
PostgreSQL
```

This is the simplest structure that preserves the specification's separation requirements. It avoids premature microservices while keeping module boundaries that may later be extracted if operational needs justify it.

### Responsibility boundaries

- React owns presentation, navigation, accessibility, client-side interaction, and localization.
- API routes validate transport data and delegate behavior; they do not own business rules.
- Services own use cases and transactions.
- Repositories own database access.
- Models define persistence; schemas define public API contracts.
- Analytics owns deterministic calculations and never delegates factual arithmetic to an LLM.
- AI owns interpretation and proposals through a provider-neutral service.
- Automation and notification packages reserve explicit future boundaries without adding infrastructure now.

## 3. Technology choices

### Frontend

- React and TypeScript, built with Vite.
- React Router for public and protected route structure.
- `i18next` and `react-i18next` for English and Italian resources.
- Native CSS custom properties for a purposeful light/dark design system. Theme preference is device-local presentation state.
- Native `fetch` behind a typed API client. A larger server-state library can be introduced when feature data warrants caching and invalidation.
- Vitest and React Testing Library for components and critical shell behavior.

### Backend

- Python 3.12 and FastAPI.
- Pydantic Settings for validated environment configuration.
- SQLAlchemy 2 asynchronous sessions with `asyncpg` for PostgreSQL.
- Alembic for reproducible schema migrations.
- Argon2 password hashing through `pwdlib`.
- Signed JWT access tokens stored in an HttpOnly cookie. Mutating cookie-authenticated requests require a matching double-submit CSRF token.
- Pytest with HTTPX for services and APIs.

### Infrastructure

- Docker Compose starts `frontend`, `backend`, and `db` services only.
- PostgreSQL data is held in a named development volume.
- Backend startup runs migrations before the API server.
- Vite proxies `/api` to FastAPI during containerized development.

Pandas is intentionally not installed in the foundation. It should be added when a concrete analytical workload benefits from tabular/vectorized processing; ordinary KPI formulas should remain typed Python functions.

## 4. Repository structure

```text
loris-pmo/
|-- backend/
|   |-- alembic/
|   |-- app/
|   |   |-- ai/
|   |   |-- analytics/
|   |   |-- api/v1/
|   |   |-- auth/
|   |   |-- automation/
|   |   |-- core/
|   |   |-- models/
|   |   |-- notifications/
|   |   |-- repositories/
|   |   |-- schemas/
|   |   `-- services/
|   `-- tests/
|-- frontend/
|   `-- src/
|       |-- components/
|       |-- features/
|       |-- i18n/
|       |-- layouts/
|       |-- pages/
|       |-- services/
|       |-- styles/
|       `-- types/
|-- docs/
|-- scripts/
|-- .env.example
`-- docker-compose.yml
```

Feature-specific frontend and backend packages will be added incrementally rather than creating empty implementations for all future areas.

## 5. Database strategy

PostgreSQL is the production and Docker development database. SQLAlchemy metadata is the code-level schema definition; Alembic migrations are the only supported way to evolve deployed schemas.

The foundation migration creates `users`, including:

- UUID primary key;
- unique, normalized email;
- password hash, active flag, and timestamps;
- an index supporting login lookup.

Projects Core adds `projects`, `objectives`, `success_criteria`, and `audit_events`. They use UUID primary keys, explicit foreign keys, UTC-aware timestamps, constraints, and indexes for owner, archive, status, and relationship access patterns. `projects.owner_user_id` makes ownership explicit even during the personal phase. Project creation and every mutation commit the domain change and its audit event in one transaction.

Historical records will be append-oriented where required (especially activity/audit and AI decisions). Soft deletion will be introduced only for entities where history and restore behavior justify its added complexity.

## 6. Authentication and security

The initial account is created explicitly with the backend CLI; there is no public registration or seeded credential.

Authentication flow:

```text
credentials -> backend validation -> Argon2 verification
            -> short-lived signed JWT in HttpOnly SameSite cookie
            -> separate CSRF cookie for double-submit validation
```

- Protected endpoints resolve the current active user on the backend.
- The frontend never receives password hashes, database credentials, signing keys, or Gemini credentials.
- State-changing authenticated requests must send `X-CSRF-Token` matching the CSRF cookie and signed token claim.
- Cookie `Secure` behavior is environment controlled: enabled outside local development.
- CORS allows only the configured frontend origin and credentials.
- Logout expires both authentication cookies.
- Authentication errors use the same public error envelope as other API failures.

Future multi-user support can add registration/invitations and authorization policies without changing ownership or authentication interfaces.

## 7. API structure

Application endpoints are versioned under `/api/v1`:

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
GET  /api/v1/portfolio/summary
GET  /api/v1/projects
POST /api/v1/projects
GET  /api/v1/projects/{project_id}
PATCH /api/v1/projects/{project_id}
POST /api/v1/projects/{project_id}/archive
```

Nested objective and success-criterion routes support list, create, update, and delete operations under their owning project.

Operational endpoints remain outside versioned product APIs:

```text
GET /health       # process liveness
GET /ready        # database readiness
```

Errors use a stable envelope:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Email or password is incorrect.",
    "details": null,
    "request_id": "..."
  }
}
```

Request IDs are accepted or generated per request and returned in `X-Request-ID`. Validation failures, expected application errors, and unexpected failures are normalized; normal responses never expose stack traces or ORM objects.

The portfolio response aggregates real, non-archived project counts for the authenticated owner. It reports total, active, on-hold, and completed projects and returns zeroes for a new account; it never uses sample content.

## 8. Frontend structure

Public routes contain the login screen. Protected routes render an `AppShell` composed of:

- responsive sidebar with Portfolio, Projects, AI Copilot, and Settings;
- top navigation with theme, language, and account/logout controls;
- main outlet area with route-level loading and error states;
- placeholder pages only for future areas, without simulating their functionality.

The portfolio and project routes fetch authenticated API data. Projects provide a searchable and filterable card view, a three-step creation wizard, editable overview data, objectives, success criteria, and archive confirmation. The first-project call to action opens the same creation wizard. Unsupported future metrics are labelled unavailable instead of derived from incomplete data.

Localization keys live in language resource files. Components do not duplicate Italian/English literals. Theme variables cover both light and dark modes, honor the device preference initially, and persist an explicit user preference locally.

## 9. AI architecture

```text
Application service
      |
      v
AIService (provider-neutral use cases and policy checks)
      |
      v
AIProvider protocol
      |
      +--> GeminiProvider
      `--> future provider
```

The foundation defines the provider contract, a safe unavailable provider, configuration, and Gemini adapter boundary. No AI endpoint or Copilot behavior is exposed yet, and an API key is not required for core operation.

Future AI output that could affect operational data must create a persisted proposal. Only a separate confirmation endpoint may validate and apply it in a transaction, followed by an audit event. Providers will never receive a database session or unrestricted execution tool. This makes human review enforceable outside prompts.

## 10. Analytics, automation, and notifications

These are internal backend modules, not additional services:

```text
Operational event -> automation rule evaluation -> typed action -> service -> audit
Operational data  -> analytics service -> KPI/health values -> API/alerts/AI context
Notification request -> preferences/policy -> channel adapter
```

Only package boundaries are created now. Queueing, Redis, schedulers, and email providers are deferred until a feature requires them.

## 11. Testing strategy

Backend tests cover:

- application startup and liveness;
- readiness/database dependency behavior;
- authentication success/failure and protected access;
- password hashing and token validation;
- project ownership, validation, filters, sorting, archiving, nested records, audit creation, and real portfolio counts.

Fast unit/API tests use an isolated SQLite database through SQLAlchemy dependency overrides. A PostgreSQL-marked integration test uses `TEST_DATABASE_URL` when provided; Docker Compose and Alembic are the primary PostgreSQL integration path.

Frontend tests cover:

- login form behavior and error feedback;
- protected-route loading/authentication decisions;
- shell navigation, language switching, theme switching, portfolio rendering, project listing, and creation-wizard behavior.

CI-ready commands run backend tests, frontend tests, TypeScript compilation, and the production frontend build. Each future feature must add tests near the business logic it introduces.

## 12. Docker and local development

`docker compose up --build` builds and starts the three required services. Compose waits for PostgreSQL health, runs migrations, and then starts FastAPI. The frontend development server proxies API calls to the backend, avoiding frontend knowledge of database or secret configuration.

Account creation is an explicit operator action after startup:

```bash
docker compose exec backend python -m app.cli create-user
```

No migration or startup hook inserts business records.

## 13. Development phases

1. Foundation (complete): architecture, auth, shell, i18n, themes, migrations, AI boundary, Docker, tests.
2. Projects (complete): project ownership, creation wizard, objectives, criteria, archive workflow, audit events, and portfolio aggregation.
3. Work planning: tasks, dependencies, milestones, and shared list/Kanban/timeline data.
4. People and finance: people, membership, workload, budgets, expenses, and deterministic calculations.
5. Control and memory: risks, issues, changes, meetings, decisions, logs, alerts, and automation.
6. Intelligence: centralized KPIs/health, context packages, AI proposals, recommendations, and scenario isolation.
7. Documents and delivery: retrieval, reports, validated import/export, notifications, and release hardening.

Each phase adds schema via migrations, implements use cases behind services, exposes typed APIs, and completes UI/empty/error states with tests.

## 14. Significant constraints and deferred choices

- There is no fake production data.
- There is no public registration in the personal first release.
- The foundation does not call Gemini; it only supplies a replaceable adapter boundary.
- No charting, Pandas, job queue, mail provider, object storage, or RAG dependency is added before a concrete use case exists.
- Kubernetes and microservices are outside V1.
- Hosted deployment is deferred; the required target is local Docker Compose.
