# Loris PMO architecture

Status: foundation through Project Assistant
Date: 2026-08-30
Product authority: `PROJECT_INTELLIGENCE_SPEC.md`

## 1. Scope

This document defines the technical foundation through the Project Assistant. In addition to complete operational and deterministic intelligence domains, the application now supplies provider-neutral AI execution, a bounded deterministic project-context builder, structured evidence-grounded project Q&A, usage metadata, safe unavailable behavior, and bilingual assistant views. Proactive AI, recommendations, scenarios, meetings, documents, and knowledge retrieval remain deferred.

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
  |-- deterministic analytics
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

Projects Core adds `projects`, `objectives`, `success_criteria`, and `audit_events`. Later cores add planning, people, finance, control, and memory records. Project Intelligence adds `alerts` and `health_snapshots`. Alerts have a project-scoped stable condition key, severity, lifecycle timestamps, translation keys, evidence, and an optional polymorphic related-entity reference. Health snapshots persist only a first or materially changed score, status, dimension, or driver set. All records use UUID primary keys, explicit foreign keys, UTC-aware timestamps, constraints, and indexes. Composite foreign keys protect same-project operational relationships, while system-created alert relationships are validated from owned facts and cannot be client-created. Domain mutations and their audit events commit in one transaction.

People are owner-scoped reusable records and are deliberately separate from authentication users. A project member relates a person to a project and stores the stable role, responsibilities, and availability percentage. Removing a membership never deletes the person. Tasks support multiple assignees through `task_assignees`; each assignee references a project member, and composite constraints prevent cross-project assignment even if application validation is bypassed. `audit_events.project_id` is nullable only for owner-level events such as person creation; project-domain events remain project-scoped.

Tasks use an `archived_at` timestamp rather than destructive deletion. One subtask level is supported deliberately. Milestone progress is not stored: it is the arithmetic mean of completion percentages for linked, non-cancelled tasks, or unavailable when no eligible task exists. Project task progress uses the same rule across all active project tasks.

