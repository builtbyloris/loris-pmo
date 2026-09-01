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

## 2026-08-30

Decision: Extend the existing `AIService` and `AIProvider` boundary with an isolated Gemini REST adapter instead of adding a provider SDK or a parallel AI architecture.

Reason: The existing provider-neutral seam already enforces the intended dependency direction. A small HTTP adapter supports structured output, timeouts, safe error mapping, and usage metadata with one maintainable runtime dependency while keeping Gemini details outside routes and application services.

Decision: Build question context deterministically from owner-scoped project data with fixed topic selection, ordering, and per-section limits.

Reason: Sending every project record would increase privacy exposure, latency, and prompt noise. Keyword selection is explainable and does not require another model call; existing intelligence, finance, workload, and planning services remain the source of calculated facts.

Decision: Accept only model evidence reference strings and resolve them through a backend-owned context catalog.

Reason: Schema-constrained JSON ensures a stable transport contract, but a model can still invent identifiers. Dropping references absent from the exact context package prevents fabricated evidence details from being presented as verified project sources.

Decision: Keep Project Assistant conversations stateless and limited to six recent messages in V1.

Reason: Short in-memory continuity supports useful follow-ups without adding generic chat persistence, a migration, retention policy, or storage of sensitive prompts. It leaves room for deliberately project-scoped conversation persistence later.

Decision: Store only high-level AI usage metadata in the existing append-only audit stream and do not create Project Log entries for chat.

Reason: Provider, model, success, latency, request topics, context sections, safe failure code, and available token counts support observability without persisting prompt/response content. Ordinary questions are technical usage, not meaningful project history.

Decision: Keep Sprint 9 strictly read-only.

Reason: The provider receives no database session or tools, the API exposes only status and chat, and no model output can invoke operational mutations. Recommendations, proposals, confirmation workflows, proactive insights, scenarios, meeting assistance, documents, and knowledge retrieval remain explicit future work.

Decision: Treat project text as untrusted data through prompt separation and architectural capability limits.

Reason: Central system instructions label project content as data, but security does not depend on the prompt alone. Owner-scoped retrieval, no tools, no database access, bounded context, validated evidence, input limits, and React text rendering remain effective even if a stored task or log contains prompt-injection text.


## 2026-08-30 — Sprint 10

Decision: Build proactive analysis as a new application use case over the existing `AIProvider` protocol and `ProjectContextBuilder`, not as a parallel AI stack.

Reason: Deterministic intelligence remains factual truth, while the verified Gemini Interactions adapter is reused only for bounded interpretation. The model receives no session, tools, credentials, or operational mutation capability.

Decision: Select candidates deterministically from active alert conditions and unresolved meeting actions before calling Gemini.

Reason: Candidate selection is explainable, bounded, owner-scoped, and already covers schedule, milestones, budget, risks, issues, workload, health, and action-item pressure. Gemini never scans the full database blindly.

Decision: Store backend-resolved evidence snapshots and reject an entire output item if any supplied reference is unknown or belongs outside its candidate.

Reason: Persisted presentation remains stable and independently verifiable without storing raw provider payloads or trusting model-authored labels, identifiers, or facts.

Decision: Use a 0.0–1.0 confidence value with Pydantic and database bounds.

Reason: The value communicates the model's evidence-based judgment without presenting mathematical certainty. The UI explains that boundary.

Decision: Suppress unchanged analysis with a deterministic candidate-set fingerprint and reuse stable per-signal insight/recommendation fingerprints.

Reason: Explicit user invocation remains the only trigger, while unchanged state avoids unnecessary cost. Cleared signals resolve active insights and expire pending recommendations; dismissed and reviewed records preserve human history.

Decision: Treat recommendation acceptance as agreement only.

Reason: Accept/reject/ignore are explicit forward-only human decisions. Acceptance creates audit and concise Project Log history but no task, milestone, date, budget, assignment, alert, risk, issue, or change-request mutation.

Decision: Set the bounded Gemini model output budget to 4096 tokens for Sprint 10 structured analysis.

Reason: A live 1200-token interaction returned `incomplete` while already containing partial model output. The analysis contract permits up to five insights and five recommendations with evidence, confidence, impact, and alternatives. The current model-based Interactions request therefore uses the documented `generation_config.max_output_tokens` field; `max_total_tokens` applies to agent runs. The 4096-token default remains below the existing 8192-token safety ceiling, preserves environment override support, and does not permit partial responses, retries, tools, or operational mutations.

