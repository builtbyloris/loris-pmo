# Loris PMO

Loris PMO is a professional-grade project management and project intelligence platform. It combines operational project control, deterministic analytics, multi-user collaboration, advanced scheduling, and evidence-backed AI assistance in a secure role-based workspace.

This public GitHub repository contains the stable **v1.0.0** release on `main` and unreleased V2 development on `v2-development`. The current development milestone is **V2.5 Cloud & Production Readiness**. No `v2.0.0` release or tag exists.

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

### V2 development

V2 development is available on `v2-development` and has not been released as `v2.0.0`.

**V2.1 — Multi-user, RBAC & Collaboration**

- Multi-user project membership with centralized server-side RBAC
- `OWNER`, `PROJECT_ADMIN`, `PROJECT_MANAGER`, `CONTRIBUTOR`, and `VIEWER` roles
- Project comments, in-app notifications, and actor-aware activity
- Permission-aware finance, documents, reports, exports, and AI context

**V2.2 — Advanced Scheduling**

- Recursive finish-to-start dependency propagation
- Deterministic Critical Path Method with total and free float
- Explicit schedule baselines and signed schedule variance
- Milestone and project-deadline impact calculations
- Non-mutating preview followed by explicit transactional apply
- Schedule-fingerprint protection against stale previews
- Scenario Analysis reuse of the same deterministic scheduling engine

**V2.3 — AI & Knowledge 2.0**

- Provider-neutral Gemini embedding boundary with bounded batch indexing
- Project- and permission-scoped semantic retrieval over document chunks
- Deterministic Reciprocal Rank Fusion for hybrid lexical + semantic ranking
- Content-hash/model/version reuse, explicit reindexing, and deletion cleanup
- Multi-document grounded Q&A and structured document comparison
- Backend-owned document evidence with page/sheet/section metadata where available
- Lexical fallback when embeddings are unavailable or fail
- Prompt-injection-resistant document context and retrieval diagnostics

**V2.4 — Integrations**

- User-owned OAuth connections for Google and GitHub with encrypted server-side tokens
- Read-only Google Calendar browsing and explicit Meeting import with preview/confirm
- Bounded Gmail search and explicit private, project, or finance-scoped message links
- Read-only GitHub repository, issue, pull-request, and commit browsing with explicit task links
- Provider-neutral adapters, manual refresh, safe reauthorization/failure states, and preserved local records
- Project membership, RBAC, account isolation, audit history, and prompt-injection-safe external evidence

**V2.5 — Cloud & Production Readiness**

- Fail-closed development/test/production configuration and safe configuration check
- Secure production cookies, exact CORS, trusted hosts, security headers, and request correlation
- Managed-PostgreSQL pool/TLS configuration with explicit one-off migration workflow
- Provider-neutral private document storage with local and S3-compatible adapters
- Static production frontend and non-root backend images while preserving local Compose
- Local/cloud backup guidance, optional dated zero-cost deployment plan, and build/test CI

V2.1–V2.5 are technically complete on the unreleased development branch. The three final production logging/configuration blockers were fixed and runtime-validated; see the [V2 feature audit](docs/V2_FEATURE_AUDIT.md). No cloud deployment, merge, release, or `v2.0.0` tag has been created.

## AI philosophy

AI is a copilot, not the project manager.

- Backend data and deterministic calculations are authoritative.
- Gemini receives bounded, permission-aware context through a provider-neutral interface.
- AI context follows server-side project membership and RBAC rules and cannot bypass domain permissions.
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
| AI | Provider-neutral generation/embedding services, Gemini REST APIs, structured JSON |
| Documents/data | pypdf, python-docx, openpyxl, ReportLab |
| Testing | Pytest, HTTPX, Vitest, React Testing Library, Ruff |
| Infrastructure | Local Docker Compose, production container references, GitHub Actions CI |

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

See the [V2 roadmap](docs/V2_ROADMAP.md) and [Architecture](docs/ARCHITECTURE.md) for domain boundaries, security controls, AI flows, storage, and decisions. See [Development Log](docs/DEVELOPMENT_LOG.md) for the rationale behind significant implementation choices.

## Portfolio positioning

