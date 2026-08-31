# Loris PMO

Loris PMO is a private, professional-grade project management and project intelligence application. It combines operational project control, deterministic analytics, and evidence-backed AI assistance in one owner-scoped workspace.

**Release:** v1.0.0 · **Status:** V1 · **Release date:** 2026-08-31

## Overview

The application helps a project manager understand what is happening, what changed, what is late or at risk, how finances and workload are evolving, and what deserves attention next. PostgreSQL remains the factual source of truth. Backend services calculate authoritative metrics; Gemini interprets bounded evidence and proposes options; the user remains the decision maker.

The repository is a modular monolith designed for reliable local operation with Docker Compose. It starts empty: no account, project, task, expense, or other business fixture is created automatically.

## Key features

- Multi-project portfolio, project lifecycle, objectives, and success criteria
- Tasks, subtasks, dependencies, milestones, List, Kanban, and Timeline views
- Reusable people, project roles, stakeholders, task assignees, and workload signals
- Budget categories, expenses, deterministic analytics, and forecasts
- Risks with a 5×5 matrix, issues, and governed change requests
- Project Log, meetings, action items, decisions, and append-only activity history
- KPIs, weighted health dimensions, health history, alerts, and deterministic automation
- Evidence-grounded Project Assistant, persistent insights, and recommendations
- Daily Briefing, rolling seven-day Weekly Review, read-only scenarios, and Meeting Assistant
- Project documents, bounded extraction, lexical knowledge retrieval, and document evidence
- Six deterministic reports, PDF output, CSV/XLSX export, and validated task/expense import
- English/Italian localization and light/dark presentation

The evidence-backed scope and V1 boundaries for all 33 official product areas are recorded in [the V1 feature audit](docs/V1_FEATURE_AUDIT.md).

## AI philosophy

AI is a copilot, not the project manager.

- Backend data and deterministic calculations are authoritative.
- Gemini receives bounded, owner-scoped context through a provider-neutral interface.
- AI interprets, summarizes, simulates, extracts proposals, and recommends; it does not receive database tools or autonomous actions.
- Model evidence identifiers are accepted only when they resolve through a backend-owned catalog.
- Recommendations record agreement or rejection but do not execute project changes.
- Meeting proposals become operational records only after explicit item-level confirmation and backend validation.
- Prompt and response content is not written to technical audit logs; only safe provider/model/usage metadata is retained.

## Tech stack

| Area | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, asyncpg |
| Database | PostgreSQL 17 in Docker Compose |
| Frontend | React 19, TypeScript, Vite, React Router, i18next |
| AI | Provider-neutral service, Gemini Interactions REST API, structured JSON |
| Documents/data | pypdf, python-docx, openpyxl, ReportLab |
| Testing | Pytest, HTTPX, Vitest, React Testing Library, Ruff |
| Infrastructure | Docker Compose |

## Architecture

Loris PMO is a modular monolith:

```text
React + TypeScript
        ↓
FastAPI API
        ↓
Application services
        ↓
Deterministic domain logic / provider-neutral AI
        ↓
PostgreSQL + private document storage
```

See [Architecture](docs/ARCHITECTURE.md) for domain boundaries, security controls, AI flows, storage, and decisions. See [Development Log](docs/DEVELOPMENT_LOG.md) for the rationale behind significant implementation choices.

## Portfolio positioning

This project demonstrates end-to-end product engineering rather than a thin AI chat interface: typed API design, relational modeling and migrations, owner/project security boundaries, deterministic financial and schedule logic, responsive frontend application development, human-in-the-loop AI, prompt/evidence safety, transactional imports, generated reports, automated tests, and reproducible local infrastructure.

For a concise walkthrough, use the [5–10 minute demo flow](docs/DEMO_FLOW.md).

## Screenshots

No fabricated screenshots are committed. The repository contains a [screenshot capture plan](docs/SCREENSHOT_PLAN.md) and a tracked [screenshots directory](docs/screenshots/README.md) for real V1 captures:

1. Portfolio Dashboard
2. Project Overview and health
3. Task Kanban and Timeline
4. Finance Dashboard
5. Risk and control workspace
6. AI Copilot
7. Daily Briefing
8. Scenario Analysis
9. Documents and knowledge retrieval
10. Reports and data portability

## Local setup

Requirements: Docker Desktop (or Docker Engine with Compose v2), Git, and available ports `5173`, `8000`, and `5432`.

