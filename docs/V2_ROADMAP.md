# Loris PMO V2 roadmap

Status: active development on `v2-development`
Baseline: immutable `v1.0.0` release

## V2.1 — Multi-user, RBAC, and collaboration foundation

V2.1 adds authenticated project access without changing the V1 operational people model. A `User` authenticates; a `Person` describes a reusable human/resource; a `ProjectMember` links a Person to delivery work; and a `ProjectMembership` grants a User access to a project. A membership may optionally map to one operational project Person. None of these concepts is substituted for another.

Existing `projects.owner_user_id` remains the ownership anchor. Migration `20260901_0013` creates exactly one active OWNER membership for every existing project. OWNER memberships cannot be removed or reassigned; ownership transfer is deliberately deferred.

### Stable roles and default capabilities

| Area | OWNER | PROJECT_ADMIN | PROJECT_MANAGER | CONTRIBUTOR | VIEWER |
|---|---:|---:|---:|---:|---:|
| Read project/work/control/people/memory/documents/reports | ✓ | ✓ | ✓ | ✓ | ✓ |
| Update project | ✓ | ✓ | ✓ | — | — |
| Archive project | ✓ | — | — | — | — |
| Manage authenticated memberships | ✓ | ✓ | — | — | — |
| Create/update delivery work | ✓ | ✓ | ✓ | ✓ | — |
| Delete/archive delivery work | ✓ | ✓ | ✓ | — | — |
| Manage people/control/meetings/documents | ✓ | ✓ | ✓ | meetings only | — |
| Read/manage finance | ✓ | ✓ | ✓ | — | — |
| Generate reports / read audit activity | ✓ | ✓ | ✓ | — | — |
| Use Project Assistant | ✓ | ✓ | ✓ | ✓ | — |
| Generate proactive AI / confirm proposals | ✓ | ✓ | ✓ | — | — |
| Write comments | ✓ | ✓ | ✓ | ✓ | — |

The backend capability registry is authoritative. The frontend consumes the effective capabilities only to present appropriate controls; hidden controls are not a security boundary. A non-member receives a project-not-found response, while a member lacking a capability receives a safe permission error.

### Collaboration scope

- Existing users are added by exact email. There is no public user directory, registration flow, outbound email, or invitation delivery in V2.1.
- Comments are bounded to 4,000 characters and target tasks, risks, issues, change requests, meetings, or decisions after same-project validation. Structured mentions are deferred.
- In-app notifications are recipient-only, capped to 100 per request, and generated for membership/role changes, comments, and task assignment when the application user is mapped to the assigned project Person. Email/push delivery is deferred.
- Activity continues to use append-only audit events and now includes actor display name plus a human-readable summary.
- Report generation and audit activity require manager-level capabilities. Finance-category documents and finance-derived KPI/health/alert projections are filtered without `finance.read`; mixed reports omit finance sections, while budget reports, expense exports/imports, and finance APIs require finance capabilities.
- AI context removes finance topics/evidence when the caller lacks finance access. Project Assistant remains read-only; proactive AI and meeting proposal confirmation require manager-level capabilities.

## V2.2 — Advanced scheduling

V2.2 adds backend-owned deterministic scheduling over existing tasks, milestones, project deadlines, and task dependencies. It includes finish-to-start graph semantics, CPM earliest/latest dates, critical path, total/free float, explicit normalized baselines, signed variance, recursive propagation preview, fingerprint-bound apply, milestone/deadline impact, schedule-aware health and alerts, a Timeline/Gantt workspace, and schedule-aware read-only scenario simulation.

Calendar-day scheduling is intentional. Business calendars, lag/lead, resource leveling, drag-and-drop scheduling, probabilistic forecasting, fallback inference for missing dates, and autonomous AI schedule changes are deferred. Only managers/administrators/owners may create/replace baselines or apply recursive changes; read access follows project access.

## Planned V2 increments

- V2.3: invitation lifecycle and ownership transfer with explicit acceptance and recovery rules.
- V2.4: structured mentions, additional assignment-notification families, notification preferences, and retention management.
- Later V2: cloud deployment, external identity, integrations, object storage, semantic retrieval, and advanced reporting only when separately designed and authorized.

This roadmap does not change the published V1 release notes or the `v1.0.0` tag.
