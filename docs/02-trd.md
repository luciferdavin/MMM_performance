# MMM Platform — Technical Requirements Document (TRD)

| | |
|---|---|
| **Document** | 02-trd.md |
| **Version** | 1.0 |
| **Date** | 2026-08-01 |
| **Author** | Senior Software Architect — Python + React SaaS |
| **Canonical source** | `docs/_spec.md` (canonical specification) |
| **Supporting research** | `research/data-connector-spec.md`, `research/ai-insights-layer.md`, `research/mmm-engine-comparison.md`, `research/competitor-landscape.md`, `research/agency-workflow.md` |
| **Audience** | Engineering team, AI coding agents, reviewers |

This document is the authoritative technical reference for building the MMM Platform. It is internally consistent with the canonical specification in `docs/_spec.md` and the research reports. Where this document and the scaffolded code differ, this document wins — the code must be refactored to match.

---

## 1. System Architecture Overview

### 1.1 Purpose and context

MMM Platform is a self-serve, multi-tenant, Bayesian Marketing Mix Modeling (MMM) SaaS for marketing agencies. Agencies connect marketing data for each client brand, train MMM models in minutes via background jobs, receive AI-generated natural-language insights, and run budget-optimization scenarios. The platform replaces the traditional 4–8 week, $10–50k consultant engagement with a self-service web product.

### 1.2 System context diagram

```
                          ┌──────────────────────────────────────────────────────┐
                          │                        INTERNET                       │
                          └──────────────────────────────────────────────────────┘
                ┌───────────────────────────────┬────────────────────────────────┐
                │                               │                                │
                ▼                               ▼                                ▼
      ┌──────────────────┐           ┌────────────────────┐            ┌──────────────────────┐
      │   Next.js 15 UI   │           │  FastAPI Backend   │            │  External Ad/Mkt APIs │
      │   (Vercel)        │◄──HTTPS──►│  (Railway / Fly.io)│            │  Meta, Google, GA4,   │
      │   App Router      │           │  REST /api/v1      │◄──────────►│  TikTok, Shopify      │
      │   Tailwind/shadcn │           │  /api/v1/insights  │            └──────────────────────┘
      └───────┬───────────┘           └──────┬──────┬──────┘
              │ JWT (Supabase Auth)          │      │
              ▼                              │      │
      ┌──────────────────┐                   │      │
      │  Supabase Auth    │                  │      │
      │  (JWT, RBAC)      │                  │      │
      └──────────────────┘                   │      │
                                     ┌───────▼──────▼───────┐
                                     │    Celery Workers     │
                                     │  • training  (MMM)    │
                                     │  • connectors(sync)   │
                                     │  • insights  (LLM)    │
                                     │  • reports   (PDF)    │
                                     └───┬─────────┬─────────┘
                                         │         │
                              ┌──────────▼──┐   ┌──▼────────────┐
                              │  Redis      │   │  Supabase PG  │
                              │  (broker)   │   │  + RLS        │
                              └─────────────┘   └──────┬────────┘
                                                       │
                                              ┌────────▼────────┐
                                              │ S3 / R2         │
                                              │ model artifacts │
                                              │ (NetCDF, JSON)  │
                                              └────────┬────────┘
                                                       │
                                              ┌────────▼────────┐
                                              │ LLM Providers   │
                                              │ Ollama (default)│
                                              │ Claude, OpenAI  │
                                              └─────────────────┘
```

### 1.3 Architectural principles

1. **API-first**: The frontend talks only to the FastAPI backend via `/api/v1`. No direct client-to-database or client-to-storage access. All business logic, validation, and tenant scoping live server-side.
2. **Multi-tenant isolation**: Every row is scoped by `organization_id` (and `client_id` where applicable). PostgreSQL Row-Level Security (RLS) enforces isolation at the database layer as a defense-in-depth backstop; the API enforces it at the application layer as the primary control.
3. **Background execution for heavy work**: Model training, connector syncs, LLM insight generation, and PDF report rendering never run in the request path. They are Celery tasks.
4. **Pluggable integration seams**: Data connectors implement a common ABC; LLM providers implement a common Protocol; model storage is a backend abstraction (`local | s3 | r2`). New connectors, LLMs, and storage targets are additive.
5. **Canonical data contract**: All connectors normalize to the canonical `MediaRecord` schema (`date, channel, spend, impressions, clicks, conversions, revenue`). Downstream components (preprocessor, engine, insights) never depend on platform-specific fields.
6. **Fail-safe AI**: Every LLM consumer has a deterministic template fallback. The product must degrade gracefully when the LLM is down.

### 1.4 Component inventory

| Component | Technology | Responsibility |
|---|---|---|
| Web app | Next.js 15 + React 19 + Tailwind + shadcn/ui | Agency workspace, dashboards, model config UI, reports |
| API | FastAPI (Python 3.11) | All business logic, validation, tenant scoping |
| MMM engine | PyMC-Marketing (thin wrapper in `src/mmm/core/engine.py`) | Bayesian model fit, contributions, allocation |
| Job queue | Celery + Redis | Async model training, data sync, insights, reports |
| Database | Supabase (PostgreSQL 15) + RLS | Persistence, auth user store, tenant isolation |
| Auth | Supabase Auth (JWT) + NextAuth.js | Sign-in, session, RBAC claims |
| Object storage | S3 (AWS) or R2 (Cloudflare) | Model artifacts (ArviZ NetCDF traces, JSON diagnostics) |
| LLM | Ollama (default), Claude, OpenAI | NL insights, summaries, scenario Q&A |
| Observability | Sentry, PostHog, structured logs | Errors, product analytics, health |
| Deployment | Vercel (frontend), Railway/Fly.io (backend + workers), Supabase (DB) | Hosting |

---

## 2. Frontend Stack

### 2.1 Framework and tooling

| Concern | Choice | Rationale / notes |
|---|---|---|
| Framework | Next.js 15 (App Router) | Server Components for data fetching, route handlers for auth callbacks |
| UI library | React 19 | Required by Next.js 15 |
| Language | TypeScript (strict mode) | `strict: true` in `tsconfig.json` |
| Styling | Tailwind CSS v4 | Utility-first, design tokens via CSS variables |
| Components | shadcn/ui | Copy-in components on Tailwind; source of truth for buttons, cards, dialogs, tables |
| Charts | Recharts | Composable SVG charts for response curves, contribution bars, forecast lines |
| Auth client | NextAuth.js v5 | JWT strategy backed by Supabase Auth |
| Data fetching | TanStack Query v5 | Server-state caching, optimistic updates, refetch windows |
| Forms/validation | React Hook Form + Zod | Shared Zod schemas mirror backend Pydantic contracts |
| State | Zustand (light) | Only cross-cutting UI state; server state stays in TanStack Query |

### 2.2 Folder structure

