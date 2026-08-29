# Loris PMO

Loris PMO is a personal project management and project intelligence application. The repository includes the production-shaped foundation, Projects Core, Work Planning Core, People Core, Finance Core, Control Core, and Project Memory Core: secure authentication, owner-scoped projects and reusable people, objectives, success criteria, tasks, subtasks, milestones, dependencies, project membership, stakeholders, normalized task assignees, deterministic workload, budget, and risk analytics, shared List/Kanban/Timeline views, budget categories and expenses, risk and issue registers, governed change requests, project logs, meetings, action items, decisions, read-only activity, portfolio aggregation, versioned APIs, PostgreSQL migrations, bilingual UI, themes, testing, Docker Compose, and a provider-neutral AI boundary.

The remaining product areas described in `PROJECT_INTELLIGENCE_SPEC.md` are intentionally delivered incrementally rather than represented with fake functionality or sample production data.

## Projects, Work Planning, People, Finance, Control, and Project Memory Core

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
- use the application in English or Italian and in light or dark mode.

Archived projects remain available through the archive filter but are read-only. Project, objective, success-criterion, task, dependency, milestone, membership, assignment, stakeholder, budget, category, expense, risk, issue, change-request, log, meeting, action-item, and decision mutations create append-only audit events. Workload uses real task assignments and stored effort without inventing hours. Finance uses the project budget plus stored expense statuses: paid is actual, pending is committed, planned is forecast-only, and cancelled is excluded. Risk severity is derived from probability × impact. Earned value and generalized project health remain unavailable until their complete source domains are implemented.

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
