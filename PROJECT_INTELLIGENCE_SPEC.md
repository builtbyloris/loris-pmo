# LORIS PMO

## Project Intelligence & AI-Assisted Project Management Portal

### Master Product & Technical Specification

**Version:** 1.0\
**Status:** Master specification\
**Primary objective:** Build a personal, professional-grade Project
Management and Project Intelligence web application with analytics,
automation, and human-in-the-loop AI assistance.

------------------------------------------------------------------------

# 1. Product Vision

Loris PMO is a web application designed to give a Project Manager a
single control center for managing multiple projects, organizing
operational information, monitoring performance, automating repetitive
workflows, and receiving contextual AI assistance.

The product must help the user answer:

-   What is happening?
-   What changed?
-   What is late?
-   What is at risk?
-   How is the budget performing?
-   Which resources are overloaded?
-   Which objectives are threatened?
-   What requires attention now?
-   What options are available?
-   What could happen next?

The AI is a **copilot**, not the Project Manager.

Core operating model:

``` text
Project Data
    ↓
Deterministic Analytics
    ↓
Alerts / Context
    ↓
AI Analysis
    ↓
Insight / Recommendation
    ↓
User Review
    ↓
Accept / Reject
    ↓
Validated Action
    ↓
Audit Trail
```

------------------------------------------------------------------------

# 2. Product Principles

## 2.1 Human-in-the-loop

AI may analyze, summarize, explain, recommend, simulate, and prepare
actions.

AI must never silently: - change deadlines; - change budgets; - assign
people; - approve change requests; - delete records; - modify project
status; - create operational records without confirmation.

All AI-generated changes follow:

``` text
AI Proposal → User Review → Confirm/Reject → Backend Validation → Apply → Audit
```

## 2.2 Database as source of truth

The application database is authoritative.

AI must not fabricate: - tasks; - milestones; - expenses; - people; -
deadlines; - risks; - issues; - KPIs; - decisions; - historical events.

If information is insufficient, the system must say so.

## 2.3 Deterministic calculations first

The backend calculates factual metrics. AI interprets them.

Examples: - task completion; - overdue count; - budget utilization; -
variance; - risk score; - workload; - milestone progress; - project
health.

## 2.4 Empty by default

There must be no production demo data.

A new account starts with:

``` text
Projects: 0
Tasks: 0
Milestones: 0
Budget: €0
Risks: 0
Issues: 0
```

Test fixtures may exist only in testing environments.

## 2.5 Connected information

Features must not behave as isolated pages. Entities should affect
relevant analytics and context.

Example:

``` text
Issue
 ↓
Task
 ↓
Milestone
 ↓
Schedule
 ↓
Health Score
 ↓
Alert
 ↓
AI Insight
 ↓
Recommendation
```

------------------------------------------------------------------------

# 3. Target Usage

Initial release: - one authenticated user; - multiple projects; -
grouping by client/company/area; - personal/private use; -
enterprise-like project structure; - architecture ready for future
multi-user evolution.

The product should be useful as a real personal PM tool and strong
enough to serve as a GitHub portfolio project.

------------------------------------------------------------------------

# 4. Official Feature Scope

The 33 official feature areas are:

1.  Multi-Project Management
2.  Project Dashboard
3.  Tasks
4.  Milestones
5.  Timeline / Gantt
6.  Team Management
7.  Workload
8.  Budget
9.  Expenses
10. Budget Analytics
11. Risk Management
12. Issues
13. Change Requests
14. Project Log
15. Meeting Management
16. Decision Log
17. Activity / Audit Log
18. Project KPIs
19. Project Health Score
20. Automatic Alerts
21. Portfolio Dashboard
22. AI Project Assistant
23. AI Insights
24. AI Recommendations
25. AI Daily Briefing
26. AI Weekly Review
27. AI Scenario Analysis
28. AI Meeting Assistant
29. AI Recommendations Center
30. Reports
31. Export
32. Project Documents
33. AI Knowledge Base

Cross-cutting capabilities: - authentication; - objectives and success
criteria; - stakeholder management; - task dependencies; - automation
engine; - email notifications; - import; - multilingual UI; - light/dark
mode; - configuration and customization.

------------------------------------------------------------------------

# 5. Navigation