```
web/
├── app/
│   ├── (auth)/login/           # Login route (Supabase Auth / NextAuth)
│   ├── (workspace)/
│   │   ├── layout.tsx          # Authenticated shell: sidebar, org switcher
│   │   ├── page.tsx            # Multi-client dashboard (F6)
│   │   ├── clients/[id]/       # Single client workspace
│   │   │   ├── page.tsx        # Dashboard: KPIs, channel cards, recent runs
│   │   │   ├── data/           # Data sources + sync status (F1)
│   │   │   ├── models/         # Model history + train form (F2)
│   │   │   ├── insights/       # NL insights + scenario Q&A (F5)
│   │   │   ├── reports/        # Report generation + share links (F7)
│   │   └── settings/           # Org settings, members, roles
│   └── s/[token]/              # Public client report view (link-based, no auth)
├── components/
│   ├── ui/                     # shadcn/ui primitives
│   ├── charts/                 # Recharts wrappers: ContributionChart, CurveChart, ForecastChart
│   └── client/                 # ClientWorkspace, ModelCard, InsightList, BudgetOptimizer
├── lib/
│   ├── api-client.ts           # Typed fetch wrapper, attaches JWT, envelope parsing
│   ├── auth.ts                 # NextAuth config, role helper
│   ├── validations.ts          # Zod schemas mirroring Pydantic models
│   └── utils.ts                # cn(), formatters (currency, percent, dates)
├── hooks/                      # useModels, useClient, useInsights, ...
└── types/                      # Generated API types (openapi-typescript)
```

### 2.3 Key pages and components (mapped to features)

| Feature | Page | Key components |
|---|---|---|
| F6 Dashboard | `/` , `/clients/[id]` | `KpiCard` (spend, revenue, ROAS), `ChannelPerformanceTable`, `RecentModelRuns`, `ModelStatusBadge` |
| F1 Data connectors | `/clients/[id]/data` | `DataSourceCard` (per connector, config state), `CsvUpload` (file/paste), `SyncSchedulePicker`, `SyncStatusTimeline` |
| F2 Model training | `/clients/[id]/models` | `TrainModelForm` (priors, adstock, saturation, sampler, chains/draws), `TrainingProgress` (job status), `DiagnosticsPanel` (R-hat, R², MAPE, PPC plot) |
| F3 Attribution | `/clients/[id]/insights` | `ContributionBarChart` (Recharts), `RoasTable`, `ResponseCurveChart` (diminishing returns), `TimeDecompositionChart` |
| F4 Budget optimizer | `/clients/[id]/models` | `BudgetOptimizerForm` (total budget, min/max %, floors), `AllocationResultTable`, `ExpectedRevenueChart` |
| F5 AI insights | `/clients/[id]/insights` | `InsightCard` (type badge, title, body, confidence), `ExecutiveSummary`, `ScenarioChat` (Q&A box) |
| F7 Reports | `/clients/[id]/reports` | `ReportBuilder`, `ExportPdfButton`, `ShareLinkDialog` (client token), `ClientReportView` (public) |

### 2.4 Design system

- **Theme**: CSS variables in `globals.css` (light/dark). shadcn/ui tokens (`--background`, `--foreground`, `--primary`, `--border`, ...) drive all components.
- **Charts**: one Recharts theme component reading the same tokens; consistent tooltip, axis, and palette across contribution, curve, and forecast charts.
- **Responsive**: mobile-first; the client view and public reports must render cleanly on mobile.

### 2.5 Frontend build requirements

- Next.js output must be deployable to Vercel (see §14).
- All API client calls go through `lib/api-client.ts`, which injects the Supabase JWT into `Authorization: Bearer <token>` and unwraps the response envelope (§6.3).
- Server Components may call the backend using a service-role client only for safe, server-side reads; never expose the service-role key to the browser.

---

## 3. Backend Stack

### 3.1 Runtime and core libraries

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11 | Per spec |
| API framework | FastAPI | Pydantic v2 models, auto OpenAPI, async support |
| Validation | Pydantic v2 | Single source of truth for request/response contracts (`src/mmm/models/schemas.py`) |
| MMM engine | PyMC-Marketing | Bayesian MMM on PyMC. Imported lazily to keep app startup light |
| Sampling backend | `pymc` (NUTS) / `numpyro` | `sampler` config option; `numpyro` when GPU available |
| Optimization | SciPy (`minimize`) | Budget allocation fallback path |
| Queue | Celery | Model training, sync, insights, reports |
| Broker / cache | Redis | Celery broker + result backend; short TTL caches |
| HTTP client | `httpx` | Async-safe, used by all connectors and LLM providers |
| ORM / DB | SQLAlchemy 2.0 (sync) for worker use; Supabase REST/`postgrest` client for API reads | Workers prefer direct SQLAlchemy to the Supabase-hosted Postgres; the API may use either |
| Config | `pydantic-settings` | `src/mmm/config.py` `Settings` class reads `.env` |

### 3.2 Backend project layout

```
src/mmm/
├── api/                  # FastAPI app: routers, deps, middleware (src/mmm/api/main.py)
│   ├── main.py           # app factory, routers, exception handlers
│   ├── deps.py           # auth dependency (JWT → org/role), pagination
│   ├── routers/
│   │   ├── auth.py, clients.py, datasources.py, syncs.py
│   │   ├── models.py, optimizer.py, insights.py, reports.py, usage.py
│   └── errors.py         # ApiError, envelope helpers
├── core/                 # domain engine (src/mmm/core/*)
│   ├── config.py         # build_model_config()
│   ├── preprocessor.py   # validate_dataset(), to_training_frame()
│   ├── engine.py         # MMMModel wrapper over PyMC-Marketing
│   ├── optimizer.py      # allocate_budget_scipy()
│   └── diagnostics.py    # compute_diagnostics()
├── models/
│   └── schemas.py        # MediaRecord, MMMDataset, ModelConfig, Diagnostics, Insight...
├── connectors/           # DataConnector ABC + platform impls (src/mmm/connectors/*)
│   ├── base.py           # DataConnector ABC, ConnectorConfig
│   ├── csv_upload.py, shopify.py, meta_ads.py, google_ads.py, ga4.py, tiktok.py
│   ├── registry.py       # name → class registry, get_connector()
│   └── controls.py       # holidays, google trends, macro dummies
├── ai/                   # LLM layer (src/mmm/ai/*)
│   ├── providers.py      # LLMProvider protocol + OpenAI/Anthropic/Ollama impls
│   ├── insights.py       # insight generators per type
│   ├── prompts.py        # prompt templates
│   └── report.py         # executive summary + _fallback_report()
├── jobs/                 # Celery
│   ├── celery_app.py     # Celery config, queues, routing
│   └── tasks/
│       ├── train.py, sync.py, insights.py, reports.py
├── storage/              # Model artifact backends
│   ├── base.py           # ArtifactStore protocol
│   ├── local.py, s3.py, r2.py
│   └── keys.py           # key construction (tenant/client/job)
├── db/                   # SQLAlchemy models + migrations (Alembic)
│   ├── models.py, session.py, rls.py (policy bootstrap)
├── services/             # business services (multi-tenancy helpers)
│   ├── tenancy.py, usage.py, credentials.py (encrypt/decrypt)
├── security/             # rate limiting, input sanitization helpers
├── cli.py                # local training CLI for dev/verification
└── config.py             # Settings
```

