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

Decision: Model people independently from authentication users and relate them to projects through project memberships.

Reason: A resource may participate in multiple projects with different roles, responsibilities, and availability. Removing one membership must not destroy the reusable person record or turn project resources into login identities.

Decision: Support multiple task assignees through a normalized relation to project members.

Reason: Composite same-project foreign keys make cross-project assignments impossible at the database boundary, while normalized assignments remain compatible with List, Kanban, Timeline, workload analytics, and future reporting. Each member currently receives the full task effort because allocation shares are not part of V1.

Decision: Store stakeholders as project records that may optionally reference an owner-scoped person.

Reason: Known people can be reused without requiring every external stakeholder to become a team member, while standalone names still support matrix and communication tracking.

Decision: Make account-level audit events possible by allowing a nullable project reference.

Reason: Person creation is significant but may occur before project membership exists. Project mutations continue to record their project ID; only owner-level entity events omit it.

Decision: Use an availability-aware task-slot heuristic for workload rather than inventing weekly hours.

Reason: Availability percentage, task assignments, due dates, and stored effort exist, but time-phased capacity and effort allocation do not. One active-task slot per 20% availability yields a documented warning signal; overdue work and zero availability with active work are always high. Missing estimates are exposed explicitly instead of imputed.

Decision: Keep `projects.planned_budget` as the authoritative project budget and add normalized categories and expenses around it.

Reason: The project model already contains the product's budget value. Reusing it avoids duplicate sources of truth while categories provide an allocation breakdown and expenses preserve transaction-level history.

Decision: Derive all finance analytics from stored expense statuses with decimal arithmetic.

Reason: Paid expenses are actual, pending expenses are committed, planned expenses affect forecast only, and cancelled expenses are excluded. Centralizing the formulas in the backend keeps the dashboard, project overview, and future consumers consistent and avoids floating-point money errors.

Decision: Define financial status from actual plus committed utilization: warning at 75%, critical above 90%, and unavailable for a zero budget.

Reason: The thresholds provide deterministic early warning without conflating plans with commitments. A zero denominator cannot yield a meaningful utilization percentage and must not be represented as zero health risk.

Decision: Preserve expense history by making cancellation terminal and preventing deletion of categories referenced by expenses.

Reason: Financial records and their audit trail must remain explainable. Cancellation expresses business reversal without destructive deletion, while restricting category deletion keeps historical classifications valid.

Decision: Enforce optional expense category, task, and milestone links with composite same-project foreign keys.

Reason: Service ownership checks provide safe API behavior, and database constraints independently prevent cross-project financial associations.

Decision: Derive risk score as probability multiplied by impact and map fixed severity bands in one backend analytics function.

Reason: Probability and impact are the authoritative stored facts. Deriving score and severity prevents stale duplicated values and keeps API lists, the matrix, summaries, and future consumers consistent.

Decision: Normalize risk, issue, and change-request links to tasks, milestones, risks, and issues with composite same-project foreign keys.

Reason: Service validation provides clear errors while the database independently prevents cross-project associations. Optional risk and issue owners use project-member composite keys for the same protection.

Decision: Require forward-only issue transitions and explicit resolution text before resolved or closed states.

Reason: An issue history must remain explainable. Reopening and arbitrary state jumps are deferred until a deliberately modeled workflow and corresponding audit semantics exist.

Decision: Treat change requests as governed decisions, not automation instructions.

Reason: Submission, approval, rejection, implementation, and cancellation are explicit audited transitions. Approval records rationale but never silently changes tasks, dates, budgets, or resource assignments.

Decision: Keep the 5×5 risk matrix as a frontend projection of backend-derived severity and stored probability/impact.

Reason: The visual provides useful control context without introducing a second scoring implementation or mutable matrix state.

Decision: Separate meaningful Project Log memory from technical Activity audit history.

Reason: Audit events must remain append-only and implementation-complete, while the Project Log should stay concise and useful to project users. Only six meaningful domain transitions create automatic log entries, atomically with their source change.

Decision: Normalize polymorphic memory links and validate every target against the owning project service-side.

Reason: A compact link model supports tasks, milestones, risks, issues, changes, meetings, and decisions without duplicating near-identical tables. Composite database constraints still protect meeting participants, owners, task traceability, meeting references, and decision makers; service validation rejects every cross-project polymorphic link.

Decision: Keep meeting action items proposed until explicit confirmation and never create tasks automatically.

Reason: Meeting notes frequently contain tentative commitments. A proposed/confirmed/completed/dismissed lifecycle preserves human review, while an optional same-project task link provides traceability without hidden plan mutations.

Decision: Preserve decisions through lifecycle states instead of exposing hard deletion.

Reason: Proposed, decided, reversed, and superseded states retain the rationale and historical record required for project memory. A transition to decided creates the meaningful log entry; later reversal or supersession remains visible without rewriting history.

Decision: Centralize Sprint 8 facts, KPIs, health, alert reconciliation, and portfolio intelligence in one owner-scoped application service.

Reason: Dashboards and future AI context must consume the same deterministic truth. Existing workload, finance, and risk primitives are reused instead of duplicated in the frontend.

Decision: Weight health as Schedule 25, Budget 20, Tasks 20, Risks 15, Resources 10, and Objectives 10, excluding unavailable dimensions and redistributing their weights.

Reason: The documented fixed weights remain explainable while an empty source domain cannot silently behave like either zero health or perfect health. Objective progress is available only when applicable structured success criteria exist.

Decision: Persist alerts with one stable project/condition key and reactivate the same record after recurrence.

Reason: Stable reconciliation prevents alert duplication and fatigue, preserves first detection, supports acknowledgement, automatically resolves cleared conditions, and makes recurrence auditable. Reappearance resets acknowledgement so a renewed condition is visible.

Decision: Keep the eight V1 automation rules in an inspectable code registry and use explicit synchronous project recalculation.

Reason: The rules are product behavior, not production fixtures or a generic DSL. Explicit invocation handles date-driven conditions without Redis, Celery, or a scheduler and avoids hidden service cycles. The architecture can add a background trigger later without changing rules or alert persistence.

Decision: Store health history only when the score, status, dimensions, or drivers materially change.

Reason: Event-shaped history explains movement without writing a duplicate snapshot on every read. Only At Risk/Critical health transitions and critical alert lifecycle events enter the Project Log; lower-level changes remain in append-only audit history.