``` text
LORIS PMO
│
├── Portfolio
│   └── Portfolio Dashboard
│
├── Projects
│   └── Project Workspace
│       ├── Overview
│       ├── Objectives
│       ├── Tasks
│       ├── Milestones
│       ├── Timeline / Gantt
│       ├── Team
│       ├── Stakeholders
│       ├── Budget
│       ├── Expenses
│       ├── Risks
│       ├── Issues
│       ├── Change Requests
│       ├── Project Log
│       ├── Meetings
│       ├── Decisions
│       ├── Activity Log
│       ├── Documents
│       ├── Analytics
│       └── Reports
│
├── AI Copilot
│   ├── Chat
│   ├── Insights
│   ├── Recommendations
│   ├── Daily Briefing
│   ├── Weekly Review
│   ├── Scenario Analysis
│   ├── Meeting Assistant
│   └── Recommendations Center
│
└── Settings
    ├── Profile
    ├── Appearance
    ├── Language
    ├── Notifications
    ├── AI Configuration
    └── Data / Import / Export
```

Use sidebar + top navigation.

------------------------------------------------------------------------

# 6. UI / UX Direction

Visual style: - modern professional SaaS; - dark-professional default
direction; - light and dark themes; - clean information hierarchy; -
dashboard-focused; - responsive; - polished but not unnecessarily
decorative.

Languages: - Italian; - English; - architecture prepared for additional
languages.

User-facing strings must use an i18n system rather than being scattered
as hardcoded strings.

Homepage after login: - Portfolio Dashboard; - include a "Continue where
you left off" area when relevant.

------------------------------------------------------------------------

# 7. First-Run Experience

No demo projects.

If no projects exist:

``` text
Welcome to Loris PMO

You don't have any projects yet.

[Create your first project]
```

Project creation uses a simple wizard with no more than three steps.

Suggested:

``` text
1. Basic Information
2. Objectives, Dates & Budget
3. Review & Create
```

After creation, suggest but do not force:

1.  Define objectives
2.  Add team
3.  Create milestones
4.  Add tasks
5.  Configure budget

------------------------------------------------------------------------

# 8. Multi-Project Management

A user can: - create projects; - edit projects; - archive projects; -
search projects; - filter projects; - sort projects; - group by
client/company/area; - navigate between projects.

Core project fields: - name; - project code; - description; -
client/company/area; - project manager; - status; - priority; - start
date; - target end date; - budget; - tags; - notes.

Initial statuses: - Not Started - Active - On Hold - Completed -
Archived

Initial priorities: - Low - Medium - High - Critical

------------------------------------------------------------------------

# 9. Objectives & Success Criteria

Projects support multiple objectives and measurable success criteria.

Example:

``` text
Objective:
Launch the application.

Success criteria:
- Release before 30 November
- Total cost <= €50,000
- Critical test pass rate >= 95%
```

The system must distinguish: - task completion; - project progress; -
objective achievement.

AI and analytics may evaluate whether objectives appear threatened, but
conclusions must be grounded in actual data.

------------------------------------------------------------------------

# 10. Portfolio Dashboard

Show real aggregated information across projects: - total projects; -
active projects; - at-risk projects; - critical projects; - overdue
tasks; - open issues; - high risks; - upcoming milestones; - total
planned budget; - actual cost; - committed cost; - forecast; - critical
alerts.

Project summary cards/table: - project; - progress; - health; -
budget; - deadline; - risks; - overdue tasks.

Support search, filters, sorting, and grouping.

------------------------------------------------------------------------

# 11. Project Dashboard

Project control center.

Sections: - health score; - progress; - budget; - milestones; - risks; -
issues; - workload; - objectives; - attention required; - recent
activity; - AI insights/recommendations when available.

Never show invented metrics when underlying data does not exist.

------------------------------------------------------------------------

# 12. Tasks

Fields: - title; - description; - status; - priority; - assignee; -
start date; - due date; - estimated effort; - actual effort; -
completion percentage; - tags; - parent task; - milestone; -
dependencies; - notes.

Initial statuses: - Backlog - To Do - In Progress - Blocked - Review -
Done - Cancelled

Views: 1. List 2. Kanban 3. Timeline/Gantt

All views use the same underlying task records.

Subtasks should be supported.

------------------------------------------------------------------------

# 13. Task Dependencies

Support dependency relationships sufficient for project scheduling.

At minimum: - blocks; - blocked by; - depends on; - related to.

