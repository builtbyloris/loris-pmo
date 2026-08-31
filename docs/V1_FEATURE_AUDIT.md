# Loris PMO V1 Feature Audit

Audit date: 2026-08-31. This audit maps the 33 official feature areas in `PROJECT_INTELLIGENCE_SPEC.md` to executable code, tests, and explicit V1 boundaries. “Complete” means the specified V1 outcome is present; it does not imply enterprise-scale collaboration or autonomous execution.

| # | Official feature | Classification | Implementation evidence / location | V1 limitation | Blocks V1? |
|---:|---|---|---|---|:---:|
| 1 | Multi-Project Management | COMPLETE | `app/services/projects.py`, `app/repositories/projects.py`, project/portfolio frontend pages, `test_projects.py` | Single-owner workspace; no enterprise RBAC | No |
| 2 | Project Dashboard | COMPLETE | `ProjectOverviewPage.tsx`; project, analytics, control, memory and AI APIs | Fixed V1 layout, not user-configurable widgets | No |
| 3 | Tasks | COMPLETE | work-planning models/service/API/UI and `test_work_planning.py` | No Jira-scale workflow customization | No |
| 4 | Milestones | COMPLETE | milestone model plus work-planning service/API/UI/tests | V1 milestone fields only | No |
| 5 | Timeline / Gantt | COMPLETE WITH V1 LIMITATION | work-planning timeline UI and dependency-aware backend schedule data | Readable project timeline; not a full Microsoft Project scheduler | No |
| 6 | Team Management | COMPLETE | people models/service/API/UI and `test_people.py` | Owner-managed project team, no organization directory/RBAC | No |
| 7 | Workload | COMPLETE WITH V1 LIMITATION | deterministic people/workload service and workload dashboard/tests | Warning and allocation view; no automatic capacity optimizer | No |
| 8 | Budget | COMPLETE | finance model/service/API/UI and `test_finance.py` | Project/category budget model only | No |
| 9 | Expenses | COMPLETE | expense lifecycle, links, validation, finance UI/tests | No accounting/ERP integration | No |
| 10 | Budget Analytics | COMPLETE | `app/analytics/budget.py`, finance analytics API/UI/tests | Deterministic V1 forecast rules | No |
| 11 | Risk Management | COMPLETE | control models/service/API, 5×5 matrix UI, `test_control.py` | No probabilistic Monte Carlo engine | No |
| 12 | Issues | COMPLETE | issue lifecycle and task/milestone links in control backend/UI/tests | V1 workflow only | No |
| 13 | Change Requests | COMPLETE | change-request decision workflow and linked entities in control backend/UI/tests | Human decision recording; no automated execution | No |
| 14 | Project Log | COMPLETE | memory models/service/API/UI and `test_memory.py` | Project-local log | No |
| 15 | Meeting Management | COMPLETE | meetings, participants and action items in memory backend/UI/tests | No calendar/video integration | No |
| 16 | Decision Log | COMPLETE | structured decisions and links in memory backend/UI/tests | Project-local decision records | No |
| 17 | Activity / Audit Log | COMPLETE | `models/audit.py`, audit service, project activity endpoints and cross-feature tests | Material events, not raw request logging | No |
| 18 | Project KPIs | COMPLETE | `analytics/intelligence.py`, intelligence service/API/UI, `test_intelligence.py` | Fixed deterministic KPI catalog | No |
| 19 | Project Health Score | COMPLETE | weighted available-dimension engine, history and drivers in intelligence backend/UI/tests | Fixed V1 weights | No |
| 20 | Automatic Alerts | COMPLETE | intelligence repository/service and deterministic automation rules/tests | In-app lifecycle; no external delivery channel | No |
| 21 | Portfolio Dashboard | COMPLETE | portfolio repository/service/API/page and portfolio/intelligence tests | Owner-scoped portfolio only | No |
| 22 | AI Project Assistant | COMPLETE | provider-neutral `app/ai`, context builder, `ProjectAssistantService`, assistant UI/tests | Gemini optional and read-only | No |
| 23 | AI Insights | COMPLETE | AI analysis models/repository/service/API/workspace and `test_ai_analysis.py` | Bounded persisted analyses | No |
| 24 | AI Recommendations | COMPLETE | recommendation model/lifecycle/API/UI/tests | Proposals only; acceptance executes nothing | No |
| 25 | AI Daily Briefing | COMPLETE | `ai_operations` service/models/API/UI and tests | Explicit/fingerprint generation, not every page load | No |
| 26 | AI Weekly Review | COMPLETE | rolling seven-day deterministic facts plus bounded AI synthesis/tests | Limited by available event history | No |
| 27 | AI Scenario Analysis | COMPLETE | deterministic simulation plus read-only interpretation in AI operations/tests | Supported scenario templates only | No |
| 28 | AI Meeting Assistant | COMPLETE | meeting analysis/proposal models, confirmation boundary, UI/tests | Proposal-by-proposal user confirmation required | No |
| 29 | AI Recommendations Center | COMPLETE | assistant analysis workspace and recommendation review lifecycle/tests | No autonomous action application | No |
| 30 | Reports | COMPLETE WITH V1 LIMITATION | `ReportingService`, report API, Reports UI, PDF artifact tests | Six fixed deterministic reports; no template/chart editor | No |
| 31 | Export | COMPLETE WITH V1 LIMITATION | `ExportService`, CSV/XLSX endpoints, PDF report export and artifact tests | Fixed project datasets; no scheduled delivery | No |
| 32 | Project Documents | COMPLETE WITH V1 LIMITATION | revision `20260831_0012`, document model/service/API/UI and document tests | Images are stored but not OCR-processed; local storage adapter | No |
| 33 | AI Knowledge Base | COMPLETE WITH V1 LIMITATION | document chunks, lexical retrieval, Project Assistant context/evidence integration and tests | Deterministic lexical search; no vector database | No |

## Supporting V1 capability: import

Import is not one of the 33 official feature labels, but the specification requires it as a supporting V1 capability. `ImportService` and the Reports & Data workspace support task and expense templates in CSV, XLSX, and JSON. The flow is upload → validate → preview → explicit confirmation → atomic persistence → audit. Invalid rows make the batch non-confirmable; raw files and unrestricted provider payloads are not persisted.

## Cross-cutting release evidence

- Authentication cookies, CSRF checks, owner/project repository filters, archive write protection, and safe public error envelopes apply to the new APIs.
- Document storage is server-only and configurable. Generated storage keys and resolved-path containment prevent client filenames from controlling storage paths.
- Document text is bounded, treated as untrusted prompt data, and only backend-catalogued `document_chunk:<uuid>` references can be accepted as document evidence.
- Deterministic reports work without Gemini. AI remains optional and read-only.
- EN/IT localization, light/dark styling, empty/error/loading states, Docker/PostgreSQL, Alembic, backend/frontend regression suites, artifact parsing, live API E2E, and one controlled document-grounded Gemini request have been verified.

## Known non-blocking V1 boundaries

- Single-owner private workspaces; enterprise RBAC, real-time collaboration, cloud object storage, OCR, semantic/vector retrieval, report template editors, scheduled delivery, and generic user-defined import mapping remain future work.
- The frontend production bundle emits a non-blocking size advisory; route-level code splitting is a post-V1 optimization.
- Visual browser automation was unavailable in the validation environment; authenticated live HTTP E2E was used as the documented fallback.
- Older migrations expose pre-existing Alembic check-constraint metadata drift during `alembic check`; revision 0012 itself upgrades, downgrades, and reaches PostgreSQL head successfully.