```bash
git clone <your-repository-url>
cd <repository-directory>
cp .env.example .env
```

Replace the placeholder `SECRET_KEY`, `POSTGRES_PASSWORD`, and database password in `DATABASE_URL`. `SECRET_KEY` must contain at least 32 characters. Optionally set `GEMINI_API_KEY`; the core application and deterministic reports work without Gemini.

Start the stack:

```bash
./scripts/start.sh
```

Equivalent direct command:

```bash
docker compose up -d --build
```

The backend waits for PostgreSQL health, applies Alembic migrations, and then serves the API. Open:

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend health: [http://localhost:8000/health](http://localhost:8000/health)
- Development API docs: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

Use `./scripts/status.sh` to inspect health and `./scripts/stop.sh` to stop services without deleting data.

## Account creation

No default account or password exists. After startup, create an account interactively:

```bash
docker compose exec backend python -m app.cli create-user
```

You may supply only the email argument; the password is still entered securely without terminal echo:

```bash
docker compose exec backend python -m app.cli create-user --email you@example.test
```

Never put real credentials in source files, command history, screenshots, or documentation.

## Environment variables

Copy `.env.example` to the ignored `.env` file and replace every credential placeholder. Important settings include:

- `SECRET_KEY`: JWT signing secret, minimum 32 characters
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`: local PostgreSQL configuration
- `FRONTEND_URL`: allowed browser origin
- `GEMINI_API_KEY`: optional, backend-only Gemini credential
- `GEMINI_MODEL`: defaults to `gemini-3.6-flash`
- `AI_TIMEOUT_SECONDS`, `AI_MAX_OUTPUT_TOKENS`, `AI_TEMPERATURE`: centralized bounded generation controls
- `DOCUMENT_STORAGE_PATH`, `DOCUMENT_MAX_UPLOAD_MB`: private storage location and upload limit

Do not commit `.env`. `.env.example` contains placeholders only.

## Running tests

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
```

Optional live PostgreSQL connectivity test:

```bash
TEST_DATABASE_URL='postgresql+asyncpg://<user>:<password>@localhost:5432/<database>'   pytest -q tests/test_postgres_connection.py
```

Frontend:

```bash
cd frontend
npm ci
npm test
npx tsc --noEmit
npm run build
```

Release checks are listed in [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

## Backup and restore

Create a timestamped PostgreSQL dump and document-storage archive:

```bash
./scripts/backup.sh
```

Restore requires an explicit dump path, confirmation, and optionally its matching document archive:

```bash
./scripts/restore.sh backups/loris-pmo-<timestamp>.dump   backups/loris-pmo-documents-<timestamp>.tar.gz
```

The restore operation is destructive to current local data and creates pre-restore safety backups. Read [Backup and Restore](docs/BACKUP_RESTORE.md) before using it.

`docker compose down` is safe for persisted data. **`docker compose down -v` deletes the local PostgreSQL and document volumes and is destructive.**

## Demo and portfolio material

- [Demo flow](docs/DEMO_FLOW.md)
- [Optional isolated demo-data guide](docs/DEMO_DATA_GUIDE.md)
- [Screenshot plan](docs/SCREENSHOT_PLAN.md)
- [Manual acceptance checklist](docs/MANUAL_ACCEPTANCE_CHECKLIST.md)
- [V1 release notes](docs/RELEASE_NOTES_V1.md)

Demo records never run at startup. The recommended demo uses a separate Compose project and disposable volumes so normal local data remains untouched.

## Project status

**v1.0.0 — Complete with documented non-blocking limitations.**

The authoritative release value is `backend/app/version.py`; FastAPI and `/health` expose it safely. The repository is not tagged or published automatically.

## Known V1 limitations

- Single authenticated owner; no multi-user collaboration or RBAC
- Local named-volume document storage; no cloud object storage
- Deterministic lexical document retrieval; no vector search
- Image storage without OCR
- Six fixed report types without a report designer
- Task and expense import templates only
- Local Docker Compose operation; no cloud deployment

Additional accepted boundaries are documented in the [V1 feature audit](docs/V1_FEATURE_AUDIT.md).

## Roadmap

Possible post-V1 work includes cloud deployment, invitations and RBAC, object storage, semantic retrieval, integrations, advanced report design, deeper scheduling, and optional OCR. These are roadmap possibilities, not implemented V1 capabilities.

## License

This is currently a private personal project. No open-source license has been granted; all rights are reserved unless the owner explicitly chooses a license later.