Prevent invalid self-dependencies and obvious cycles where practical.

Dependencies feed: - Gantt; - schedule analytics; - milestone risk; -
scenario analysis; - AI context.

------------------------------------------------------------------------

# 14. Milestones

Fields: - title; - description; - deadline; - status; - owner; - linked
tasks; - progress; - notes.

Milestone progress should derive from linked work where appropriate.

Detect: - approaching deadlines; - incomplete linked tasks; - overdue
linked tasks; - blocking dependencies.

------------------------------------------------------------------------

# 15. Timeline / Gantt

Support: - task dates; - milestone dates; - dependencies; - progress; -
drag-and-drop date adjustment; - dependency visualization; - useful
critical-path visualization.

Do not attempt to reproduce every feature of Microsoft Project in V1.

Date modifications must update shared task data and trigger relevant
recalculations.

------------------------------------------------------------------------

# 16. Team Management

Separate a person from their project role.

Person information: - name; - email; - department; - skills; - notes.

Project membership: - project; - person; - role; - responsibilities; -
availability.

Roles may include: - Project Manager; - Sponsor; - Product Owner; - Team
Member; - Developer; - Designer; - Data Analyst; - QA / Tester; -
Stakeholder; - Other/custom.

A person may participate in multiple projects.

------------------------------------------------------------------------

# 17. Stakeholder Management

Fields: - name; - organization; - project role; - influence; -
interest; - communication frequency; - preferred channel; - notes.

Provide a stakeholder matrix.

AI may suggest stakeholder attention based on project events, but
communication remains under user control.

------------------------------------------------------------------------

# 18. Workload

Calculate from real assignments: - active tasks per person; - overdue
tasks; - estimated effort; - due dates; - workload distribution.

Highlight potential overload and under-allocation.

AI may propose reallocation but cannot perform it without confirmation.

------------------------------------------------------------------------

# 19. Budget

Support: - planned budget; - actual cost; - committed cost; -
forecast; - remaining amount; - variance; - category allocations.

Budget categories are configurable.

Example: - Development - Equipment - External Services - Marketing -
Travel - Other

------------------------------------------------------------------------

# 20. Expenses

Fields: - description; - category; - amount; - date; - payer; -
supplier; - status; - related project; - optional task/milestone; -
notes.

Statuses: - Planned - Pending - Paid - Cancelled

Financial logic must distinguish planned, committed, and actual values.

------------------------------------------------------------------------

# 21. Budget Analytics

Calculate: - planned vs actual; - committed cost; - forecast; -
remaining budget; - budget utilization; - variance; - category
spending; - monthly trend; - thresholds.

Formulas must live in deterministic application logic, not in LLM
prompts.

------------------------------------------------------------------------

# 22. Risk Management

Risk = a possible future event.

Fields: - title; - description; - category; - probability; - impact; -
score; - owner; - mitigation; - contingency; - status; - identified
date; - review date; - affected tasks; - affected milestones.

Initial score:

``` text
Risk Score = Probability × Impact
```

Support a risk matrix.

Statuses: - Identified - Monitoring - Mitigating - Occurred - Accepted -
Closed

------------------------------------------------------------------------

# 23. Issues

Issue = a problem/event that has already occurred.

Fields: - title; - description; - date; - category; - priority; -
owner; - schedule impact; - cost impact; - scope impact; - quality
impact; - estimated delay; - estimated cost; - affected tasks; -
affected milestones; - resolution; - actual impact; - notes.

Suggested workflow: - Open - In Analysis - Action Planned - In
Progress - Resolved - Closed

------------------------------------------------------------------------

# 24. Change Requests

Fields: - title; - requested change; - reason; - requester; - date; -
scope impact; - schedule impact; - budget impact; - resource impact; -
affected entities; - status; - decision; - decision date.

Statuses: - Draft - Pending - Approved - Rejected - Implemented -
Cancelled

AI can prepare impact analysis. AI cannot approve.

------------------------------------------------------------------------

# 25. Project Log

Structured chronological project memory.

Types: - Meeting - Decision - Issue - Change - Milestone - Task Update -
Risk Update - Note - AI Event

Fields: - timestamp; - type; - title; - description; - source/author; -
linked entities.

Support: - manual entries; - automatic system events; - AI-related
events.

Search and filtering are required.

