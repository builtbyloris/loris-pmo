# Development log

## 2026-08-28

Decision: Use a modular monolith split into a React frontend, FastAPI backend, and PostgreSQL database.

Reason: It preserves domain boundaries and future scalability without premature distributed-system complexity.

Decision: Use SQLAlchemy 2 async sessions and Alembic migrations.

Reason: They provide explicit transactional persistence and reproducible PostgreSQL schema evolution.

Decision: Use an HttpOnly JWT cookie with double-submit CSRF protection and Argon2 password hashing.

Reason: The browser does not store bearer credentials in JavaScript-accessible storage, while backend validation protects state-changing requests.

Decision: Do not provide public registration or seed an initial account.

Reason: The initial product is personal/private, and explicit CLI account creation avoids default credentials and production seed data.

Decision: Keep AI behind `AIService` and an `AIProvider` protocol; make configuration optional.

Reason: Core project management must remain available without Gemini, and providers must be replaceable.

Decision: Defer Pandas, charting, task queues, email providers, and document infrastructure.

Reason: The foundation has no concrete workload requiring them; deferral keeps the dependency and operational footprint small.

Decision: Scope every project query and mutation by the authenticated owner's user ID and return `404` for cross-owner identifiers.

Reason: Ownership is enforced in the repository/service boundary, prevents identifier enumeration, and is ready for multi-user use without changing the project schema.

Decision: Archive projects with an `archived_at` timestamp and terminal `ARCHIVED` status instead of deleting them.

Reason: Project history and future reporting need stable identifiers. Archived records are excluded from normal listings and portfolio counts and become read-only.

Decision: Persist append-only audit events in the same transaction as project, objective, and success-criterion mutations.

Reason: Atomic audit recording preserves a trustworthy history without allowing a successful domain mutation to outlive its corresponding event.

Decision: Keep portfolio metrics limited to counts supported by Projects Core data.

Reason: Budget variance, earned value, health, schedule, and progress metrics require finance and work-planning sources that do not exist yet; presenting them would imply unsupported calculations.