Decision: Use a 30-second production Gemini provider timeout for bounded Sprint 10 analysis.

Reason: With the 4096-token output cap, the final controlled interaction completed in 11.302 seconds and used 465 output tokens plus 875 thought tokens, while an earlier equivalent validation exceeded the previous 20-second cutoff. Thirty seconds provides a measured latency margin without retaining the temporary 60-second diagnostic timeout or adding retries.

## 2026-08-31 — Sprint 11: operational AI

- Added persistent daily briefing, weekly review, scenario result, meeting analysis, and meeting proposal models with Alembic revision `20260831_0011`.
- Reused deterministic Sprint 8/10 intelligence and backend-owned evidence for bounded briefing candidates, rolling seven-day facts, and scenario simulations.
- Added explicit meeting proposal confirmation/rejection. No operational entity is created during analysis; confirmation creates exactly one validated entity and records audit/Project Log history.
- Added AI workspace views for Daily Briefing, Weekly Review, and Scenario Analysis, plus the meeting assistant in completed meeting cards.
- Added EN/IT localization and focused backend/frontend tests.
- Gemini remains `gemini-3.6-flash` through the existing Interactions API with the centralized 30-second timeout and 4096-token output budget. No retries, fallback models, tools, or autonomous execution were added.

## 2026-08-31 — Sprint 12: V1 documents, knowledge, reporting and portability

- Added project document metadata, bounded extracted chunks, and validated import batches in Alembic revision `20260831_0012`.
- Added configurable local document storage with a Docker named volume, generated storage keys, containment checks, upload limits, and no storage-path exposure.
- Added bounded PDF/DOCX/XLSX/CSV/TXT extraction; images remain downloadable but explicitly unavailable for text retrieval without OCR.
- Added deterministic lexical project-document retrieval and backend-owned document evidence integration in the existing Project Assistant.
- Added six deterministic report types, server-rendered PDF, CSV/XLSX project exports, and audited generation.
- Added preview/validate/confirm import for task and expense CSV/XLSX/JSON templates with all-or-nothing persistence.
- Added EN/IT Documents and Reports & Data workspaces and project-overview navigation.
- Added `docs/V1_FEATURE_AUDIT.md` covering all 33 official product features and honest V1 boundaries.

## 2026-08-31 — Sprint 13: V1 release and portfolio readiness

Decision: Establish `backend/app/version.py` as the authoritative v1.0.0 release source and expose it through FastAPI/OpenAPI and the safe liveness response.

Reason: Reviewers and operators need one inspectable release identity without introducing a new settings surface or duplicating runtime version logic. Hatch reads the same source for backend packaging; the private frontend manifest mirrors the release for build metadata.

Decision: Replace sprint-history-oriented onboarding with a portfolio README, real screenshot checklist, concise demo flow, GitHub-ready release notes, and an auditable release/manual-acceptance checklist.

Reason: V1 is functionally complete. Release material must explain the architecture, human-in-the-loop AI boundaries, actual capabilities, and accepted limitations without implying unimplemented cloud, collaboration, OCR, vector, or reporting features.

Decision: Keep demo data manual and isolated in a separately named Compose project.

Reason: No production/startup seed path is introduced. A reviewer can build one coherent project for screenshots, then remove only the explicitly named disposable volumes without contaminating the ordinary workspace.

Decision: Add transparent start, status, stop, PostgreSQL/document backup, and confirmed restore helpers.

Reason: Local operational reliability benefits from repeatable commands, but scripts must preserve volumes by default, use container-owned database configuration without printing credentials, validate artifacts, create pre-restore safety backups, and never silently replace current data.

Decision: Require an explicit database URL instead of retaining the early local password fallback.

Reason: Docker and tests already provide a database URL. Failing closed when configuration is absent removes a credential-shaped default without changing any configured database behavior.

Decision: Retain private-project licensing status and defer tagging/publishing.

Reason: No open-source license should be inferred. The `v1.0.0` tag and GitHub release remain explicit owner actions after the final visual/manual acceptance pass.

Final V1 status: functionally complete with documented non-blocking limitations; Sprint 13 introduces no new product feature, migration, AI capability, or provider call.


## 2026-09-01 — V2.1 multi-user, RBAC, and collaboration foundation

Decision: Introduce `ProjectMembership` as a new authenticated-access relationship and preserve `Person` plus operational `ProjectMember` unchanged.

Reason: Authentication identity, reusable people/resource data, delivery participation, and authorization are different concerns. Optional same-project mapping supports a real human occupying both roles without forcing every user to be a resource or every resource to log in.