------------------------------------------------------------------------

# 26. Meeting Management

Fields: - title; - date/time; - duration; - participants; - agenda; -
notes; - decisions; - action items; - related entities.

AI Meeting Assistant may extract: - summary; - decisions; - action
items; - owners; - deadlines; - risks; - issues.

Extracted items are proposals until confirmed.

------------------------------------------------------------------------

# 27. Decision Log

Fields: - decision; - date; - decision maker; - reason; -
alternatives; - selected option; - expected impact; - actual impact; -
related entities; - notes.

The decision history becomes AI context.

The AI should eventually answer: - Why did we choose X? - What
alternatives were considered? - When was the decision made? - What
impact was expected?

Only from stored evidence.

------------------------------------------------------------------------

# 28. Activity / Audit Log

System-level immutable or append-oriented history for significant
actions.

Examples: - task created; - task updated; - expense added; - risk
changed; - recommendation accepted; - recommendation rejected; - project
setting changed.

Store: - timestamp; - actor; - action; - entity; - entity ID; - old
value where appropriate; - new value where appropriate.

Audit Log is distinct from Project Log.

------------------------------------------------------------------------

# 29. Project KPIs

Initial KPI library: - task completion rate; - overdue task rate; -
milestone completion; - schedule variance; - budget utilization; -
budget variance; - open risks; - high risks; - open issues; - workload
distribution; - objective progress.

Use one centralized analytics layer.

------------------------------------------------------------------------

# 30. Project Health Score

Dimensions: - Schedule - Budget - Tasks - Risks - Resources - Objectives

Each dimension must have documented deterministic rules.

Overall score uses documented/configurable weighting.

The application should explain score movement.

Example:

``` text
Health decreased from 84 to 78.

Drivers:
- 2 tasks became overdue
- one high-impact risk increased
- a milestone deadline is approaching
```

AI may translate calculations into natural-language explanation, but not
invent drivers.

------------------------------------------------------------------------

# 31. Automatic Alerts

Severity: - Info - Warning - Critical

Initial alerts: - task overdue; - milestone approaching; - milestone at
risk; - budget threshold; - high risk; - critical issue; - workload
overload; - project deadline; - health decline.

Fields: - title; - reason; - severity; - affected entity; - timestamp; -
read/unread; - status; - optional AI analysis.

Avoid alert fatigue.

------------------------------------------------------------------------

# 32. Automation Engine

Support predefined and future custom rules.

Architecture:

``` text
Event
 ↓
Rule Evaluation
 ↓
Action
 ↓
Audit
```

Examples:

``` text
IF task overdue > 2 days
THEN create alert
AND recalculate relevant health metrics
AND optionally request AI analysis
```

``` text
IF budget utilization >= threshold
THEN create warning/critical alert
AND notify user according to preferences
```

Automation actions must be traceable.

AI must not be the source of deterministic trigger truth.

------------------------------------------------------------------------

# 33. Notifications

Initial external channel: - email.

Support preferences for: - severity; - immediate critical alerts; -
daily digest; - weekly digest.

Do not email for every low-value event.

------------------------------------------------------------------------

# 34. AI Project Assistant

AI is available: - in a dedicated chat; - contextually inside relevant
sections.

It may use: - project metadata; - objectives; - tasks; - milestones; -
team; - stakeholders; - budget; - expenses; - risks; - issues; -
changes; - logs; - meetings; - decisions; - KPIs; - alerts; - relevant
documents.

Example questions: - What needs my attention? - Why is this project at
risk? - What changed this week? - Which milestone is most vulnerable? -
How is the budget performing? - Why did the health score decline? - Why
did we choose this option?

------------------------------------------------------------------------

# 35. AI Insights

Proactive observations derived from evidence.

Structure: - title; - severity; - explanation; - evidence; - affected
entities; - timestamp; - status.

Example:

``` text
Potential schedule risk

3 tasks linked to Testing are overdue.
Testing milestone is due in 4 days.
```

The user may request a deeper "why" explanation.

------------------------------------------------------------------------

# 36. AI Recommendations

Required structure: - Recommendation - Why - Evidence - Expected
Impact - Alternatives - Confidence

Recommendations are proposals, not actions.

------------------------------------------------------------------------

# 37. AI Recommendations Center

Statuses: - Pending - Accepted - Rejected - Ignored - Applied - Expired

