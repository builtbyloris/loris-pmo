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

## 2026-08-29

Decision: Model tasks, milestones, and dependencies as project-owned records with composite same-project foreign keys.

Reason: Ownership checks remain explicit at the service boundary while database constraints prevent cross-project parent, milestone, or dependency relationships even if a future caller bypasses application validation.

Decision: Support one level of subtasks and archive tasks with `archived_at`.

Reason: One level covers the current planning need without introducing tree-maintenance complexity. Archiving preserves identifiers, dependency history, and auditability.

Decision: Derive milestone and project task progress as the arithmetic mean of completion percentages for non-cancelled tasks; return unavailable when no eligible tasks exist.

Reason: A single deterministic rule avoids conflicting stored progress and does not invent values for empty plans. Effort-weighted and earned-value calculations remain deferred until their prerequisite domains are available.

Decision: Normalize scheduling semantics for validation while preserving the user-facing dependency type.

Reason: `A BLOCKS B` and `B DEPENDS_ON A` represent the same directed scheduling edge. Treating them equivalently prevents semantic duplicates and cycles; `RELATED_TO` remains non-directional and is excluded from cycle analysis.

Decision: Keep List, Kanban, Timeline, and Milestones as projections of one frontend work-planning state.

Reason: A Kanban mutation persists through the API and refreshes the shared state, ensuring every view reflects the database rather than maintaining divergent client models. Optimistic status changes roll back on failure.

Decision: Defer Timeline drag/resize, editable dependency lines, and critical-path analysis.

Reason: The V1 timeline is useful with real task bars, milestone markers, dates, dependency counts, and completion state. More advanced scheduling interactions should be added only with reliable persistence, rollback, and calculation behavior.