Expenses are append-oriented financial records. They may be updated while active, but cancellation is terminal and preserves their history. A category referenced by any expense cannot be deleted. Amount constraints are enforced in both API validation and the database. Category, task, and milestone associations use composite project foreign keys so cross-project links are impossible even if application validation is bypassed.

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
GET  /api/v1/projects/{project_id}/tasks
POST /api/v1/projects/{project_id}/tasks
GET  /api/v1/projects/{project_id}/tasks/{task_id}
PATCH /api/v1/projects/{project_id}/tasks/{task_id}
POST /api/v1/projects/{project_id}/tasks/{task_id}/archive
GET  /api/v1/projects/{project_id}/milestones
POST /api/v1/projects/{project_id}/milestones
PATCH /api/v1/projects/{project_id}/milestones/{milestone_id}
GET  /api/v1/projects/{project_id}/task-dependencies
POST /api/v1/projects/{project_id}/task-dependencies
DELETE /api/v1/projects/{project_id}/task-dependencies/{dependency_id}
GET  /api/v1/projects/{project_id}/work-planning/summary
GET  /api/v1/people
POST /api/v1/people
PATCH /api/v1/people/{person_id}
GET  /api/v1/projects/{project_id}/members
POST /api/v1/projects/{project_id}/members
PATCH /api/v1/projects/{project_id}/members/{member_id}
DELETE /api/v1/projects/{project_id}/members/{member_id}
GET  /api/v1/projects/{project_id}/stakeholders
POST /api/v1/projects/{project_id}/stakeholders
PATCH /api/v1/projects/{project_id}/stakeholders/{stakeholder_id}
DELETE /api/v1/projects/{project_id}/stakeholders/{stakeholder_id}
GET  /api/v1/projects/{project_id}/workload
GET  /api/v1/projects/{project_id}/people/summary
GET  /api/v1/projects/{project_id}/budget
PATCH /api/v1/projects/{project_id}/budget
GET  /api/v1/projects/{project_id}/budget/categories
POST /api/v1/projects/{project_id}/budget/categories
PATCH /api/v1/projects/{project_id}/budget/categories/{category_id}
DELETE /api/v1/projects/{project_id}/budget/categories/{category_id}
GET  /api/v1/projects/{project_id}/expenses
POST /api/v1/projects/{project_id}/expenses
GET  /api/v1/projects/{project_id}/expenses/{expense_id}
PATCH /api/v1/projects/{project_id}/expenses/{expense_id}
POST /api/v1/projects/{project_id}/expenses/{expense_id}/cancel
GET  /api/v1/projects/{project_id}/budget/analytics
GET  /api/v1/projects/{project_id}/risks
POST /api/v1/projects/{project_id}/risks
GET  /api/v1/projects/{project_id}/risks/{risk_id}
PATCH /api/v1/projects/{project_id}/risks/{risk_id}
POST /api/v1/projects/{project_id}/risks/{risk_id}/close
GET  /api/v1/projects/{project_id}/issues
POST /api/v1/projects/{project_id}/issues
GET  /api/v1/projects/{project_id}/issues/{issue_id}
PATCH /api/v1/projects/{project_id}/issues/{issue_id}
POST /api/v1/projects/{project_id}/issues/{issue_id}/resolve
POST /api/v1/projects/{project_id}/issues/{issue_id}/close
GET  /api/v1/projects/{project_id}/changes
POST /api/v1/projects/{project_id}/changes
GET  /api/v1/projects/{project_id}/changes/{change_id}
PATCH /api/v1/projects/{project_id}/changes/{change_id}
POST /api/v1/projects/{project_id}/changes/{change_id}/{submit|approve|reject|implement|cancel}
GET  /api/v1/projects/{project_id}/control/summary
GET  /api/v1/projects/{project_id}/kpis
GET  /api/v1/projects/{project_id}/health
GET  /api/v1/projects/{project_id}/alerts
GET  /api/v1/projects/{project_id}/intelligence
POST /api/v1/projects/{project_id}/intelligence/recalculate
POST /api/v1/projects/{project_id}/alerts/{alert_id}/{acknowledge|read}
GET  /api/v1/portfolio/intelligence
GET  /api/v1/projects/{project_id}/ai/status
POST /api/v1/projects/{project_id}/ai/chat
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

The portfolio response aggregates real, non-archived project counts for the authenticated owner. It reports total, active, on-hold, and completed projects and returns zeroes for a new account; it never uses sample content. Work-planning responses use the same owner-scoped project lookup and return `404` for foreign identifiers.

Scheduling dependencies are stored as the user-facing `BLOCKS`, `DEPENDS_ON`, or `RELATED_TO` relation. Cycle analysis normalizes `A BLOCKS B` and `B DEPENDS_ON A` to the same directed edge. Equivalent scheduling duplicates are rejected; related links are symmetric and normalized by identifier order.

## 8. Frontend structure

Public routes contain the login screen. Protected routes render an `AppShell` composed of:

- responsive sidebar with Portfolio, Projects, AI Copilot, and Settings;
- top navigation with theme, language, and account/logout controls;
- main outlet area with route-level loading and error states;
- placeholder pages only for future areas, without simulating their functionality.

The portfolio and project routes fetch authenticated API data. Projects provide a searchable and filterable card view, a three-step creation wizard, editable overview data, objectives, success criteria, planning metrics, and archive confirmation. The first-project call to action opens the same creation wizard. Unsupported future metrics are labelled unavailable instead of derived from incomplete data.

Work Planning loads tasks, milestones, dependencies, and summary data into one shared feature state. List, Kanban, Timeline, and Milestone views are projections of that same state. Kanban status moves update optimistically, persist through the API, refresh all projections, and roll back with localized feedback on failure. The V1 Timeline renders real task bars and milestone markers. Drag/resize, editable connection lines, and critical-path analysis are deferred until they can be implemented reliably without implying an enterprise scheduling engine.

