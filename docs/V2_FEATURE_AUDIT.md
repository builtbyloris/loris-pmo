# V2 feature audit

Audit date: 2026-09-04  
Branch: `v2-development`  
Release state: unreleased; no `v2.0.0` tag exists

Status meanings:

- **COMPLETE**: implemented and covered by relevant automated/runtime evidence.
- **COMPLETE WITH LIMITATION**: required V2 behavior is implemented; a documented accepted boundary remains.
- **PARTIAL**: material requested behavior is missing.
- **NOT IMPLEMENTED**: no implementation.
- A blocker is a failure of the agreed V2.1–V2.5 definition, not an accepted non-enterprise limitation.

## V2.1 — Multi-user, RBAC, and collaboration

| Capability | Status | Implementation / evidence | Limitation | V2 blocker |
|---|---|---|---|---|
| Multi-user project membership | COMPLETE | `models/collaboration.py`, `services/collaboration.py`, migration `20260901_0013`, `test_collaboration.py` | No ownership transfer | NO |
| Centralized RBAC | COMPLETE | `services/authorization.py`, `auth/authorization.py`, project API guards | Five fixed system roles | NO |
| Comments and notifications | COMPLETE | collaboration schemas/services/routes and frontend collaboration workspace | In-app only; no outbound invitation email | NO |
| Actor-aware audit/activity | COMPLETE | audit service/model and collaboration tests | Append-oriented application audit, not an external SIEM | NO |
| Permission-aware finance/documents/reports/AI | COMPLETE | centralized capabilities plus cross-project/role tests | No field-level custom policy designer | NO |
| Realtime collaboration | NOT IMPLEMENTED | No WebSocket/event-bus module | Explicitly outside V2.1 | NO |

## V2.2 — Advanced scheduling

| Capability | Status | Implementation / evidence | Limitation | V2 blocker |
|---|---|---|---|---|
| Recursive propagation | COMPLETE | `services/scheduling.py`, scheduling routes/tests | Finish-to-start only | NO |
| Deterministic CPM and float | COMPLETE | scheduling analytics/service tests | Calendar-day calculations | NO |
| Baselines and variance | COMPLETE | scheduling models/schemas, migration `20260902_0014` | Explicit snapshots, no portfolio baseline optimizer | NO |
| Preview/apply and stale protection | COMPLETE | schedule fingerprint, preview/apply endpoints and tests | No drag-and-drop planner | NO |
| Milestone/deadline impact | COMPLETE | scheduling impact response and Timeline UI | No holiday/business calendar | NO |
| Scenario reuse | COMPLETE | operational AI scenario path uses deterministic scheduling | Simulation only by design | NO |
| Resource leveling/assignment | NOT IMPLEMENTED | No leveling engine | Explicitly outside V2.2 | NO |

## V2.3 — AI and Knowledge 2.0

| Capability | Status | Implementation / evidence | Limitation | V2 blocker |
|---|---|---|---|---|
| Provider-neutral embeddings | COMPLETE | `ai/embeddings.py`, Gemini embedding adapter, dependency boundary | Gemini is the only live adapter | NO |
| Hybrid retrieval | COMPLETE | `services/knowledge.py`, deterministic RRF and tests | Application-side vectors; no dedicated vector index | NO |
| Permission/project isolation | COMPLETE | document authorization and knowledge cross-project tests | Depends on the central RBAC model | NO |
| Evidence-backed Q&A/comparison | COMPLETE | knowledge AI service, schemas, routes, frontend, tests | Bounded document types; no OCR | NO |
| Index lifecycle/deduplication | COMPLETE | content hash/model/version metadata, reindex/delete cleanup | Synchronous; no queue | NO |
| Lexical fallback | COMPLETE | knowledge service fallback tests | Semantic quality unavailable without embedding provider | NO |
| Prompt-injection boundary | COMPLETE | document context treated as untrusted evidence; evidence catalog validation | Not a claim of model infallibility | NO |

## V2.4 — Integrations

| Capability | Status | Implementation / evidence | Limitation | V2 blocker |
|---|---|---|---|---|
| Provider-neutral OAuth connections | COMPLETE | `integrations/provider.py`, services/routes, migration `20260904_0016` | Google and GitHub only | NO |
| Encrypted token storage | COMPLETE | `integrations/crypto.py`, encrypted connection columns, tests | Losing the Fernet key requires reconnect | NO |
| Google Calendar import | COMPLETE | Google adapter plus preview/confirm flow | Read/manual refresh; no push sync | NO |
| Gmail bounded links | COMPLETE | bounded search and explicit project/finance link workflow | Message content is not copied into audit logs | NO |
| GitHub browsing/task links | COMPLETE | GitHub adapter, explicit repository/work-item link flows | Read/manual refresh; no webhooks | NO |
| RBAC/account isolation | COMPLETE | integration service authorization and cross-account tests | User-owned rather than organization-owned connections | NO |
| Safe disabled/failure states | COMPLETE | provider availability/status mapping and tests | No background retry worker | NO |

