# Loris PMO v1.0.0

Release date: 2026-08-31  
Status: V1

Loris PMO v1.0.0 is the first complete local release of the private project management and project intelligence application.

## Highlights

- Connected project, portfolio, delivery, people, finance, control, memory, and intelligence workspaces
- Deterministic backend facts and health analytics rather than frontend or model-authored calculations
- Evidence-grounded Gemini assistance with explicit human review boundaries
- Private project documents, lexical knowledge retrieval, reporting, and controlled data portability
- Reproducible local startup with Docker Compose and PostgreSQL migrations

## Project management

- Multi-project portfolio, three-step project setup, objectives, and success criteria
- Tasks, one-level subtasks, dependencies, milestones, List, Kanban, and Timeline
- Team members, stakeholders, task assignments, and workload warnings
- Budget categories, expenses, forecasts, and financial status
- Risks, 5×5 matrix, issues, and governed change requests
- Project Log, meetings, action items, decisions, and Activity history

## Intelligence

- Deterministic KPIs and six weighted health dimensions with missing-data handling
- Material health history and explanatory drivers
- Eight predefined alert/automation rule families with deduplication, acknowledgement, reactivation, and resolution
- Portfolio-level health, schedule, budget, risk, issue, and alert signals

## AI

- Provider-neutral AI service using Gemini Interactions REST API and `gemini-3.6-flash`
- Structured Project Assistant responses with backend-resolved evidence
- Persistent insights and proposals with fingerprint-based freshness control
- Daily Briefing, rolling seven-day Weekly Review, read-only Scenario Analysis, and Meeting Assistant
- No tools, fallback models, automatic retries, or autonomous project mutation
- Recommendation acceptance records agreement only; meeting proposals require individual confirmation

## Documents and knowledge

- Private configurable storage with generated paths, upload limits, and owner/project isolation
- Bounded PDF, DOCX, XLSX, CSV, and TXT extraction
- Image storage with extraction explicitly unavailable; no implied OCR
- Deterministic overlapping chunks, lexical top-five retrieval, and document-grounded evidence

## Reports and data

- Project, Executive, Weekly, Budget, Control, and Team reports
- Server-rendered PDF reports and CSV/XLSX dataset export
- CSV/XLSX/JSON task and expense import with validation, preview, confirmation, audit, and atomic persistence

## Security

- Operator-created accounts; no public registration or default credentials
- Argon2 passwords, HttpOnly authentication cookie, double-submit CSRF, and environment-aware secure cookies
- Server-side owner/project checks plus database constraints for sensitive relationships
- Safe error envelopes, request IDs, private document paths, backend-only API keys, and untrusted-document prompt boundaries
- No production demo data and no persisted unrestricted AI payloads

## Technical foundation

- Python/FastAPI/SQLAlchemy/Alembic backend
- React/TypeScript/Vite bilingual frontend
- PostgreSQL 17, Docker Compose health checks, automatic migration startup, and named data volumes
- Backend, PostgreSQL, frontend, artifact, ownership, AI-contract, and security-focused test coverage
- Safe local start/status/stop and backup/restore procedures

## Known limitations

- Single-owner private workspace; no collaboration or RBAC
- Local document volume; no cloud object storage
- Lexical retrieval instead of semantic/vector search
- No image OCR
- Fixed report catalog and task/expense import templates
- No hosted deployment
- Non-blocking frontend bundle-size advisory and accepted historical Alembic metadata drift
