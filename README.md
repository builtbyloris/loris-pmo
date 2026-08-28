# Loris PMO

Loris PMO is a personal project management and project intelligence application. The repository includes the production-shaped technical foundation plus the Projects Core: secure authentication, owner-scoped projects, objectives and success criteria, portfolio aggregation, versioned APIs, PostgreSQL migrations, bilingual UI, themes, testing, Docker Compose, and a provider-neutral AI boundary.

The remaining product areas described in `PROJECT_INTELLIGENCE_SPEC.md` are intentionally delivered incrementally rather than represented with fake functionality or sample production data.

## Projects Core

An authenticated user can:

- create a project through a three-step wizard, including initial objectives and success criteria;
- view, search, filter, sort, edit, and archive only their own projects;
- maintain project objectives and success criteria;
- see real total, active, on-hold, and completed counts in the portfolio;
- use the application in English or Italian and in light or dark mode.

Archived projects remain available through the archive filter but are read-only. Project, objective, and success-criterion mutations create append-only audit events. Planned-versus-actual, earned-value, and health metrics remain unavailable until their source domains are implemented.

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