Preserve: - original recommendation; - evidence; - confidence; - user
decision; - timestamp; - resulting action if applicable.

This creates a human-AI decision history.

------------------------------------------------------------------------

# 38. AI Daily Briefing

Proactive dashboard experience.

Example:

``` text
Good morning.

3 things require attention:

1. Testing milestone may be delayed.
2. Project Beta budget utilization reached 87%.
3. Two critical tasks are due tomorrow.
```

Prioritize useful information rather than producing generic summaries.

------------------------------------------------------------------------

# 39. AI Weekly Review

Summarize: - progress; - completed work; - delays; - budget movement; -
risks; - resolved issues; - decisions; - changes; - major events; - next
focus.

Compare with previous periods only when historical data exists.

------------------------------------------------------------------------

# 40. AI Scenario Analysis

Simulation only.

Never change the real project.

Example:

``` text
What if Development is delayed by 10 days?
```

Possible output: - affected tasks; - affected milestones; - projected
release impact; - affected resources; - estimated financial impact where
calculable; - AI interpretation; - possible responses.

Clearly label hypothetical results.

------------------------------------------------------------------------

# 41. AI Meeting Assistant

Input: - notes; - transcript when available; - participants; - project
context.

Output proposals: - summary; - decisions; - actions; - owners; -
deadlines; - risks; - issues.

User confirmation is required before operational records are created.

------------------------------------------------------------------------

# 42. Project Documents

Supported uploads: - PDF - DOCX - XLSX - CSV - TXT - images

Metadata: - filename; - type; - size; - upload date; - category; -
description; - linked project/entities.

Suggested categories: - Requirements - Specifications - Meeting Notes -
Contracts - Reports - Other

------------------------------------------------------------------------

# 43. AI Knowledge Base

Prepare for retrieval-augmented project Q&A.

The AI should retrieve relevant project documents rather than sending
all documents on every request.

Document-grounded answers should identify source documents where
practical.

Respect project/user authorization boundaries.

------------------------------------------------------------------------

# 44. Reports

Initial reports: - Project Summary - Weekly Report - Executive Summary -
Budget Report - Risk Report - Team Report

Metrics must come from real project data.

AI may create narrative interpretation around verified metrics.

------------------------------------------------------------------------

# 45. Export

Support: - CSV - Excel - PDF

Relevant export targets: - tasks; - expenses; - risks; - issues; -
project summaries; - reports.

------------------------------------------------------------------------

# 46. Import

Support: - CSV - XLSX - JSON

Flow:

``` text
Select
→ Validate
→ Preview
→ Map Fields
→ Confirm
→ Import
→ Audit
```

Invalid records must not silently enter production data.

------------------------------------------------------------------------

# 47. Authentication & Security

Initial application requires an account/login.

Requirements: - secure password hashing; - protected routes; - secure
session/token strategy; - logout; - backend authorization; - input
validation; - secrets via environment variables.

Never expose: - database credentials; - secret keys; - Gemini API keys

to frontend code.

------------------------------------------------------------------------

# 48. AI Provider Architecture

Initial provider: - Google Gemini API.

Use abstraction:

``` text
Application
    ↓
AI Service
    ↓
Provider Interface
    ↓
Gemini Provider
```

Do not scatter Gemini-specific calls throughout the codebase.

Future provider replacement should be feasible.

------------------------------------------------------------------------

# 49. AI Context Engine

Do not send the full database for every AI request.

Build context packages such as:

``` text
Project Summary
Objectives
Critical Tasks
Milestones
Budget Snapshot
Risks
Issues
Recent Log
Recent Decisions
KPIs
Alerts
Relevant Documents
```

Context selection belongs in backend application logic.

------------------------------------------------------------------------

# 50. AI Reliability Rules

AI must: - distinguish facts from assumptions; - ground claims in
available evidence; - communicate missing information; - communicate
uncertainty; - distinguish simulation from reality; - never claim an
action was executed if it was not; - never invent project records; -
never bypass user confirmation for protected actions.

These safeguards must be enforced through architecture and backend
validation, not only system prompts.

------------------------------------------------------------------------

# 51. AI Action Flow

``` text
User request
 ↓
Intent interpretation
 ↓
Context retrieval
 ↓
AI prepares proposed action
 ↓
Backend validates proposal
 ↓
UI preview
 ↓
User confirms/rejects
 ↓
Backend applies confirmed action
 ↓
Audit Log
 ↓
Project Log when relevant
```