The People workspace uses Team, Stakeholders, and Workload projections. Team supports reusable person creation/editing and membership management. The stakeholder matrix places stored influence and interest values without generating recommendations. Workload rows consume backend-calculated facts and status; the frontend does not reproduce the formula. Task creation and List assignment editing use the same normalized member identifiers, while List, Kanban, and Timeline resolve display names from current membership data.

The Finance workspace uses Dashboard, Expenses, and Categories projections. The dashboard consumes backend-calculated totals and thresholds; it does not recalculate financial status in the browser. Expense filters and sorting are server-backed, while forms reuse the project's real categories, tasks, and milestones. Archived projects expose finance data read-only.

The Control workspace uses Risks, Issues, and Change Requests projections. The risk register includes a 5×5 matrix driven by backend scores. Issue resolution and change approval/rejection require explicit recorded text. Forms select only the current project's members, tasks, milestones, risks, and issues; the backend and composite foreign keys independently enforce the same boundary. Approved changes never mutate tasks, dates, budgets, or resources automatically.

Project Overview performs an explicit intelligence recalculation, then renders the backend-owned health score, dimension availability, deterministic drivers, KPIs, Attention Required, alert filters, and acknowledgement action. The Portfolio renders current health and control facts for every owned active project. The browser never reimplements a KPI, health, workload, budget, or risk formula.

AI Copilot and the contextual project route render the same Project Assistant. The browser keeps only the current in-memory conversation and sends at most six recent messages. Responses render as text through React, never as untrusted HTML, and present backend-validated evidence, missing information, assumptions, and follow-up questions separately. A missing provider key produces an explicit unavailable state without affecting the project workspace.

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

`ProjectAssistantService` first resolves the owner-scoped project, then asks `ProjectContextBuilder` for a question-relevant package. The builder reuses finance, workload, work-planning, and project-intelligence services for facts and formulas. English/Italian keyword selection deterministically chooses work, finance, control, people, objectives, or memory sections. It caps critical tasks at 12, milestones and control records at 8, recent memory at 6 per type, pending actions at 8, and active alerts at 10. Ordering is deterministic by urgency, severity, due date, recency, and stable identifier.

Gemini is called only through the provider protocol. The REST adapter sends the API key in the server-side `x-goog-api-key` header, applies centralized timeout/token/temperature settings, performs no automatic retry loop, and requests schema-constrained JSON. Provider transport, authentication, rate-limit, timeout, empty, malformed, and contract failures map to safe public errors. The application and readiness endpoint do not require a key.

The centralized system instruction, context JSON, and current question are explicitly separated. Project fields are labelled untrusted data and cannot grant tools or database access. The provider receives no session, credentials, unrelated users/projects, password hashes, tokens, secret keys, or mutation capability. Evidence returned by the model consists only of reference strings; the backend drops unknown references and resolves accepted references from its own context catalog.

V1 conversation continuity is stateless: at most six recent user/assistant messages return from the browser and no prompt or answer is persisted. Audit records contain only provider, model, success/failure, latency, high-level deterministic request topics, selected context sections, safe error code, and token counts when the provider supplies them. AI questions do not enter Project Log.

The Project Assistant is read-only. It has no endpoints for tasks, budgets, assignments, dates, alerts, risks, issues, or change decisions. Future AI output that could affect operational data must use a separate persisted proposal and explicit confirmation flow; that flow is not part of this sprint.

## 10. Analytics, automation, and notifications

These are internal backend modules, not additional services:

```text
Operational event -> automation rule evaluation -> typed action -> service -> audit
Operational data  -> analytics service -> KPI/health values -> API/alerts/AI context
Notification request -> preferences/policy -> channel adapter
```

Only package boundaries are created now. Queueing, Redis, schedulers, and email providers are deferred until a feature requires them.

### Project intelligence and automation

The intelligence service gathers owner-scoped operational facts once per project invocation. It returns a consistent KPI structure with `available` and `reason` fields. Objective progress is calculated only from applicable structured success criteria; schedule, budget, task, resource, and objective dimensions remain unavailable when their prerequisite data is absent.