### 3.3 Async vs sync strategy

- **FastAPI endpoints** for quick reads may be `async def` using `httpx` for external calls.
- **Heavy compute** (model fit, optimization, PDF) runs in Celery workers with synchronous SciPy/PyMC code. The engine's public methods are intentionally sync (`MMMModel.fit`, `.allocate_budget`), which is fine inside workers.
- **Connectors** expose async `fetch_spend` (httpx) for the API path and a sync wrapper used by the Celery sync task.

### 3.4 Configuration surface

`Settings` (env-prefixed, from `src/mmm/config.py`) must cover at least:

```
LLM_PROVIDER           # ollama | anthropic | openai
OLLAMA_BASE_URL        # http://localhost:11434
OLLAMA_MODEL           # qwen2.5:7b
ANTHROPIC_API_KEY / ANTHROPIC_MODEL
OPENAI_API_KEY / OPENAI_MODEL
MODEL_STORAGE_BACKEND  # local | s3 | r2
MODEL_STORAGE_PATH     # local dir or bucket name
REDIS_URL
DATABASE_URL           # Supabase Postgres connection string
SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY
SECRET_KEY             # for credential encryption (KMS-managed in prod)
ENV / LOG_LEVEL
```

---

## 4. Database (Supabase / PostgreSQL)

### 4.1 Platform

- **Supabase** (PostgreSQL 15) hosts the database, provides **Auth** (§5), and enables **Row-Level Security**.
- Migrations managed with Alembic against the Postgres connection string; Supabase SQL migrations may be used for RLS policies and functions.
- `pgcrypto` extension enabled (used for UUIDs and encryption helpers).

### 4.2 Schema (core entities)

Entity relationships from the spec: `Organization → (Users via memberships) → Clients → (DataSources, ModelJobs, Insights, Reports)`.

```
organizations (id, name, slug UNIQUE, plan tier, created_at, settings jsonb)
users            (id uuid PK = auth.users.id, email, full_name, created_at)
memberships      (id, organization_id FK, user_id FK, role enum)
clients          (id, organization_id FK, name, timezone, currency, target_column,
                  control_columns jsonb, created_at, archived bool)
data_sources     (id, client_id FK, organization_id FK, connector_type enum, name,
                  config jsonb, credentials_encrypted text, sync_schedule text,
                  last_sync_at, enabled bool, created_at)
model_jobs       (id, client_id FK, organization_id FK, name, config jsonb,
                  status enum, diagnostics jsonb, artifact_key text, result_summary jsonb,
                  metrics jsonb, error text, queued_at, started_at, finished_at, created_by)
insights         (id, model_job_id FK, organization_id FK, client_id FK, type enum,
                  title, body, confidence float, metrics jsonb, source enum, created_at)
reports          (id, model_job_id FK, organization_id FK, client_id FK, title,
                  share_token uuid UNIQUE, status enum, pdf_key text, created_at)
usage_records    (id, organization_id FK, record_type enum, amount numeric, unit text,
                  meta jsonb, created_at)
```

### 4.3 Enum types

| Enum | Values |
|---|---|
| `membership_role` | `agency_owner`, `analyst`, `viewer` |
| `connector_type` | `csv`, `meta_ads`, `google_ads`, `ga4`, `tiktok`, `shopify` |
| `job_status` | `queued`, `running`, `succeeded`, `failed`, `canceled` |
| `insight_type` | `channel_performance`, `budget_recommendation`, `anomaly`, `benchmark`, `summary` |
| `usage_record_type` | `compute_seconds`, `storage_mb`, `api_calls`, `llm_tokens`, `model_train` |
| `plan_tier` | `starter`, `pro`, `enterprise` |

### 4.4 Row-Level Security (RLS)

Every tenant-scoped table has `organization_id` and RLS enabled. Policies:

1. **Membership check function** (used by all policies):
   ```sql
   create or replace function public.is_org_member(org_id uuid)
   returns boolean
   language sql stable security definer as $$
     select exists (
       select 1 from public.memberships m
       join auth.users u on u.id = m.user_id
       where m.organization_id = org_id
         and m.user_id = auth.uid()
         and m.role in ('agency_owner','analyst','viewer')
     );
   $$;
   ```
2. **`clients`**: `USING (is_org_member(organization_id))` for SELECT; `WITH CHECK` for INSERT requires role `IN ('agency_owner','analyst')`.
3. **`memberships`**: `USING (user_id = auth.uid() OR is_org_member(organization_id))` — users always see their own membership; org-scoped admin actions gated in the API.
4. **`model_jobs` / `data_sources` / `insights` / `reports` / `usage_records`**: `USING (is_org_member(organization_id))`.
5. **RLS is defense-in-depth**: the primary enforcement is the FastAPI auth dependency (§5). `SUPABASE_SERVICE_ROLE_KEY` bypasses RLS and is never exposed to the client; `SUPABASE_ANON_KEY` (public) relies entirely on RLS and should only serve authenticated requests.

### 4.5 Indexes

- `model_jobs(client_id, created_at DESC)` — dashboard "recent runs"
- `model_jobs(organization_id, status)` — queue/ops queries
- `insights(model_job_id)`, `insights(client_id, created_at DESC)`
- `data_sources(client_id)` — client workspace
- `usage_records(organization_id, created_at)` — billing rollups
- `memberships(organization_id)`, `memberships(user_id)`

### 4.6 Usage records

Written by the Celery worker (`services/usage.py`) after every train, sync, insight batch, and LLM call. Fields: `amount` (seconds of compute, MB stored, token count), `unit`, `meta` (job id, model name, provider). Aggregated monthly for plan enforcement (Starter 3 clients/20 trains, Pro 15/100 — **V2**, enforcement is advisory in MVP).

---

## 5. Authentication and Authorization

### 5.1 AuthN

- **Supabase Auth** issues JWTs signed with the project's HS256 key. Routes: email/password sign-up and sign-in, magic-link/OTP optional, password reset.
- **NextAuth.js v5** on the frontend brokers the session: the NextAuth JWT stores the Supabase `access_token` and `user_id`, refreshed via Supabase's `/auth/v1/token?grant_type=refresh_token`.
- **Backend trust**: FastAPI validates the Supabase JWT itself (verify signature via `supabase-jwt` or `PyJWT` with `SUPABASE_JWT_SECRET`), extracts `sub` (user id) and `aud`, then resolves the org/role from `memberships`. Never trust client-sent org claims.

### 5.2 Authorization (RBAC)

| Role | Capabilities |
|---|---|
| `agency_owner` | Everything the analyst can do, plus: invite/remove members, change roles, edit client list, view usage/billing, delete models/clients |
| `analyst` | Train models, run optimizer, generate reports, manage data connectors and sync schedules, view all org data |
| `viewer` | Read-only: dashboards, model history, diagnostics, insights, reports |
| `client` (external) | Read-only public report view via unguessable `share_token` UUID (no login); only the linked report's content |

Enforcement matrix (server-side, in `api/deps.py`):