The LLM must never receive unrestricted database execution capability.

------------------------------------------------------------------------

# 52. Technology Stack

Preferred:

Frontend: - React - TypeScript

Backend: - Python - FastAPI

Database: - PostgreSQL

Analytics: - Pandas where useful

AI: - Google Gemini API

Charts: - mature React-compatible library such as Recharts or Plotly

Infrastructure: - Docker - Docker Compose

Initial deployment: - localhost; - Dockerized; - structured for future
cloud deployment.

------------------------------------------------------------------------

# 53. Frontend Architecture

Suggested structure:

``` text
frontend/src/
├── components/
├── features/
├── pages/
├── layouts/
├── hooks/
├── services/
├── types/
├── utils/
├── i18n/
└── styles/
```

Prefer feature-based organization as complexity grows.

Avoid giant page components and duplicated business logic.

------------------------------------------------------------------------

# 54. Backend Architecture

Suggested structure:

``` text
backend/app/
├── api/
├── auth/
├── models/
├── schemas/
├── repositories/
├── services/
├── analytics/
├── ai/
├── automation/
├── notifications/
├── core/
└── main.py
```

API handlers orchestrate requests but should not contain all business
logic.

------------------------------------------------------------------------

# 55. API Design

Use versioned REST endpoints, e.g.:

``` text
/api/v1/auth
/api/v1/projects
/api/v1/projects/{project_id}/tasks
/api/v1/projects/{project_id}/milestones
/api/v1/projects/{project_id}/budget
/api/v1/projects/{project_id}/risks
/api/v1/projects/{project_id}/issues
/api/v1/projects/{project_id}/meetings
/api/v1/projects/{project_id}/analytics
/api/v1/projects/{project_id}/ai
```

Requirements: - typed request/response schemas; - validation; -
appropriate status codes; - consistent error format; - authorization
checks; - pagination for large collections where appropriate.

Do not expose raw database internals.

------------------------------------------------------------------------

# 56. Database Architecture

Relational core entities:

``` text
User
Project
ProjectMember
Person
Stakeholder
Objective
SuccessCriterion
Task
TaskDependency
Milestone
Budget
BudgetCategory
Expense
Risk
Issue
ChangeRequest
ProjectLogEntry
Meeting
MeetingParticipant
Decision
ActivityLog
Alert
Notification
AIInsight
AIRecommendation
AIScenario
Document
Report
AutomationRule
```

Use: - primary keys; - foreign keys; - indexes; - created_at; -
updated_at; - constraints; - migrations.

Use soft deletion only where historical integrity justifies it.

------------------------------------------------------------------------

# 57. High-Level Relationships

``` text
User
 └── Projects

Project
 ├── Objectives
 ├── Success Criteria
 ├── Tasks
 ├── Milestones
 ├── Members
 ├── Stakeholders
 ├── Budget
 ├── Expenses
 ├── Risks
 ├── Issues
 ├── Change Requests
 ├── Log Entries
 ├── Meetings
 ├── Decisions
 ├── Activity Logs
 ├── Alerts
 ├── Documents
 ├── Reports
 ├── AI Insights
 ├── AI Recommendations
 └── AI Scenarios
```

Tasks may relate to: - people; - milestones; - dependencies; - risks; -
issues; - changes.

Meetings may relate to: - participants; - decisions; - proposed action
items; - risks; - issues.

------------------------------------------------------------------------

# 58. Analytics Architecture

``` text
Operational Data
      ↓
Analytics Service
      ↓
KPIs / Health / Trends
      ↓
Alerts + Dashboard + AI Context
```

Centralize formulas.

Frontend components consume calculated values rather than reimplementing
formulas independently.

------------------------------------------------------------------------

# 59. Error Handling

Handle: - invalid forms; - API errors; - database failures; - AI
provider failure; - file errors; - import errors; - notification
failures.

AI failure must not make core PM functionality unusable.

Example:

``` text
AI analysis is temporarily unavailable.
Your project data has not been changed.
```

Never show normal users raw stack traces.

------------------------------------------------------------------------

# 60. Empty States

Every major feature needs a useful empty state.

Examples:

``` text
No tasks yet.
Create your first task to start planning.
```