## V2.5 — Cloud and production readiness

| Capability | Status | Implementation / evidence | Limitation | V2 blocker |
|---|---|---|---|---|
| Dev/test/prod configuration | COMPLETE | `core/config.py`, `app.cli check-config`, production tests | Configuration is environment-based, not a remote control plane | NO |
| Auth/cookie/CORS/host hardening | COMPLETE | auth route, app middleware/config validation, security tests | Cross-site default provider domains require a same-origin gateway | NO |
| Health/readiness/errors/logs | COMPLETE | health API, safe application/runtime logs, real Uvicorn and Docker synthetic-exception regression | No external APM/SIEM integration | NO |
| Managed PostgreSQL readiness | COMPLETE | configurable pool/TLS engine options, Alembic workflow | Provider-specific CA provisioning remains operational | NO |
| Document storage abstraction | COMPLETE | `app/storage.py`, local/S3 contract tests, authenticated streaming | No automatic local-to-S3 migration | NO |
| Local backup/restore | COMPLETE WITH LIMITATION | `scripts/backup.sh`, `scripts/restore.sh`, backup guide | Scripts cover local volume only | NO |
| Cloud backup guidance | COMPLETE WITH LIMITATION | `docs/BACKUP_RESTORE.md`, provider export/object guidance | No cross-provider automated backup job | NO |
| Frontend production build | COMPLETE | central API URL, production Vite validation, static Nginx image | Existing bundle-size warning remains | NO |
| Production containers | COMPLETE | rebuilt non-root/read-only images; approved-Host loopback probe; empty/split API-base validation; TLS PostgreSQL smoke | Same-origin routing still requires the documented gateway | NO |
| Zero-cost cloud plan | COMPLETE WITH LIMITATION | `docs/CLOUD_FREE_DEPLOYMENT.md` with dated official references | Free tiers have quotas, sleep, and no SLA | NO |
| CI | COMPLETE | `.github/workflows/ci.yml` | Test/build only; no deployment | NO |
| Rate limiting | COMPLETE WITH LIMITATION | production guide requires trusted-gateway limits | No in-process/distributed limiter | NO |
| Migration schema change | COMPLETE | No V2.5 schema change; head remains `20260904_0016` | None | NO |

## Final decision

V2.1 through V2.4 retain their completed status. The three verified V2.5 blockers are now resolved:

1. Production Uvicorn/asyncio exception records are sanitized before handlers. Real Uvicorn and rebuilt Docker checks return safe HTTP 500 JSON, retain a correlated application error event, and contain neither the synthetic exception marker nor traceback output. Normal server operational messages remain visible; OS error numbers remain available.
2. The image probe connects to loopback with an explicitly approved Host header from centralized settings. Production backend/frontend containers become healthy; public Host requests succeed and arbitrary untrusted hosts (including unlisted localhost) still return HTTP 400. No wildcard or host-validation bypass was added.
3. Empty/unset API base intentionally means same-origin in Compose and the shared frontend build/runtime validator. Empty and HTTPS split-origin builds/configurations pass; malformed and insecure production origins fail. OAuth paths remain backend-owned.

Final rerun: **150 backend tests passed**, including configured PostgreSQL connectivity; **56 frontend tests passed**; focused production/runtime regressions, Ruff, TypeScript, and production builds passed. Rebuilt non-root/read-only containers passed `/health`, `/ready`, and synthetic error validation against disposable TLS-enabled PostgreSQL. A fresh migration reached `20260904_0016`; the normal local database remains at the same head.

Authenticated disposable smoke checks covered login/secure cookies, project creation, access/membership, scheduling, knowledge status, integration status, reports, CSV/XLSX exports, document upload/download/delete, task import preview/confirm, logout, and static frontend SPA serving. No live AI or external integration calls were made. Temporary database/user/project records, containers, volume, network, image tags, environment file, and TLS files were removed. Real local data and historical backups were preserved.

**V2 TECHNICALLY COMPLETE**, with the accepted limitations above and no remaining reproduced blocker. This audit does not merge `v2-development`, move `main`, create `v2.0.0`, publish a release, start a redesign, or begin a V3 roadmap. Deployment and release actions remain subject to explicit approval.