| Action | agency_owner | analyst | viewer |
|---|---|---|---|
| List clients / dashboard | ✅ | ✅ | ✅ |
| Create/update client | ✅ | ✅ | ❌ |
| Configure data source + credentials | ✅ | ✅ | ❌ |
| Trigger sync / retry | ✅ | ✅ | ❌ |
| Start model job / re-train | ✅ | ✅ | ❌ |
| Run budget optimizer | ✅ | ✅ | ❌ |
| Generate/export report | ✅ | ✅ | ❌ |
| Manage members / billing / usage | ✅ | ❌ | ❌ |

### 5.3 JWT payload expectations

The backend depends on the Supabase JWT claims:

```json
{ "sub": "user-uuid", "aud": "authenticated", "exp": 1740000000, "email": "a@agency.com" }
```

Org/role resolution is a DB lookup on `memberships` — never embedded in the token (keeps role changes instant). A small in-memory/Redis cache (TTL 60 s) avoids a DB hit per request.

### 5.4 External report access

`reports.share_token` (UUIDv4, `gen_random_uuid()`) grants anonymous read of a single report through `GET /api/v1/reports/share/{token}` → served to the public `/s/[token]` page. Tokens are unguessable, revocable (delete row / rotate), and logged for audit.

---

## 6. API Design

### 6.1 Conventions

- Base path: `/api/v1` behind a versioned router.
- JSON only. All timestamps ISO-8601 UTC. Currency in `float` local currency per client.
- Envelope (every response, errors included):

```json
{ "status": "ok", "data": {...} }
{ "status": "error", "error": { "code": "NOT_FOUND", "message": "..." } }
```

- Errors: consistent codes — `VALIDATION`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `PAYMENT_REQUIRED`, `INTERNAL`.
- Pagination: `?limit=1..100&offset=0` (or cursor) with envelope metadata `{ "total": n, "limit": l, "offset": o }` for list endpoints.
- Idempotency: model job creation accepts `Idempotency-Key` header; duplicates return the existing job.
- All endpoints require `Authorization: Bearer <supabase JWT>` except `POST /auth/*`, `GET /health`, and `GET /reports/share/{token}`.

### 6.2 Endpoint catalog

| Method | Path | Feature | Summary |
|---|---|---|---|
| `GET` | `/health` | ops | Liveness + component status (§15) |
| `POST` | `/auth/login` | auth | Exchange Supabase session (client-side flow primary; kept for tests) |
| `POST` | `/auth/refresh` | auth | Refresh JWT |
| `GET` | `/me` | auth | Current user + active org memberships + roles |
| `POST` | `/orgs/{org_id}/invites` | RBAC | Invite member (owner) |
| `GET` | `/orgs/{org_id}/members` | RBAC | List members/roles (owner) |
| `PATCH` | `/orgs/{org_id}/members/{user_id}` | RBAC | Change role (owner) |
| `GET` | `/clients` | F6 | List clients (org-scoped) |
| `POST` | `/clients` | F6 | Create client (analyst+) |
| `GET` | `/clients/{id}` | F6 | Client detail + KPIs |
| `PATCH` | `/clients/{id}` | F6 | Update client meta (analyst+) |
| `GET` | `/clients/{id}/data-sources` | F1 | List connectors + config state |
| `POST` | `/clients/{id}/data-sources` | F1 | Configure connector (analyst+) |
| `PATCH` | `/clients/{id}/data-sources/{ds_id}` | F1 | Update credentials/schedule (analyst+) |
| `POST` | `/clients/{id}/data-sources/{ds_id}/sync` | F1 | Trigger sync job → returns `job` |
| `POST` | `/clients/{id}/csv-upload` | F1 | Multipart CSV upload → parsed preview + save |
| `GET` | `/clients/{id}/datasets` | F1/F2 | Canonical merged dataset (latest sync) |
| `POST` | `/clients/{id}/model-jobs` | F2 | Create training job (config in body) → `job_id` |
| `GET` | `/clients/{id}/model-jobs` | F6 | History: date, status, diagnostics summary |
| `GET` | `/model-jobs/{job_id}` | F2 | Job detail + live status |
| `POST` | `/model-jobs/{job_id}/cancel` | F2 | Cancel queued/running job (analyst+) |
| `GET` | `/model-jobs/{job_id}/diagnostics` | F2 | R-hat, R², MAPE, posterior predictive check |
| `GET` | `/model-jobs/{job_id}/contributions` | F3 | Channel contribution %, ROAS, spend |
| `GET` | `/model-jobs/{job_id}/curves` | F3 | Response curve points per channel |
| `GET` | `/model-jobs/{job_id}/decomposition` | F3 | Trend / seasonality / media time series |
| `GET` | `/model-jobs/{job_id}/forecast` | F3 | Forecast with CI bands |
| `POST` | `/model-jobs/{job_id}/allocate` | F4 | Budget constraints → allocation result |
| `GET` | `/model-jobs/{job_id}/insights` | F5 | Generated insights (or trigger generation) |
| `POST` | `/model-jobs/{job_id}/insights/generate` | F5 | Enqueue LLM insight task |
| `POST` | `/model-jobs/{job_id}/chat` | F5 | Scenario Q&A ("shift 20% from TV to Meta") |
| `POST` | `/model-jobs/{job_id}/reports` | F7 | Enqueue report generation (PDF) |
| `GET` | `/reports/{report_id}` | F7 | Report metadata + share token |
| `GET` | `/reports/share/{share_token}` | F7 | Public read (no auth) |
| `GET` | `/usage/summary` | billing | Org usage rollup (owner) |

### 6.3 Example request / response

Create a model job (F2):

```http
POST /api/v1/clients/{id}/model-jobs
Authorization: Bearer <jwt>
Idempotency-Key: 8f9c...
Content-Type: application/json

{
  "name": "Q3 weekly model",
  "config": {
    "name": "q3-weekly",
    "target_column": "revenue",
    "granularity": "week",
    "adstock_max_lag": 8,
    "saturation_beta": [1.5, 1.2, 1.8],
    "adstock_first": true,
    "sampler": "nuts",
    "draws": 1000,
    "tune": 1000,
    "chains": 4,
    "forecast_days": 90,
    "random_seed": 42
  }
}
```

Response `201 Created`:

```json
{
  "status": "ok",
  "data": {
    "id": "b4f1...",
    "client_id": "c-01...",
    "name": "Q3 weekly model",
    "status": "queued",
    "queued_at": "2026-08-01T10:00:00Z",
    "metrics": {}
  }
}
```

The client polls `GET /model-jobs/{job_id}` (SSE/polling cadence in §13).

### 6.4 Streaming (insights)

Scenario chat (F5) streams via `text/event-stream`. Each chunk is a JSON delta; for structured outputs the server reassembles deltas, validates against the Pydantic schema, and emits a final `[done]` event with the validated object.

---

## 7. Data Connectors Architecture

Canonical source: `research/data-connector-spec.md`. Implementation lives in `src/mmm/connectors/`.

### 7.1 Base interface