Health weights are Schedule 25%, Budget 20%, Tasks 20%, Risks 15%, Resources 10%, and Objectives 10%. Scores use documented penalties over stored facts. Unavailable dimensions are excluded and their weights are redistributed proportionally. Thresholds are Healthy 85–100, Watch 70–84, At Risk 50–69, and Critical 0–49. Structured drivers preserve the evidence behind movement.

Eight code-defined V1 rules cover overdue/blocked tasks, milestone deadlines, budget thresholds and forecast, severe risks, critical/aged issues, workload overload, project deadlines, and health thresholds. Code-defined rules avoid production seed data while exposing trigger, condition, action, and enabled metadata through the intelligence response. Explicit synchronous recalculation reconciles all conditions in one project: a stable `(project, condition key)` updates instead of duplicating, resolved conditions close automatically, and reappearance reactivates the same record while resetting acknowledgement. Clients cannot create or manually resolve system alerts.

Recalculation records a snapshot only when the score, status, dimensions, or drivers materially change. Audit records are emitted for state-changing automation executions, acknowledgement, health status movement, alert generation/reactivation/escalation, and resolution. Only At Risk/Critical health transitions and critical alert generation/resolution enter Project Log.

### Workload formula

Workload is a deterministic, explicitly heuristic status rather than an hours-capacity forecast. For each project member, the backend counts non-archived assigned tasks excluding `DONE` and `CANCELLED`, overdue tasks, and tasks due within 14 days. It sums only stored estimated and actual effort. A zero estimate on any active task marks effort data incomplete; the service never substitutes hours.

The availability heuristic supplies one active-task slot per 20 availability percentage points, with a minimum of one slot when availability is positive. `HIGH` means an overdue task exists, active work exists at zero availability, or active task count exceeds slots. `MEDIUM` begins at 60% of slots, `LOW` is below that threshold, and `NO_DATA` means no active assigned tasks. Multiple assignees each receive the full task count and stored effort because the model does not yet capture effort allocation shares.

### Budget formula

Budget analytics use decimal arithmetic and are calculated only by the backend. `actual` is the sum of paid expenses, `committed` is the sum of pending expenses, and `planned expenses` is the sum of planned expenses. Cancelled expenses contribute zero everywhere. `forecast = actual + committed + planned expenses`; `remaining = budget - actual - committed`; `actual variance = budget - actual`; and `utilization = (actual + committed) / budget * 100`. Utilization is unavailable when the budget is zero.

Financial status is `NORMAL` below 75% utilization, `WARNING` from 75% through 90%, and `CRITICAL` above 90%. A zero budget produces `UNAVAILABLE` rather than an invented percentage. Category analytics use the same rules, uncategorized expenses remain visible as an explicit bucket, and the monthly trend groups expenses by their stored expense date and status.

### Risk formula and control workflows

Risk score is the integer product of stored probability and impact, each constrained from 1 through 5. Severity is `LOW` for 1–4, `MEDIUM` for 5–9, `HIGH` for 10–16, and `CRITICAL` for 17–25. The score and severity are derived by the backend and are not duplicated as mutable database fields.

Issues follow a forward-only operational workflow from open analysis and action states to resolved and closed. Resolution text is mandatory before resolution or closure. Change requests start as draft, are explicitly submitted, and may then be approved or rejected with mandatory rationale; only approved requests can be marked implemented. Cancellation is explicit. These transitions record audit events but never execute the requested change.

### Project memory and activity separation

The Project Log is the durable, human-facing memory of meaningful project context. Manual entries may link to same-project tasks, milestones, risks, issues, changes, meetings, and decisions through normalized link records. Automatic entries are intentionally limited to milestone completion, risk closure, issue resolution, change approval, meeting completion, and a decision becoming decided. They are written in the same transaction as the source mutation and are read-only.

Meetings reference project members through composite same-project constraints. Action items start as proposed and require explicit confirmation before completion; they never create tasks automatically, but may be linked to an existing same-project task. Decisions preserve their lifecycle instead of supporting hard deletion and may reference a meeting, decision maker, and normalized same-project entities.