Decision: Preserve `projects.owner_user_id`, backfill one immutable OWNER membership per existing project, and defer ownership transfer.

Reason: This gives V1 data a lossless forward migration, retains owner-scoped code uniqueness, prevents orphaned projects, and avoids inventing an unsafe transfer workflow.

Decision: Centralize stable role capabilities in one backend authorization policy and return effective capabilities to the frontend.

Reason: Server enforcement remains authoritative across API, reports, exports/imports, AI context, and direct service use. The UI can remain role-aware without duplicating the security model. Non-members receive 404 to avoid project enumeration; members without a capability receive 403.

Decision: Restrict finance to OWNER, PROJECT_ADMIN, and PROJECT_MANAGER and enforce section-aware reporting and AI context.

Reason: Hiding a navigation link is insufficient. Project budget fields are masked, finance endpoints reject unauthorized callers, finance-specific portability is blocked, mixed reports omit financial sections, and backend AI evidence never includes unauthorized financial facts.

Decision: Implement bounded entity comments and recipient-owned in-app notifications without mentions, outbound email, or background infrastructure.

Reason: V2.1 needs useful collaboration with a small, auditable persistence surface. Same-project target validation, 4,000-character comments, 100-recipient fan-out/list bounds, soft deletion, and append-only audit events preserve isolation and history. Membership, role, comment, and mapped task-assignment events generate safe in-app notifications.

Decision: Treat deterministic report generation and audit activity as separate manager-level capabilities, and treat finance-category documents as finance-sensitive.

Reason: A read-only project role must not gain audit history or trigger report generation implicitly, and document/knowledge endpoints must not become a finance side channel. Mixed reports, document lists/downloads/search, exports, and AI context all enforce the underlying domain capability.

Decision: Keep V1 runtime version `1.0.0` and the V1 release documentation/tag unchanged during V2 branch development.

Reason: V2.1 is an unreleased development increment. Release identity changes only through a later explicit release process.


## 2026-09-02 — V2.2 advanced scheduling

Decision: Add a pure deterministic scheduling engine and one project-scoped scheduling service rather than embedding date logic in routes or the Timeline.

Reason: CPM, float, recursive propagation, baselines, deadline impact, intelligence, and scenarios must consume the same explainable backend truth. The frontend remains presentation and explicit user control.

Decision: Interpret existing `BLOCKS` and `DEPENDS_ON` task relations as finish-to-start scheduling edges and leave `RELATED_TO` non-scheduling.

Reason: V2.2 can add useful dependency scheduling without changing the existing dependency schema or inventing lag, lead, start-to-start, calendars, or hidden semantics.

Decision: Use inclusive calendar-day durations and signed baseline variance (`current - baseline`).

Reason: These rules are deterministic with the existing date-only model. Positive variance is late, negative variance is early, and incomplete task dates remain explicitly unavailable rather than inferred.

Decision: Persist one normalized schedule baseline per project and require explicit creation or replacement.

Reason: Baseline comparisons need durable factual snapshots and same-project foreign keys. Automatic replacement would erase the reference plan and make variance misleading.

Decision: Require non-mutating preview plus a fingerprint-bound confirmation token before recursive schedule apply.

Reason: Users must see affected tasks, milestones, critical path, and deadline impact before a manager-level transaction changes dates. Recalculation at apply time prevents stale previews from overwriting concurrent work.

Decision: Reuse schedule preview for Sprint 11 task and milestone delay scenarios.

Reason: Scenario analysis must show the same recursive impacts as operational scheduling while remaining read-only. No AI output can call apply or mutate operational project data.

Decision: Add schedule-aware health and stable automatic alert conditions.

Reason: Projected deadline lateness, milestone lateness, material baseline variance, critical blocked tasks, and dependency violations are deterministic conditions suitable for existing alert reconciliation and lifecycle behavior.

Validation scope includes exact CPM/float graphs, disconnected and incomplete schedules, recursive chain/branch/convergence, baseline create/replace and signed variance, preview non-mutation, stale-token rejection, atomic apply, audit events, manager/viewer authorization, schedule-aware scenarios, frontend preview/apply behavior, Alembic head migration, PostgreSQL, and browser E2E.

Compatibility fix: Live PostgreSQL validation exposed timezone-naive SQLAlchemy mappings for V2.1 collaboration timestamps even though migration `20260901_0013` created timezone-aware columns. The model now explicitly uses `DateTime(timezone=True)` for membership, comment-deletion, and notification-read timestamps; no schema migration was required. A mapping regression test and authenticated PostgreSQL project-creation flow verify the fix.