```python
# src/mmm/connectors/base.py
class ConnectorConfig(BaseModel):
    name: str
    enabled: bool = True
    credentials: dict[str, str] = {}   # secret references, never raw values

class DataConnector(ABC):
    def __init__(self, config: ConnectorConfig) -> None: ...
    @abstractmethod
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame: ...
    @abstractmethod
    def is_configured(self) -> bool: ...
```

- **Normalization is internal to each connector.** Output rows always match the canonical schema:

| column | type | notes |
|---|---|---|
| `date` | `datetime` | UTC; already bucketed per granularity by preprocessor |
| `channel` | `str` | `meta`, `google_ads`, `tiktok`, `shopify_revenue`, `organic`, `tv`, `radio`, ... |
| `spend` | `float` | local currency |
| `impressions` | `int` | default 0 |
| `clicks` | `int` | default 0 |
| `conversions` | `int` | default 0 |
| `revenue` | `float` | attributed/known revenue or target KPI |

- Pydantic canonical model: `MediaRecord` in `src/mmm/models/schemas.py`. A connector returns a DataFrame that is validated record-by-record into `MediaRecord` before it enters the `MMMDataset`.
- **Credentials**: stored per-tenant in `data_sources.credentials_encrypted` (AES-256-GCM, key derived from `SECRET_KEY`/KMS) or in the secret manager for org-level defaults. Never in code or `.env` for real tenants.
- **HTTP**: `httpx` async-safe; all connectors support both `async def fetch_spend_async` and a sync wrapper for Celery.
- **Resilience**: HTTP 429/5xx → exponential backoff with jitter (base 1 s, factor 2, max 60 s, 4 retries); per-connector rate-limit token bucket; connector-level timeouts (default 90 s per request).
- **Registry**: `connectors/registry.py` maps `connector_type` → class for factory use.

### 7.2 Per-platform matrix

| Connector | Priority | API / method | Auth | Key implementation notes |
|---|---|---|---|---|
| CSV upload | P0 | n/a | none | Universal fallback. Accepts file upload or pasted frame; column-mapping UI (must map to `date, channel, spend[, impressions, clicks, conversions, revenue]`); preview + validation before save |
| Shopify | P0 | Admin API (`orders` endpoint) | `X-Shopify-Access-Token` | Primary revenue source. Pull order totals, group by channel attribution (`shopify_revenue`), sum by day |
| Meta Ads | P1 | Marketing API v19+ `insights`, `time_increment=1` | OAuth2 / long-lived token | Cost in `spend`, impressions/clicks/conversions directly; map `account_id`, date preset range |
| Google Ads | P1 | `GoogleAdsService` (GAQL) | OAuth2 + developer token | `metrics.cost_micros` → `spend / 1e6`; query segments.date, campaign → normalize to `google_ads` channel |
| GA4 | P1 | Data API v1beta | service account | Organic sessions/revenue; used for `organic` / baseline control |
| TikTok | P2 | Marketing API v1.3 `report/integrated/get` | access token | Time range `YYYY-MM-DD`, report type BASIC; normalize spend/impressions/clicks/conversions |
| LinkedIn / Snap / Pinterest | P2 | respective APIs | OAuth2 | Same canonical normalization; P2 backlog |
| DV360 / TTD | P3 | DV360 API / TTD | OAuth2 | Programmatic — **V2**, not in MVP |

### 7.3 Sync lifecycle

1. User configures a data source (analyst+) → credentials encrypted → stored.
2. Manual trigger `POST .../sync` **or** scheduled sync (weekly default) enqueues `sync` Celery task.
3. Task: `fetch_spend(start=last_sync - 7d, end=now)` → normalize → validate → upsert into a per-client `datasets` table (or replace the working frame).
4. Update `data_sources.last_sync_at`; write `usage_records(api_calls, compute_seconds)`.
5. Failures update `sync_status` and surface as a warning card in the UI; retries per §7.1.

### 7.4 Control variables (model robustness)

Sourced by the preprocessor from `clients.control_columns` + `connectors/controls.py`:

- Holidays calendar (US + target markets)
- Google Trends index per category
- Pricing changes / promos (manual overrides or CSV)
- Macro indicators (CPI) and seasonality dummies (week-of-year, month)

---

## 8. MMM Engine Integration

### 8.1 Wrapper design

Canonical wrapper: `src/mmm/core/engine.py` (`MMMModel`). Thin, testable layer over PyMC-Marketing:

| Method | Purpose |
|---|---|
| `fit(dataset) -> FitResult` | Preprocess → build PyMC-Marketing `MMM` → fit (draws/tune/chains/seed) → compute diagnostics |
| `predict(data=None, n_periods=12) -> list[ForecastPoint]` | Forecast with CI bands |
| `get_channel_contributions() -> list[ChannelContribution]` | Contribution %, ROAS, spend per channel |
| `allocate_budget(total_budget, date_range, constraints) -> AllocationResult` | PyMC `allocate_budget` when sampler is `nuts`/`numpyro`; **fallback** to `allocate_budget_scipy` (constrained SciPy minimize) |
| `save(path)` / `classmethod load(path, config)` | Persist/restore artifacts (model.json, fit_data, channels) |

Key rules:

- **Lazy import** of `pymc_marketing` (module-level `_PyMC_MMM` cache) so API import stays fast and workers import it on demand.
- **Sampler**: `"nuts"` (PyMC) or `"numpyro"` (GPU). `numpyro` on GPU targets for the <2 min SLA.
- **Defaults** (matching `ModelConfig` in `src/mmm/models/schemas.py`): granularity `week`, adstock `max_lag=8`, saturation beta default `1.5` per channel, `adstock_first=True`, draws 1000, tune 1000, chains 4, seed 42, forecast 90 days.
- `FitResult.status in {"ok","failed"}`; failures are caught, logged, and returned with `error` — the job wraps this.

### 8.2 Diagnostics (F2)

`compute_diagnostics()` returns `ModelDiagnostics`:

| Field | Source |
|---|---|
| `converged` | all `rhat < 1.1` |
| `rhat_max` | max Gelman-Rubin over params |
| `r2` | R² on in-sample predictions |
| `mape` | mean absolute percentage error |
| `warnings` | e.g., "channel X has >90% zero spend", "low R²", "chain did not converge" |

Posterior predictive check (PPC) plot is exposed via the diagnostics endpoint for the UI.

### 8.3 Job lifecycle (F2)

```
user submits config
      │
      ▼
POST /model-jobs ──► model_jobs row created (status=queued, queued_at)
      │
      ▼  (Celery training queue)
task: preprocess (validate, aggregate, controls)
      │
      ├── failed  → status=failed, error written, job finished_at
      │
      ▼  (status=running, started_at)
MMMModel.fit(draws, tune, chains, seed)
      │
      ├── failed  → status=failed (+ diagnostics.warnings if partial)
      │
      ▼  (status=running)
diagnostics (rhat/r2/mape/ppc)
      │
      ▼
artifact upload (local | s3 | r2) ──► artifact_key stored
      │
      ▼
status=succeeded, finished_at, result_summary, metrics
      │
      ▼
optional: auto-enqueue insights task (analyst default: yes)
      │
      ▼
write usage_records(compute_seconds, storage_mb, model_train)
```