Activity is a read-only projection of existing append-only audit events. It remains technically complete and exposes actor, action, entity, recorded changes, and a resolvable entity name where possible. Project Log and Activity are separate because user-relevant memory and implementation-level audit history have different purposes.

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
- work-planning empty/list/filter states, Kanban rendering and status persistence, milestone progress, task creation, and shared-state refresh behavior.
- team empty/create/add/edit flows, stakeholder list/matrix rendering, workload facts/incomplete-data display, and task assignment display/update behavior.
- finance dashboard totals and empty states, expense creation/filter behavior, and budget-category create/edit flows.
- exact risk severity boundaries, control ownership, cross-project and member protections, issue resolution, change decisions, audit events, risk-matrix rendering, normalized relationship forms, and decision validation.
- project-log chronology and links, meeting/action review states, decision history, meaningful automatic memory events, activity projection, overview signals, cross-project protection, and EN/IT memory navigation.
- KPI availability and formulas, every health dimension and threshold, weight redistribution, deterministic drivers, alert generation/deduplication/acknowledgement/resolution/reappearance, all predefined rule families, ownership isolation, portfolio aggregation, and bilingual intelligence rendering.

CI-ready commands run backend tests, frontend tests, TypeScript compilation, and the production frontend build. Each future feature must add tests near the business logic it introduces.

## 12. Docker and local development

`docker compose up --build` builds and starts the three required services. Compose waits for PostgreSQL health, runs migrations, and then starts FastAPI. The frontend development server proxies API calls to the backend, avoiding frontend knowledge of database or secret configuration.

AI tests mock provider execution and cover Gemini payload/usage parsing, timeout/authentication/rate-limit/malformed behavior, no-key startup, context selection and limits, prompt-injection separation, evidence validation, request bounds, audit metadata, authorization, cross-owner `404`, UI loading/error/unavailable/evidence states, follow-up history, and EN/IT labels. Normal tests never call Gemini; an optional single live smoke test is performed only when `GEMINI_API_KEY` is configured.

Account creation is an explicit operator action after startup:

```bash
docker compose exec backend python -m app.cli create-user
```

No migration or startup hook inserts business records.

## 13. Development phases

1. Foundation (complete): architecture, auth, shell, i18n, themes, migrations, AI boundary, Docker, tests.
2. Projects (complete): project ownership, creation wizard, objectives, criteria, archive workflow, audit events, and portfolio aggregation.
3. Work planning (complete): tasks, one-level subtasks, dependencies, milestones, deterministic progress, project overview metrics, and shared List/Kanban/Timeline data.
4. People (complete): reusable people, membership, roles, stakeholders, task assignees, workload analytics, and project overview signals.
5. Finance (complete): budgets, categories, expenses, deterministic analytics, thresholds, project overview signals, and audit events.
6. Control (complete): risks, deterministic scoring and matrix, issues, governed change requests, project overview signals, and audit events.
7. Project memory (complete): project log, meetings, reviewable action items, decisions, read-only activity, meaningful automatic entries, overview signals, and bilingual UI. Alerts and automation remain deferred.
8. Intelligence (complete): centralized KPIs, health and history, automatic alerts, predefined automation, overview/portfolio signals, audit/log integration, and bilingual UI.
9. AI foundation (complete): Gemini execution, provider-neutral service, deterministic context packages, structured evidence-grounded Project Assistant, safe failures, usage/audit metadata, and bilingual UI. Proactive insights, recommendations, scenarios, meeting AI, documents, and knowledge retrieval remain deferred.
10. Documents and delivery: retrieval, reports, validated import/export, notifications, and release hardening.

Each phase adds schema via migrations, implements use cases behind services, exposes typed APIs, and completes UI/empty/error states with tests.

## 14. Significant constraints and deferred choices

- There is no fake production data.
- There is no public registration in the personal first release.
- Gemini is optional and backend-only; without a key, core application startup and readiness remain healthy.
- No charting, Pandas, job queue, mail provider, object storage, or RAG dependency is added before a concrete use case exists.
- Kubernetes and microservices are outside V1.
- Hosted deployment is deferred; the required target is local Docker Compose.
