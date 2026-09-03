# Zero-cost cloud deployment plan

Status: optional demonstration architecture, not deployed  
Free-tier facts checked: 2026-09-02

Loris PMO does not require cloud hosting. The local Docker Compose workflow is the reliable, supported baseline. This document describes how the existing architecture can be hosted without a recurring platform charge while usage remains inside provider allowances. It is not an SLA-backed production recommendation and it does not authorize automatic deployment.

## Provider-neutral architecture

```text
Static HTTPS frontend / same-origin gateway
            |
            v
Container-capable FastAPI service
       |              |
       v              v
Managed PostgreSQL   Private S3-compatible object storage
```

The services are replaceable:

- frontend: any static host with SPA fallback and HTTPS;
- backend: any container host that supports injected environment values;
- database: managed PostgreSQL reachable with TLS;
- documents: private S3-compatible storage;
- TLS/gateway: one public origin is recommended for cookie/CSRF simplicity.

The application does not require a proprietary database API, public bucket URLs, or a provider SDK in domain services.

## Current illustrative free-tier stack

One possible demonstration stack as of the review date is:

| Layer | Example | Current published allowance/behavior | Important constraint |
|---|---|---|---|
| Static frontend | Cloudflare Pages Free | 500 builds/month, one concurrent build, 20,000 files, 25 MiB per asset | Cloudflare now recommends Workers for many new projects; Pages remains available |
| Backend | Koyeb Free Web Service | one 512 MB / 0.1 vCPU / 2 GB instance | scales to zero after one idle hour; no volume; explicitly intended for preview/hobby use |
| PostgreSQL | Neon Free | $0, 100 CU-hours/month per project, 0.5 GB storage per project, scale-to-zero | cold starts, storage and transfer quotas; not an availability guarantee |
| Documents | Cloudflare R2 Standard | 10 GB-month storage, 1M Class A and 10M Class B operations/month, free egress | free allowance excludes Infrequent Access; account/billing rules can change |

Official references:

- Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits/
- Koyeb instances: https://www.koyeb.com/docs/reference/instances
- Koyeb pricing FAQ: https://www.koyeb.com/docs/faqs/pricing
- Neon pricing: https://neon.com/pricing
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/

Free tiers, quotas, account-validation requirements, inactivity policies, and product availability change. Recheck every provider before creating accounts. Configure hard spending controls or do not attach a payment method where the provider permits. “Free tier” is not equivalent to “cannot generate a bill.”

## Authentication topology

Do not combine unrelated provider default domains with direct cross-origin browser calls. The frontend must read the non-HttpOnly CSRF cookie, so choose one of:

1. Recommended: expose one frontend origin and proxy `/api`, `/health`, and `/ready` to Koyeb.
2. Use custom frontend/API subdomains under one registrable domain and set `COOKIE_DOMAIN` deliberately.

The first option can use a provider edge function/gateway, but that gateway configuration is infrastructure outside this repository. If neither is possible, stay local; do not weaken CSRF.

## Deployment outline

1. Create a private PostgreSQL database and record its TLS connection URL in the backend secret manager.
2. Create a private Standard-class S3-compatible bucket. Disable public listing/access.
3. Build the backend from `backend/Dockerfile`; inject production environment settings.
4. Run `python -m app.cli check-config`.
5. Run `alembic upgrade head` once as a one-off job.
6. Start the backend and validate `/health` and `/ready`.
7. Build `frontend/` with the chosen public `VITE_API_BASE_URL` (empty for a same-origin gateway).
8. Configure SPA fallback to `index.html`, HTTPS, exact origin/host values, and gateway rate limits.
9. Create the first account with the backend CLI.
10. Test login, one CSRF-protected mutation, a private document upload/download, and logout.

Example backend storage values for R2-style S3 compatibility:

```text
DOCUMENT_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://<account-endpoint>
S3_BUCKET=<private-bucket>
S3_REGION=auto
```

Credentials remain backend-only. Do not place them in `VITE_*`, repository settings visible to pull requests, or frontend hosting variables.

## Expected free-tier limitations

- Backend and database cold starts can make the first request slow or fail a short timeout.
- A sleeping backend cannot provide continuous monitoring, background refresh, or an SLA.
- 512 MB backend memory may be tight for large PDF/DOCX/XLSX extraction.
- Database and object quotas constrain document and audit-history growth.
- Free services may suspend inactive accounts or change terms.
- OAuth providers still require correct production consent-screen and callback configuration.
- Gemini usage has its own independent quota and is optional.
- No automatic cross-provider backup is implemented.

Use this topology for a portfolio demonstration or low-traffic personal evaluation only. Local Docker remains the fallback whenever a provider sleeps, removes its free offering, or requires billing.

## Local and cloud coexistence

### Recommended: separate data

```text
LOCAL  -> local PostgreSQL + local document volume
CLOUD  -> managed PostgreSQL + private object bucket
```

Both run the same code and migrations but contain independent accounts/projects. This prevents accidental production-data use and makes the local environment reliable without internet access.

### Optional: local app using cloud data

A local backend can point to managed PostgreSQL and object storage, but this is operationally risky:

- internet loss interrupts work;
- local commands can mutate production data;
- environment files are easier to confuse;
- latency and provider quotas apply;
- local backup scripts do not back up S3 objects.

Use a visibly named environment file, a least-privilege database role, an isolated cloud project when possible, and `python -m app.cli check-config` before startup. There is no synchronization or merge mechanism between local and cloud datasets.

## Cost and safety checklist

- Reconfirm official pricing and quotas.
- Enable usage alerts and hard caps where available.
- Keep bucket access private and credentials least-privileged.
- Retain independent database exports and object inventories.
- Verify the integration encryption key is recoverably stored.
- Never treat a free-tier provider snapshot as the only backup.
- Keep `docker compose up -d` tested as the no-cloud fallback.