- **Cancel**: `POST /model-jobs/{id}/cancel` sets a cancellation flag checked between sampling phases; running PyMC sampling cannot be interrupted mid-iteration — cancel applies at phase boundaries.
- **Retry**: a failed job may be retried (re-queued) without resubmitting the full config.
- **Determinism**: `random_seed` is configurable; default 42 makes local reproduction and testing deterministic.

### 8.4 Budget optimizer (F4)

`BudgetConstraints` (schemas.py): `total_budget`, `min_per_channel_pct`, `max_per_channel_pct`, `channel_bounds {channel: (min, max)}`, `channel_floors {channel: $}`.

Flow: try `_fitted_model.allocate_budget(budget, date_start, date_end)` for NUTS/numpyro models → on any exception, fall back to `allocate_budget_scipy` which maximizes expected revenue over channel budgets subject to the constraints. Output: `AllocationResult{total_budget, allocations[{channel, allocated_budget, share, expected_revenue}], expected_total_revenue}` with `is_feasible` guard (within 1%).

---

## 9. LLM Integration

Canonical source: `research/ai-insights-layer.md`. Implementation evolves in `src/mmm/ai/`.

### 9.1 LLMProvider protocol

```python
# src/mmm/ai/providers.py
from typing import Protocol, AsyncIterator

class LLMProvider(Protocol):
    async def complete(self, req: ChatRequest) -> ChatResponse: ...
    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]: ...
    async def extract(self, req: ChatRequest, schema: type[BaseModel]) -> BaseModel: ...
```

- **Pydantic at every boundary.** Raw LLM output is never trusted; `extract` re-validates with `schema.model_validate(...)` and raises on failure (caller falls back to template).
- Three concrete providers:

| Provider | SDK | Notes |
|---|---|---|
| `OpenAIProvider` | `openai` | **One class serves both OpenAI and Ollama** — Ollama exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`; pass `base_url` per tenant setting. Structured output via `response_format={type:"json_schema", ...}`. |
| `AnthropicProvider` | `anthropic` (native) | **Never** use Anthropic's OpenAI-compat endpoint for structured output — it ignores `response_format`. Use native `messages.create` with JSON-schema tool/structured mode. |
| `OllamaProvider` | `ollama` HTTP `/api/chat` | Direct Ollama path used by the local/dev scaffold; production routes Ollama through `OpenAIProvider` with `base_url` (or direct HTTP). Uses `format=<full JSON schema>` (schema-mode), `temperature 0–0.1`. |

- **Rejected** in research: LiteLLM (12 transitive deps), LangChain (version coordination), Vercel AI SDK (TS-first). Revisit LiteLLM only if proxy/spend-tracking/100+ providers are needed.

### 9.2 Tenant override

```python
tenant_llm_settings(org_id) -> LLMSettings:
    provider: str          # ollama | openai | anthropic
    model: str
    base_url: str | None   # e.g., Ollama on tenant GPU
    api_key_ref: str       # secret reference, NEVER a raw key
