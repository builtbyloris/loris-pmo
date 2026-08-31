# Isolated Demo Data Guide

Loris PMO never creates demo business data automatically. For screenshots or a portfolio demonstration, use a separate Docker Compose project with disposable named volumes. Never build the demo inside a real local workspace.

## 1. Create an isolated environment

Stop the normal stack so the same host ports are free:

```bash
./scripts/stop.sh
cp .env.example .env.demo
```

Edit `.env.demo` and replace all credential placeholders with demo-only random values. Do not reuse personal or production secrets. Start an isolated Compose project:

```bash
docker compose --env-file .env.demo --project-name loris-pmo-demo up -d --build
```

Create a demo-only account interactively:

```bash
docker compose --env-file .env.demo --project-name loris-pmo-demo   exec backend python -m app.cli create-user
```

`.env.demo` is ignored by the repository-wide `.env*` rule added for local secrets.

## 2. Build one coherent project manually

Suggested fictional project: **City Library Digital Launch** (`LIB-DIGITAL`). This name is documentation only; nothing seeds it.

Create enough connected records to make the product understandable:

- Objective: launch the public digital borrowing service; add two measurable success criteria.
- Planning: one completed task, two in progress, one blocked, one overdue, one future milestone, and one dependency.
- People: project manager, developer, and stakeholder; assign work and vary availability.
- Finance: a planned budget, two categories, one paid expense, one pending expense, and one planned expense.
- Control: one high risk, one medium risk, one open issue linked to a task, and one approved change request.
- Memory: one completed meeting with action items, one decided decision, and one manual Project Log entry.
- Intelligence: recalculate once so health, KPIs, alerts, and portfolio facts reflect the records.
- AI: generate only the outputs needed for the demo if a demo-only Gemini key is configured.
- Documents: upload one short, non-sensitive requirements PDF or TXT file and retrieve one grounded answer.

Do not use real client names, confidential text, personal email addresses, or production documents.

## 3. Reset safely

The following command is intentionally destructive **only to the explicitly named demo Compose project and its volumes**:

```bash
docker compose --env-file .env.demo --project-name loris-pmo-demo down -v
rm .env.demo
```

Confirm the project name is exactly `loris-pmo-demo` before running it. Never add `-v` to the normal `./scripts/stop.sh` flow.