## 2026-09-03 — V2.3 AI & Knowledge 2.0

Decision: Add a separate provider-neutral embedding boundary and preserve the existing Gemini Interactions generation provider unchanged.

Reason: Embedding batches, vector validation, and retrieval purposes have different contracts from structured generation. Isolating them keeps credentials server-side, configuration centralized, tests deterministic, and the existing AI architecture intact.

Decision: Store one normalized embedding per document chunk as PostgreSQL-compatible JSON with provider/model/version/dimension/content-hash metadata.

Reason: The current bounded local corpus does not justify an external vector database. A unique chunk constraint prevents duplicates, content hashes reuse unchanged vectors, and explicit version/model metadata makes reindex decisions explainable. Candidate retrieval remains bounded so application-side cosine ranking is maintainable at the intended scale.

Decision: Merge lexical and semantic ranks with deterministic Reciprocal Rank Fusion, then suppress adjacent chunks while better diverse evidence exists.

Reason: RRF is exact, testable, and does not depend on opaque model reranking or incomparable score scales. Neighbor suppression reduces repetitive excerpts without discarding clearly better evidence.

Decision: Filter active membership, project, document selection/category, and finance capability in SQL before either lexical or semantic scoring.

Reason: Semantic search cannot become a late-filter authorization side channel. The same server-side RBAC boundary governs library listing, index status, retrieval, Project Assistant context, grounded Q&A, comparison, and evidence resolution.

Decision: Treat extracted document content as untrusted data and require every AI document citation to resolve through the backend-owned evidence catalog.

Reason: A document may contain prompt injection or fabricated identifiers. System instructions remain separate, no tools/actions are enabled, unknown/cross-project/deleted evidence is rejected, and Q&A/comparison remain read-only.

Decision: Preserve lexical availability when embeddings are absent or fail and expose an explicit semantic lifecycle.

Reason: Provider configuration, quota, network, or malformed responses must not make uploaded documents unusable. `LEXICAL_ONLY`, `FAILED`, and `PARTIAL` states plus safe fallback diagnostics are honest without exposing provider payloads.

Known V2.3 boundaries: indexing is synchronous; ranking uses a bounded application-side vector scan; there is no OCR, background queue, dedicated vector index/database, cross-project corpus, integrations, cloud deployment, or autonomous AI execution.


## 2026-09-04 — V2.4 integrations

Decision: Add provider-neutral OAuth, calendar, email, and source-control protocols coordinated by one application integration service.

Reason: Google and GitHub transport details must remain replaceable and testable without leaking into domain services, routes, AI, or frontend behavior. The modular monolith retains one authorization/audit boundary and no parallel integration architecture.

Decision: Make OAuth accounts user-owned, encrypt access/refresh tokens with a dedicated Fernet key, and store OAuth state only as a time-bounded user/provider-bound digest with PKCE.

Reason: Project membership does not authorize using another user's external identity. Credentials must remain server-side, authenticated at rest, absent from APIs/logs/audit/AI, and explicitly removable. Missing provider configuration is a supported non-blocking state.

Decision: Keep provider operations read-only and require explicit selection, linking, or preview/confirmation before any local domain record is created.

Reason: Calendar browsing, Gmail search, and GitHub browsing must not silently import, poll, or mutate project state. Calendar Meeting import refetches and verifies a signed preview fingerprint; Gmail links are private by default; GitHub task links do not change task lifecycle.

Decision: Preserve local records when credentials are revoked or upstream objects disappear.

Reason: Provider availability cannot control the integrity of the project system of record. Disconnect deletes credentials and marks connections/links unavailable; refresh not-found updates availability only. Reconnection and unlinking remain explicit user actions.

Decision: Admit only explicit authorized external links into the existing backend-owned evidence catalog and label all external content untrusted.

Reason: Gemini receives no live provider access, credentials, inbox/repository dump, tools, or write capability. Permission filtering occurs before context construction, content cannot override system rules, and fabricated/cross-project/private/finance-restricted evidence remains invalid.

Known V2.4 boundaries: no webhooks or background synchronization, no provider write-back, no Gmail body/attachment ingestion, no shared OAuth accounts, no autonomous AI execution, and no cloud secret manager. GitHub's default `read:user` scope supports public repositories; private repository access requires an explicit operator scope override. Live provider acceptance requires operator-owned OAuth applications and credentials and is therefore optional when unavailable.