```

`api_key_ref` resolves through the secret manager at call time. Defaults come from `Settings` (`llm_provider=ollama`, `ollama_model=qwen2.5:7b`).

### 9.3 Ollama model tiers (deep-research findings)

| Tier | Model | Size (Q4_K_M) | Notes |
|---|---|---|---|
| Default (budget) | Qwen2.5-7B-Instruct | ~5 GB VRAM | Explicit JSON/table training, 128K ctx, fits RTX 3090/4090 with 2–3 parallel |
| Ultra-budget | Qwen3-4B | ~2.5 GB | Fallback when VRAM tight |
| Premium | Qwen2.5-32B-Instruct | ~19–20 GB | RTX 4090 24 GB with `OLLAMA_KV_CACHE_TYPE=q4_0`, `num_ctx` 4096–8192 |
| Throughput alt | Qwen2.5-14B | ~11 GB | Q5_K_M, 2–4 parallel |
| JSON-reliability alt | Mistral Small 24B | ~14 GB | Competitive with GPT-4o-mini on structured output |

**Production serving** (Ollama has no built-in rate limiting — put behind nginx):

```
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_KV_CACHE_TYPE=q4_0
OLLAMA_FLASH_ATTENTION=1
OLLAMA_NUM_PARALLEL=2-3
OLLAMA_CONTEXT_LENGTH=8192
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=-1          # preload both tiers
```

Scale-out: one Ollama per GPU + app-level round-robin. Recommended request settings: `temperature 0–0.1`, `num_ctx` 8192–16384 (7B) / 4096–8192 (32B).

### 9.4 Insight types (F5)

| `insight_type` | Content | Example |
|---|---|---|
| `channel_performance` | ROAS, contribution share, trends | "Meta drives 42% of revenue at 3.4x ROAS, up 0.6x QoQ" |
| `budget_recommendation` | Reallocation + expected revenue impact | "Shift 20% of TV budget to Meta; expected +$12k/mo" |
| `anomaly` | spend/CPM/ROAS deviations | "Spend on Google up 31% week-over-week with flat ROAS" |
| `benchmark` | vs industry averages | "Your search ROAS is 18% above industry median" |
| `summary` | executive narrative | Full narrative for the report |

Generation runs in a Celery task (`ai/insights.py`) per model job; results stored in `insights` with `source="llm"` or `source="template"`.

### 9.5 Guardrails

- Always cite numbers from model output; never fabricate metrics (prompts inject the actual `ChannelContribution`/`AllocationResult`/diagnostics JSON).
- Include confidence intervals where available.
- **Template fallback**: if the provider errors, times out (>60 s), or `extract` validation fails, `report._fallback_report` produces deterministic insights from the same JSON. The UI shows a "generated from templates" badge.
- Scenario Q&A: the LLM receives the client's model context (contributions, allocation result, constraints) + question; it may only operate on provided numbers; answer is re-validated and streamed via SSE (§6.4).

---

## 10. Model Artifact Storage

### 10.1 Backends

`Settings.model_storage_backend in {"local", "s3", "r2"}` — implemented by `src/mmm/storage/{local,s3,r2}.py` behind an `ArtifactStore` protocol:

| Backend | Use | Notes |
|---|---|---|
| `local` | dev / tests | `MODEL_STORAGE_PATH` on disk; never in production |
| `s3` | production | AWS S3 bucket + optional lifecycle rules |
| `r2` | production (cost) | Cloudflare R2, S3-compatible API via `boto3`/`s3fs` |

Interface: `put(key, bytes|file)`, `get(key) -> file-like`, `exists(key)`, `delete(key)`, `presign_url(key, ttl) -> str`.

### 10.2 Key naming (tenant + client + job)

```
s3://mmm-model-artifacts/{org_id}/{client_id}/{job_id}/
├── model.json          # PyMC-Marketing model export (params + sampling config)
├── fit_data.pkl        # processed training frame (channels × time)
├── channels.pkl        # channel column list
├── idata.nc            # ArviZ InferenceData (posterior + posterior_predictive) — primary trace artifact
├── diagnostics.json    # ModelDiagnostics
├── contributions.json  # ChannelContribution[]
├── summary.json        # FitResult + metrics + config snapshot
└── metadata.json       # {job_id, org_id, client_id, model_name, created_at, pymc_marketing_version, python_version}
```

### 10.3 Versioning

- **Job-scoped keys** (above) mean every run is a distinct immutable version. Immutability = never overwrite an existing `{job_id}/` prefix; new run = new `job_id`.
- `model_jobs.artifact_key` points at the latest successful run's prefix. "Save/load model artifacts" (F2) resolves via that pointer, so a re-train creates a new version without destroying history.
- **Retention** (MVP): keep all successful jobs; lifecycle policy for failed jobs' partial artifacts (delete after 30 days). Enterprise tier can pin/archive.
- **Reproducibility**: `metadata.json` records package versions + `random_seed`; workers pin `pymc_marketing`, `pymc`, `arviz` versions in the image (lockfile).

---

## 11. Background Jobs (Celery)

### 11.1 Topology

- **Broker**: Redis (`REDIS_URL`), also the result backend (short TTL).
- **Worker image** shares the backend codebase; separate CLI flags select which queues a worker consumes.
- Celery config in `src/mmm/jobs/celery_app.py`.

### 11.2 Queues and priorities

| Queue | Routing key | Priority | Consumes | Purpose | Task example |
|---|---|---|---|---|---|
| `default` | `celery` | low | default worker | maintenance, lightweight jobs | usage rollups, retry bookkeeping |
| `training` | `train.*` | high | worker + GPU (if available) | model training | `train_model_job(job_id)` |
| `connectors` | `sync.*` | normal | connector worker | data sync + LLM control pulls | `sync_data_source(ds_id)` |
| `insights` | `insights.*` | normal | LLM worker | NL insight generation, scenario Q&A | `generate_insights(job_id)`, `answer_scenario(job_id, q)` |
| `reports` | `reports.*` | low | report worker | PDF rendering + email/share link | `render_report(report_id)` |

Priority semantics: separate queues + per-queue concurrency; `task_acks_late=True` and `prefetch_multiplier=1` so long jobs are acked only on success and don't monopolize workers.

### 11.3 Task specifications

| Task | Timeout | Retries | Notes |
|---|---|---|---|
| `train_model_job` | 1200 s (20 min) hard; SLA < 5 min CPU / < 2 min GPU | 1 retry on transient infra errors; never on modeling failure | Phase-boundary cancellation (§8.3) |
| `sync_data_source` | 600 s | 3 (exponential backoff, respects connector 429 policy) | Idempotent upsert |
| `generate_insights` | 300 s | 1 | Falls back to templates on LLM failure |
| `answer_scenario` | 120 s | 0 (stream to client) | SSE; client resends on drop |
| `render_report` | 600 s | 1 | PDF via `reportlab`/`weasyprint` |

- **Task results**: only the job id + final status; heavy payloads live in the DB (`model_jobs`, `insights`, `reports`).
- **Chains**: `train → insights` composed via Celery chain; `sync → recompute dataset` optional.
- **Observability**: every task emits structured logs with `job_id`, `client_id`, `org_id`, duration; task events (`task-received/started/succeeded/failed`) wired to monitoring (§15).

### 11.4 Rate limiting (workers ↔ external APIs)

Workers respect per-connector token buckets; LLM worker uses a provider rate limiter (e.g., 10 requests/min default, configurable) so Ollama on a single GPU is not saturated by the app.

---

## 12. Security Requirements

### 12.1 OWASP Top 10 mapping

| OWASP | Control in MMM Platform |
|---|---|
| A01 Broken Access Control | RBAC (§5.2) enforced in `deps.py`; RLS as second layer; `share_token` scoped to one report |
| A02 Cryptographic Failures | TLS 1.2+ everywhere; credentials AES-256-GCM server-side; secrets in env/secret manager only; no keys in code or client bundles |
| A03 Injection | All SQL via SQLAlchemy/PostgREST (parameterized); LLM prompts injected only with server-validated numeric data; CSV parsing escapes formula injection (`=`/`+`/`-`/`@` cells) |
| A04 Insecure Design | Threat model: tenant isolation boundaries, token rotation, least-privilege service roles |
| A05 Security Misconfiguration | Default-deny CORS (allowlist: Vercel origin + localhost dev), no debug endpoints in prod, `SECRET_KEY` forced rotation, container non-root user |
| A06 Vulnerable Components | `pip-audit` + `npm audit` in CI; Dependabot/renovate; pinned base images |
| A07 Auth failures | Supabase Auth JWT validation with signature check on the API; refresh-token rotation; brute-force protection on auth routes |
| A08 Software/Data integrity | No client-uploaded code; CSV/PDF rendered server-side; signed/locked dependency files |
| A09 Logging/monitoring failures | Structured logs + Sentry (§15); auth + model-job + sync events logged with org/user context |
| A10 SSRF | Connector base URLs fixed per connector; redirects disabled; no user-supplied URLs fetched by the backend; outbound egress allowlist in prod |

### 12.2 Secrets

- Never hardcode. `.env` for local dev (git-ignored); Railway/Fly.io env or a secret manager (Vault/Doppler) in production.
- `credentials_encrypted` in `data_sources`: encrypt at rest with AES-256-GCM; key from `SECRET_KEY` (dev) or KMS-managed key (prod); key id stored alongside ciphertext for rotation.
- `api_key_ref` indirection for LLM keys (§9.2).

### 12.3 Rate limiting and abuse

- API: per-user token bucket via Redis (default 120 req/min; burst 200). Stricter on `POST` endpoints (train/sync/report: 10/min).
- Auth routes: 10/min per IP + email lockout after 5 failed attempts (Supabase handles reset/built-ins).
- Uploads: CSV size ≤ 25 MB, ≤ 5k rows, file-type sniffing (reject executables/macros).
- Share-token endpoints: 30 req/min per IP.

### 12.4 RLS recap

RLS (§4.4) is a defense-in-depth backstop. The **application** enforces org/role scoping on every query; RLS guarantees a compromised or buggy query cannot cross tenants. Service-role key stays server-side only.

### 12.5 Data protection notes

- PII minimization: email stored for auth; report share tokens are anonymous.
- Right-to-delete: deleting an org cascades to clients, jobs, artifacts (S3 delete with lifecycle), and usage records; Supabase user record removed via admin API.

---

## 13. Performance Requirements

### 13.1 Model training SLA (from spec)

| Metric | Target |
|---|---|
| Time to first model (CSV upload → trained) | **< 15 min** (end-to-end, including upload + queue wait) |
| Training, CPU (4 chains, 1000 draws, weekly, ≤ 8 channels) | **< 5 min** |
| Training, GPU (`numpyro`) | **< 2 min** |
| R² (ecommerce datasets) | **> 0.7** |
| Model job API call overhead (queued → running visible) | < 2 s |

Enforcement: default `draws=1000/tune=1000/chains=4` balanced against SLA; on CPU, `numpyro` fallback not auto-used — the analyst can opt in. Training queue concurrency tuned so N concurrent jobs still meet the p95 "time to first model".

### 13.2 API latency targets (p95)

| Endpoint class | Target (p95) |
|---|---|
| Health / auth | < 50 ms |
| List/detail reads (dashboard, clients, model history) | < 150 ms |
| Diagnostics / contributions / forecast reads (from stored JSON) | < 300 ms |
| Budget allocation (scipy or PyMC) | < 2 s (cached per constraint set, 10-min TTL) |
| CSV upload parse + validate | < 5 s (≤ 5k rows) |
| Insight generation (LLM) | async; template < 2 s, LLM p95 < 60 s |
| Scenario Q&A first token | < 3 s |

Mitigations: TanStack Query caching + SWR, JSONB result snapshots (`model_jobs.result_summary`, `contributions.json`), materialized dashboard rollups refreshed post-training, pagination on all list endpoints.

### 13.3 Capacity assumptions (MVP launch)

- 5 agencies × 3–15 clients; worst case ~10 orgs, 100 clients, 100 model trains/month peak.
- Training jobs peak 4–8 concurrent; one medium CPU worker (8 vCPU) + optional one GPU worker; 2 connector workers; 1 LLM worker (Ollama GPU or hosted API).

---

## 14. Infrastructure / Deployment

### 14.1 Environments

| Env | Purpose | Frontend | Backend | DB |
|---|---|---|---|---|
| `dev` | local | `next dev` (localhost:3000) | `uvicorn` (localhost:8000) | Supabase local (`supabase start`) or project |
| `staging` | pre-prod | Vercel preview | Railway/Fly.io staging | Supabase preview DB (branch) |
| `prod` | live | Vercel prod | Railway/Fly.io prod | Supabase prod project |

### 14.2 Containers

Backend Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -m app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src ./src
COPY alembic ./alembic
USER app
EXPOSE 8000
CMD ["uvicorn", "mmm.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Worker entrypoint (`celery -A mmm.jobs.celery_app worker -Q training,connectors,insights,reports -n mmm-worker@%h`); separate queues via worker flags per service.

`docker-compose.yml` (dev): `api`, `worker`, `redis`, `ollama` (optional, mounted GPU).

### 14.3 Hosting matrix

| Service | Host | Config |
|---|---|---|
| Frontend | Vercel | Next.js 15 preset; env: `NEXTAUTH_SECRET`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `API_BASE_URL` |
| Backend | Railway or Fly.io | Web service `uvicorn` (2 replicas MVP); attach volume only for `local` storage in dev |
| Workers | Railway/Fly.io worker services | One per queue group; GPU machine for `training`+`insights` when using Ollama |
| Redis | Upstash / Railway managed Redis | TLS, `REDIS_URL` |
| DB + Auth | Supabase | Region nearest to API; RLS + migrations applied via CI |
| Object storage | R2 (default for cost) or S3 | Bucket private; presigned URLs, CORS not needed (server-side) |
| Ollama | Self-host GPU host (or cloud GPU) | nginx TLS + rate limit in front (§9.3) |

### 14.4 CI/CD

- GitHub Actions: lint (ruff, isort, black --check, eslint), type check (mypy, tsc), unit + integration tests (`pytest --cov=src` target ≥ 80%), `pip-audit` + `npm audit`, build images, run Alembic migrations against staging, deploy on merge to main.
- Rollbacks: Railway/Fly.io keep previous deploy; Vercel instant rollback.

---

## 15. Monitoring and Observability

### 15.1 Error tracking

- **Sentry** (Python SDK + Next.js SDK): capture unhandled exceptions, 4xx/5xx, task failures; tag with `org_id`, `client_id`, `job_id`, `task`. DSN from env, never bundled to the client.
- Breadcrumbs on job lifecycle and LLM calls (provider, model, latency, token count).

### 15.2 Product analytics

- **PostHog**: frontend pageviews + key events (`model_train_started`, `model_train_succeeded/failed`, `report_exported`, `insight_generated`, `scenario_asked`); capture `org_id` (post-anonymization where needed).

### 15.3 Health checks

`GET /health` returns component status:

```json
{
  "status": "ok",
  "time": "2026-08-01T10:00:00Z",
  "components": {
    "database": "ok",
    "redis": "ok",
    "storage": "ok",
    "llm_provider": "ok",          // 1 lightweight ping (5s timeout); degraded if down
    "celery_worker_heartbeat": 42  // seconds since last heartbeat
  }
}
```

Readiness for Railway/Fly.io uses this endpoint (fail → restart). Worker heartbeat stored in Redis (`heartbeat:<worker>` TTL 60 s) to detect dead workers.

### 15.4 Metrics and logs

- Structured JSON logs (Python `logging` with a formatter; task context in `extra`). Centralized via Railway/Fly.io log drains (or Papertrail/Loki).
- Prometheus scrape endpoint (`/metrics`) at the API and per-worker: job durations, queue depths (Redis `LLEN`), training success rate, LLM latency/token usage, API request p50/p95, 429 rate.
- Alerts (MVP): training job failed rate > 5% over 1h; `train_model_job` duration > 10 min p95; `GET /health` returning non-ok; LLM provider error rate > 10%.

---

## Appendix A — Cross-reference to spec features

| Spec feature | Sections in this TRD |
|---|---|
| F1 Data Connectors | §7, §4.2, §11.2 |
| F2 MMM Model Training | §8, §6.2, §10 |
| F3 Channel Attribution | §8.1, §6.2 |
| F4 Budget Optimizer | §8.4, §6.2 |
| F5 AI Insights (NL) | §9, §6.4 |
| F6 Multi-Client Dashboard | §2.3, §6.2 |
| F7 Reports & Export | §6.2, §7.3, §9.4 |
| Data model / usage | §4, §6.1 |
| Success metrics / SLAs | §13 |

## Appendix B — Non-goals (out of scope, MVP)

- Incrementality test calibration, A/B test integration, programmatic (DV360/TTD) connectors, white-label branding, SSO (SAML), Stripe billing, audit log, multi-geo MMM, mobile app — **V2/later**.
- MTA/pixel tracking, social media scheduling, creative tools, ad builder, SEO tools — **not building**.

## Appendix C — Key design decisions (ADR summary)

1. **Thin PyMC-Marketing wrapper** (no custom sampler code) — speed to correct Bayesian MMM; override points preserved via config + scipy fallback.
2. **Protocol-based LLM layer, OpenAIProvider serving both OpenAI and Ollama via `base_url`** — Ollama exposes an OpenAI-compatible endpoint; one code path, minus Anthropic which requires its native SDK for structured output.
3. **Qwen2.5-7B as default LLM** (Apache 2.0, JSON/table-trained) with template fallback as the product's floor.
4. **Job-scoped immutable artifacts + pointer** (`artifact_key`) — reproducibility and multi-version history without a version server.
5. **RLS + application RBAC** — tenant isolation is enforced at both layers.
6. **Reject LiteLLM/LangChain/Vercel AI SDK** — 3 providers don't justify the dependency weight.