This project demonstrates end-to-end product engineering rather than a thin AI chat interface: typed API design, relational modeling and migrations, project membership, centralized RBAC, permission-aware AI and data access, deterministic financial analytics, advanced deterministic scheduling, permission-aware hybrid retrieval, responsive frontend application development, human-in-the-loop AI, prompt/evidence safety, transactional imports, generated reports, automated tests, and reproducible local infrastructure.

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
docker compose exec backend python -m app.cli create-user --email you@example.com
```

Never put real credentials in source files, command history, screenshots, or documentation.

## Environment variables

Copy `.env.example` to the ignored `.env` file and replace every credential placeholder. Important settings include:

- `SECRET_KEY`: JWT signing secret, minimum 32 characters
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`: local PostgreSQL configuration
- `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `TRUSTED_HOSTS`: browser and host boundaries
- `DATABASE_SSL_MODE` and pool settings: managed PostgreSQL transport/capacity controls
- `GEMINI_API_KEY`: optional, backend-only Gemini credential
- `GEMINI_MODEL`: defaults to `gemini-3.6-flash`
- `AI_TIMEOUT_SECONDS`, `AI_MAX_OUTPUT_TOKENS`, `AI_TEMPERATURE`: centralized bounded generation controls
- `DOCUMENT_STORAGE_BACKEND`, `DOCUMENT_STORAGE_PATH`, `DOCUMENT_MAX_UPLOAD_MB`: private storage mode/location/limit
- `S3_*`: optional backend-only S3-compatible object-storage configuration
- `INTEGRATION_TOKEN_ENCRYPTION_KEY`: dedicated Fernet key for OAuth token encryption at rest
- Google/GitHub OAuth client, redirect, and scope settings: optional; integrations stay unavailable when absent

Do not commit `.env`. `.env.example` contains placeholders only.

Provider setup, redirect URI, scope, encryption-key rotation, disconnect, and recovery guidance is in [Integrations](docs/INTEGRATIONS.md). Production deployment and configuration are documented in [Production operations](docs/PRODUCTION.md); the optional non-SLA example is in [Zero-cost cloud deployment](docs/CLOUD_FREE_DEPLOYMENT.md).

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

**Stable:** `v1.0.0` — released and stable on `main`.

**Development:** V2 is in progress on `v2-development`.

**Milestones:**

- ✅ V2.1 Multi-user / RBAC / Collaboration
- ✅ V2.2 Advanced Scheduling
- ✅ V2.3 AI & Knowledge 2.0
- ✅ V2.4 Integrations
- ✅ V2.5 Cloud & Production Readiness

V2 has not been released as `v2.0.0`. The authoritative runtime release value remains `backend/app/version.py` at `1.0.0`; V2 development intentionally does not create or move release tags.

## Stable V1 limitations

- V1 uses a single-owner workspace without multi-user RBAC; V2.1 addresses this on the unreleased development branch
- V1 provides the original task dependency and Timeline behavior; V2.2 adds advanced deterministic scheduling on the unreleased development branch
- Local named-volume document storage; no cloud object storage
- Deterministic lexical document retrieval; no vector search
- Image storage without OCR
- Six fixed report types without a report designer
- Task and expense import templates only
- Local Docker Compose operation; no cloud deployment

Additional accepted boundaries are documented in the [V1 feature audit](docs/V1_FEATURE_AUDIT.md).

## Current V2 development limitations

- No ownership transfer
- No outbound email invitations
- No realtime or WebSocket collaboration
- Finish-to-start scheduling dependencies only
- Calendar-day scheduling; no holiday or business calendar
- No resource leveling or automatic resource assignment
- No drag-and-drop scheduling
- Semantic vectors use bounded PostgreSQL-compatible JSON storage and application-side ranking; no dedicated vector index or external vector database
- Embedding and reindex work is synchronous; no background indexing queue
- No realtime provider push/webhook synchronization; integrations use explicit bounded refresh
- No cloud deployment is performed by the repository; deployment remains optional and operator-controlled
- Free-tier cloud examples have quotas, sleep/cold starts, changing terms, and no SLA
- No automatic cloud backup, local/cloud synchronization, or automatic local-to-S3 migration
- Rate/request-size limiting is delegated to the trusted production gateway

## Roadmap

- ✅ V2.1 — Multi-user, RBAC & Collaboration
- ✅ V2.2 — Advanced Scheduling
- ✅ V2.3 — AI & Knowledge 2.0
- ✅ V2.4 — Integrations
- ✅ V2.5 — Cloud & Production Readiness

See [V2_ROADMAP.md](docs/V2_ROADMAP.md) and the evidence-backed [V2 feature audit](docs/V2_FEATURE_AUDIT.md). V2 is technically complete but remains unreleased; release actions require explicit approval.

## License

This repository is publicly viewable for portfolio and demonstration purposes.

No open-source license has been granted. Unless explicitly stated otherwise, all rights are reserved.