``` text
No recorded risks.
```

``` text
No AI insights yet.
Add project information to enable deeper analysis.
```

Do not populate fake content for visual appearance.

------------------------------------------------------------------------

# 61. Customization

The application should progressively support configurable: - roles; -
statuses; - priorities; - categories; - KPI settings; - custom fields
where practical.

Do not overengineer customization during the first implementation phase.

------------------------------------------------------------------------

# 62. System Activity

Provide a way to inspect significant internal/project activity.

Example:

``` text
16:20 Task created
16:21 KPIs recalculated
16:21 Health score updated
16:22 Alert generated
16:22 AI insight generated
16:24 Recommendation rejected
```

This may initially be implemented through the Activity/Audit Log rather
than as a separate official feature.

------------------------------------------------------------------------

# 63. Data Integrity

Examples: - expenses belong to projects; - milestones belong to
projects; - tasks cannot depend on themselves; - cross-project
relationships require explicit support; - budget calculations must
reconcile; - risk scoring is consistent; - AI-applied actions are
audited; - historical records are not accidentally destroyed.

Use transactions for operations requiring multiple related changes.

------------------------------------------------------------------------

# 64. Testing Strategy

Backend: - unit tests; - service tests; - API tests; - database
integration tests.

Frontend: - component tests; - critical flow tests.

High-priority unit tests: - KPI formulas; - health score; - budget
calculations; - risk scoring; - task state logic; - automation rules; -
scenario calculations.

Acceptance flows: 1. Create project. 2. Create/update task. 3. Overdue
task triggers correct effects. 4. Add expense and update budget. 5.
Create risk and update health. 6. Create issue. 7. Record meeting. 8. AI
proposes action without applying it. 9. User confirms AI action. 10.
Scenario simulation leaves real data unchanged. 11. Import validates
before commit. 12. Export produces correct data.

------------------------------------------------------------------------

# 65. Docker & Deployment

Initial architecture:

``` text
Browser
  ↓
Frontend
  ↓
FastAPI
  ↓
PostgreSQL
```

Gemini is accessed only by backend services.

Docker Compose should support local development.

Keep architecture cloud-ready but do not make public deployment a V1
requirement.

------------------------------------------------------------------------

# 66. Environment Variables

Use `.env` locally and provide `.env.example`.

Examples:

``` text
DATABASE_URL=
SECRET_KEY=
GEMINI_API_KEY=
APP_ENV=
FRONTEND_URL=
```

Never commit real secrets.

------------------------------------------------------------------------

# 67. Repository Structure

Recommended:

``` text
loris-pmo/
├── frontend/
├── backend/
├── docs/
├── tests/
├── scripts/
├── .env.example
├── docker-compose.yml
├── PROJECT_INTELLIGENCE_SPEC.md
├── README.md
└── LICENSE
```

Architecture may adjust this if documented.

------------------------------------------------------------------------

# 68. Documentation Requirements

Final repository should include: - README; - architecture
documentation; - database/ER diagram; - API documentation; - AI
architecture; - screenshots; - roadmap; - setup instructions; - testing
instructions; - demo video plan/link when available.

The README should present Loris PMO as a professional portfolio project.

------------------------------------------------------------------------

# 69. Git Strategy

Development repository remains private initially.

Suggested workflow:

``` text
main
 ↓
feature branch
 ↓
implementation
 ↓
tests
 ↓
review
 ↓
merge
```

Example commits:

``` text
feat: add project creation flow
feat: implement task dependencies
feat: add project health score
feat: add AI recommendation workflow
fix: correct budget variance calculation
```

Do not bundle unrelated changes into huge commits where avoidable.

------------------------------------------------------------------------

# 70. Development Rules for Codex

Codex must:

1.  Read this specification before substantial work.
2.  Inspect existing code before modifying it.
3.  Do not rebuild working modules unnecessarily.
4.  Preserve architectural consistency.
5.  Keep frontend, business logic, analytics, persistence, and AI
    separated.
6.  Do not add fake production data.
7.  Never expose secrets.
8.  Add/update tests for meaningful logic.
9.  Keep database migrations reproducible.
10. Keep the app runnable after meaningful increments.
11. Document significant architectural changes.
12. Avoid scope outside this specification unless requested.
13. Never create autonomous AI database changes.
14. Prefer maintainable, simple implementations over overengineering.
15. Report limitations rather than hiding incomplete behavior.

