# Loris PMO v1.0.0 Release Checklist

Complete automated items before the release commit. Complete manual items before creating or pushing the tag. Do not tag or publish from this checklist automatically.

## Repository

- [ ] Working tree contains only reviewed release changes
- [ ] Authoritative application version is `1.0.0`
- [ ] Release date/status are correct
- [ ] README, architecture, development log, audit, and release notes are current
- [ ] No secret, credential, dump, demo environment, or generated business data is tracked
- [ ] No open-source license is implied for the private repository
- [ ] `git diff --check` passes

## Backend and database

- [ ] Full backend tests pass
- [ ] PostgreSQL-marked integration test passes against PostgreSQL
- [ ] Ruff passes
- [ ] Alembic reports `20260831_0012` as head/current
- [ ] Upgrade path reaches head on the Docker PostgreSQL database
- [ ] Existing project records remain valid

## Frontend

- [ ] Full frontend tests pass
- [ ] TypeScript check passes
- [ ] Production build passes
- [ ] Bundle advisory is understood and accepted for V1

## Docker and local operations

- [ ] `docker compose config` passes with a configured `.env`
- [ ] Images build successfully
- [ ] PostgreSQL, backend, and frontend start successfully
- [ ] PostgreSQL and backend health checks pass
- [ ] `scripts/start.sh`, `stop.sh`, and `status.sh` behave safely
- [ ] Backup creates a PostgreSQL dump and document archive
- [ ] Restore procedure has been reviewed; destructive confirmation is explicit

## Security and AI

- [ ] No `.env`, API key, database dump, backup, or default account is tracked
- [ ] Authentication cookie, CSRF, owner, cross-project, and archive protections pass
- [ ] Document path/storage and evidence-catalog protections pass
- [ ] Prompt/response content is absent from audit logging
- [ ] Gemini model and backend-only configuration are documented
- [ ] AI remains read-only except individually confirmed meeting proposals
- [ ] No new live Gemini call was made for release preparation

## Artifacts and data portability

- [ ] PDF report opens and contains deterministic data
- [ ] CSV export parses correctly
- [ ] XLSX export opens and contains expected rows/types
- [ ] Invalid import cannot be confirmed
- [ ] Valid task/expense import requires preview and explicit confirmation

## Manual acceptance

- [ ] Complete `docs/MANUAL_ACCEPTANCE_CHECKLIST.md`
- [ ] Review EN and IT
- [ ] Review light and dark themes
- [ ] Review desktop and mobile-width layout
- [ ] Capture and privacy-review portfolio screenshots
- [ ] Rehearse `docs/DEMO_FLOW.md`

## Release

- [ ] Sprint 12 commit is present (`83c5b74` at preparation time)
- [ ] Create and review the Sprint 13 release commit
- [ ] Confirm the working tree is clean
- [ ] Create annotated tag `v1.0.0` only after explicit approval
- [ ] Push the release commit and tag
- [ ] Create GitHub release from `docs/RELEASE_NOTES_V1.md`
