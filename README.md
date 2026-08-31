# Loris PMO

Loris PMO is a personal project management and project intelligence application. The repository includes the production-shaped foundation through AI Insights and Recommendations: secure authentication; owner-scoped project, planning, people, finance, control, and memory records; deterministic KPIs and health; automatic alerts and automation rules; portfolio intelligence; question-relevant AI context packages; provider-neutral Gemini execution; evidence-grounded project Q&A; explicit proactive analysis; persistent, deduplicated AI insights and recommendations; human review history; bilingual UI; testing; and Docker Compose.

The remaining product areas described in `PROJECT_INTELLIGENCE_SPEC.md` are intentionally delivered incrementally rather than represented with fake functionality or sample production data.

## Project management and deterministic intelligence

An authenticated user can:

- create a project through a three-step wizard, including initial objectives and success criteria;
- view, search, filter, sort, edit, and archive only their own projects;
- maintain project objectives and success criteria;
- create tasks and one-level subtasks with validated dates, effort, priority, status, milestone, and completion data;
- connect project tasks with blocking, dependency, and related relationships while preventing scheduling cycles;
- create milestones whose progress is derived from their linked non-cancelled tasks;
- use the same persisted task data in searchable List, draggable Kanban, and date-based Timeline views;
- see real total, completed, overdue, upcoming-milestone, and deterministic task-progress metrics on a project;
- see real total, active, on-hold, and completed counts in the portfolio;
- create reusable people and add them to projects with roles, responsibilities, and availability;
- assign one or more valid project members to tasks and see them across planning views;
- manage linked or standalone stakeholders and inspect their influence/interest matrix;
- review backend-calculated workload counts, effort totals, incomplete-data indicators, and documented heuristic states;
- set a project budget, organize planned allocation into categories, and record planned, pending, paid, or cancelled expenses;
- review deterministic budget totals, utilization status, category breakdown, uncategorized spend, monthly trends, and recent expenses;
- assess risks with probability and impact, deterministic severity bands, owner and work links, mitigations, contingencies, and a 5×5 matrix;
- track issues through explicit analysis, action, resolution, and closure with schedule, budget, scope, and quality impacts;
- submit, approve, reject, implement, or cancel change requests with recorded rationale and no automatic mutation of project plans;
- preserve durable project context in a searchable chronological Project Log with normalized record links;
- plan and complete meetings with project-member participants and reviewable action items;
- confirm, complete, or dismiss meeting actions explicitly, with optional links to existing tasks;
- record decisions, rationale, impact, lifecycle history, and same-project links without hard deletion;
- inspect the existing append-only technical audit stream separately from meaningful Project Log memory;
- review centralized KPIs with explicit unavailable states instead of invented values;
- inspect Schedule, Budget, Tasks, Risks, Resources, and Objectives health dimensions with documented weighting and deterministic drivers;
- track meaningful health history without creating a snapshot on every read;
- review, filter, and acknowledge persistent automatic alerts that deduplicate, reactivate, and resolve from their underlying conditions;
- see health, overdue work, severe risks, critical issues, budget state, and active alerts across the portfolio;
- ask read-only project questions through a Gemini-backed assistant whose evidence references are validated against owner-scoped context;
- explicitly analyze deterministic alert/action candidates once per meaningful state, producing at most five evidence-validated insights and five recommendations;
- review persistent insights and recommendations with confidence, evidence, alternatives, freshness, and EN/IT presentation;
- accept, reject, ignore, or dismiss AI proposals without executing any operational project mutation;
- use the application in English or Italian and in light or dark mode.

Archived projects remain available through the archive filter but are read-only. Domain mutations and intelligence state changes create append-only audit events; only material health changes and critical alert transitions enter the human-facing Project Log. Workload uses real task assignments and stored effort without inventing hours. Finance uses the project budget plus stored expense statuses: paid is actual, pending is committed, planned is forecast-only, and cancelled is excluded. Risk severity is derived from probability × impact. Earned value remains unavailable because the required time-phased baseline does not exist.