------------------------------------------------------------------------

# 71. 30-Day Development Roadmap

## Days 1--2 --- Foundation

-   architecture;
-   repository structure;
-   React + TypeScript;
-   FastAPI;
-   PostgreSQL;
-   Docker;
-   auth;
-   migrations;
-   layout;
-   sidebar;
-   top navigation;
-   light/dark mode;
-   i18n;
-   routing;
-   tests.

## Days 3--4 --- Projects

-   multi-project;
-   project wizard;
-   objectives;
-   success criteria;
-   portfolio;
-   project overview.

## Days 5--7 --- Tasks & Schedule

-   tasks;
-   subtasks;
-   list;
-   Kanban;
-   milestones;
-   dependencies;
-   timeline/Gantt.

## Days 8--10 --- People

-   team;
-   project roles;
-   stakeholders;
-   workload.

## Days 11--13 --- Financial

-   budget;
-   categories;
-   expenses;
-   committed/actual;
-   forecast foundation;
-   analytics.

## Day 14 --- Risks & Issues

-   risk register;
-   matrix;
-   issues;
-   impact fields.

## Days 15--16 --- Project Memory

-   project log;
-   meetings;
-   decisions;
-   activity/audit.

## Days 17--18 --- Changes

-   change requests;
-   impact analysis workflow.

## Days 19--21 --- Analytics & Control

-   KPIs;
-   health score;
-   trends;
-   alerts;
-   automation;
-   portfolio intelligence.

## Days 22--23 --- AI Foundation

-   Gemini integration;
-   provider abstraction;
-   context builder;
-   safety/action architecture.

## Days 24--25 --- AI Assistant

-   contextual chat;
-   project summary;
-   schedule/budget/risk analysis.

## Days 26--27 --- Proactive AI

-   insights;
-   recommendations;
-   recommendation center;
-   daily briefing;
-   weekly review.

## Day 28 --- Advanced AI

-   scenario analysis;
-   meeting assistant.

## Day 29 --- Knowledge & Reporting

-   documents;
-   knowledge-base foundation;
-   reports;
-   import/export;
-   email notification integration where feasible.

## Day 30 --- Release

-   integration testing;
-   bug fixing;
-   security review;
-   UI polish;
-   README;
-   diagrams;
-   screenshots;
-   final portfolio presentation.

The target is a coherent V1. Features do not all need enterprise-level
depth during the first month.

------------------------------------------------------------------------

# 72. Definition of Done

A feature is not complete merely because code was generated.

It is done when: - behavior matches this specification; - relevant
validation exists; - tests pass; - UI works; - persistence works; -
empty states work; - errors are handled; - relevant analytics are
updated; - audit behavior works where required; - documentation is
updated where necessary; - existing functionality remains intact.

------------------------------------------------------------------------

# 73. Non-Goals for V1

Do not attempt to build: - a full ERP; - every Jira feature; - every
Microsoft Project feature; - enterprise-scale collaboration; -
autonomous AI management; - Kubernetes infrastructure; - unnecessary
microservices; - premature high-scale optimization.

V1 should be a strong modular monolith unless a documented reason
requires otherwise.

------------------------------------------------------------------------

# 74. Future Evolution

Possible future features: - true multi-user collaboration; - RBAC; -
cloud deployment; - calendar integration; - Gmail integration; -
Slack/Teams integration; - additional AI providers; - local LLM; -
advanced forecasting; - advanced resource capacity planning; - mobile
client; - richer RAG/document intelligence; - custom workflow builder.

These are not reasons to delay the V1.

------------------------------------------------------------------------

# 75. Final Product Philosophy

Loris PMO should function as a Project Manager's digital control center.

The system loop is:

``` text
CAPTURE
   ↓
ORGANIZE
   ↓
MONITOR
   ↓
CALCULATE
   ↓
DETECT
   ↓
AUTOMATE
   ↓
AI ASSIST
   ↓
HUMAN DECISION
   ↓
EXECUTE
   ↓
LOG
   ↓
LEARN
```

The backend owns factual truth.

The analytics engine owns deterministic calculations.

The AI owns interpretation, explanation, contextual assistance, and
proposals.

The user owns decisions.

That separation is a core architectural requirement of Loris PMO.