## Project Assistant, Insights, and Gemini

The Project Assistant is available from AI Copilot and from each project overview. It uses deterministic backend facts and a bounded context package selected from the current question. Gemini receives only relevant records from that owned project; authentication data, credentials, unrelated projects, and raw audit internals are excluded. Model output is structured, and evidence references are resolved by the backend rather than trusted directly from the model.

Set the backend-only key in `.env` to enable real execution:

```bash
GEMINI_API_KEY=your-local-key
GEMINI_MODEL=gemini-3.6-flash
```

Optional conservative generation settings are `AI_TIMEOUT_SECONDS` (default `30`), `AI_MAX_OUTPUT_TOKENS` (default `4096` for the bounded Sprint 10 structured response), and `AI_TEMPERATURE`. The key is never returned to or configured by the frontend. If no key is present, the application and readiness checks remain healthy and the assistant shows a clear unavailable state.

Conversation history is not persisted in V1. The browser sends at most six recent messages for a follow-up, while audit events store only provider/model, success, latency, request category, selected sections, and provider usage counts when available. The assistant cannot mutate tasks, dates, budgets, assignments, alerts, risks, issues, or changes. Proactive analysis is never called on page load: an explicit Analyze Project action sends only deterministic candidate signals, reuses unchanged analysis by fingerprint, and persists backend-validated evidence rather than raw provider responses. Recommendation acceptance records agreement and project memory only; it executes no project change.

## Quick start with Docker

Requirements: Docker and Docker Compose.

```bash
cp .env.example .env
```

Replace `SECRET_KEY`, `POSTGRES_PASSWORD`, and the password inside `DATABASE_URL` with local values, then start the stack:

```bash
docker compose up --build
```

Create the first account in a second terminal. No account or business data is seeded automatically.

```bash
docker compose exec backend python -m app.cli create-user
```

Open [http://localhost:5173](http://localhost:5173). API documentation is available in development at [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

## Local development

Backend (Python 3.12+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend (Node.js 22+):

```bash
cd frontend
npm ci
npm run dev
```

## Tests and checks

```bash
cd backend
pytest
ruff check .
```

```bash
cd frontend
npm test
npm run build
```

The optional PostgreSQL integration check runs when `TEST_DATABASE_URL` is set. The normal Docker startup also verifies PostgreSQL readiness and applies all Alembic migrations before serving the API.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for system boundaries, security, data, AI, testing, Docker, and development-phase decisions. Significant choices are recorded in [`docs/DEVELOPMENT_LOG.md`](docs/DEVELOPMENT_LOG.md).

## Security notes

- Never commit `.env` or real credentials.
- The Gemini key is backend-only and optional.
- Authentication uses an HttpOnly token cookie and CSRF protection.
- Public registration is deliberately unavailable in the personal foundation release.

### Operational AI workspace

Sprint 11 adds user-triggered Daily Briefings, rolling seven-day Weekly Reviews, read-only Scenario Analysis, and an AI Meeting Assistant. AI outputs remain evidence-backed proposals: scenario runs never mutate the project, and meeting proposals create an operational record only after explicit per-item confirmation.

## V1 documents and data workspace

Each project now includes **Documents** and **Reports & data** workspaces. Documents are stored under the server-only `DOCUMENT_STORAGE_PATH` (10 MB default limit), extracted into bounded searchable chunks where supported, and can ground the existing read-only Project Assistant through validated evidence references. Reports are deterministic backend snapshots with PDF download; project datasets export to CSV/XLSX. Task and expense imports require a validation preview and explicit atomic confirmation.

Set `DOCUMENT_STORAGE_PATH=/app/data/documents` in Docker deployments; Compose provisions the persistent `document_data` volume. Image OCR, vector search, generic field-mapping imports, and custom report-template design are intentionally outside V1. See `docs/V1_FEATURE_AUDIT.md` for the complete release audit.
