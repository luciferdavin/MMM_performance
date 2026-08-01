# Implementation Plan: MMM Platform

**Version:** 1.0
**Date:** 2026-08-01
**Author:** Senior Full-Stack Engineer & Project Manager
**Status:** Active

---

## Executive Summary

This document defines a phased implementation plan for the MMM Platform — an AI-powered, agency-first Marketing Mix Modeling SaaS. The plan spans 9 phases (Phase 0 through Phase 8), covers the full stack from repository setup to production deployment, and is designed so an AI coding agent can execute each phase with concrete file paths, verification criteria, and dependency chains.

**Total estimated duration:** 42–56 working days (single engineer) or 20–28 days with two parallel engineers.

**Key design decisions carried from spec:**
- Backend: Python 3.11 + FastAPI
- Frontend: Next.js 15 + React 19 + Tailwind + shadcn/ui
- Database: Supabase (PostgreSQL + RLS + Auth)
- Job queue: Celery + Redis
- MMM engine: PyMC-Marketing
- LLM: Ollama default (Qwen2.5-7B), pluggable Claude + OpenAI via `LLMProvider` protocol
- Deployment: Vercel (frontend) + Railway (backend) + Supabase (DB)

---

## Current State Assessment

The repository already contains meaningful scaffolding from prior phases:

| Component | Status | Notes |
|-----------|--------|-------|
| Python package (`src/mmm/`) | Scaffolded | Core engine, preprocessor, optimizer, diagnostics, config, CLI, connectors (CSV, Meta, Google, GA4, TikTok, Shopify), AI layer (providers, insights, reports, prompts), models/schemas, API stub |
| Frontend (`app/`) | Skeleton only | Next.js 15 with 4 placeholder pages (dashboard, clients, optimize, reports), hardcoded KPI cards, no real data fetching |
| Tests | Minimal | 3 test files (optimizer, preprocessor, schemas) |
| Docker | Basic | Dockerfile + docker-compose.yml (api, redis, ollama) |
| Supabase | Directory exists | No migrations yet |
| CI/CD | None | No GitHub Actions |
| Docs | PRD complete | TRD, app-flow, UI/UX brief, backend-schema are placeholders |

**This plan builds on the existing scaffolding and fills every gap to reach a deployable MVP.**

---

## Phase Breakdown

---

### Phase 0: Project Setup & Infrastructure Scaffolding

**Duration:** 2–3 days
**Dependencies:** None (starting phase)

#### Objectives

Establish a production-ready monorepo with CI/CD, linting, formatting, and a repeatable local development workflow.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| Monorepo structure | Clear separation: `src/mmm/` (Python backend), `app/` (Next.js frontend), `supabase/` (migrations), `docs/` |
| Python environment | `pyproject.toml` updated with all dependencies (Celery, Redis, Supabase client, ArviZ, boto3, etc.) |
| Frontend environment | `app/package.json` updated with shadcn/ui, TanStack Query, zod, next-auth, tailwind-merge, clsx |
| Pre-commit hooks | Ruff linting + formatting for Python; Prettier + ESLint for TypeScript |
| CI/CD skeleton | GitHub Actions: lint, type-check, test for both Python and TypeScript on push/PR |
| Environment config | `.env.example` completed; `.env.local` template for frontend; `docker-compose.yml` for local dev |
| Database client setup | `supabase` CLI installed; initial migration directory structure |

#### Files to Create/Modify

```
# Python environment
pyproject.toml                          # MODIFY: add celery, redis, supabase, arviz, boto3, cryptography deps
requirements-dev.txt                    # CREATE: pinned dev dependencies

# Frontend environment
app/package.json                        # MODIFY: add shadcn/ui, @tanstack/react-query, zod, clsx, tailwind-merge
app/tailwind.config.ts                  # MODIFY: extend with shadcn theme tokens
app/components.json                     # CREATE: shadcn/ui configuration
app/tsconfig.json                       # MODIFY: path aliases (@/components, @/lib, @/hooks)

# CI/CD
.github/workflows/ci.yml               # CREATE: Python lint + test + TypeScript build + test
.github/workflows/deploy.yml            # CREATE: Vercel (frontend) + Railway (backend) deploy on merge to main

# Pre-commit
.pre-commit-config.yaml                 # CREATE: ruff, prettier, eslint hooks

# Docker
docker-compose.yml                      # MODIFY: add volumes, health checks, env_file references
Dockerfile                              # MODIFY: multi-stage build for smaller image

# Dev tooling
.vscode/settings.json                   # CREATE: recommended extensions, formatting settings
.vscode/extensions.json                 # CREATE: Python + TypeScript recommended extensions

# Documentation
docs/02-trd.md                          # REWRITE: technical reference document
docs/03-app-flow.md                     # REWRITE: user flow diagrams
docs/04-uiux-brief.md                   # REWRITE: UI/UX design brief
docs/05-backend-schema.md               # REWRITE: database schema reference
```

#### Verification Criteria

- [ ] `pip install -e ".[dev,api]"` succeeds without errors
- [ ] `cd app && npm install && npm run build` succeeds
- [ ] `ruff check src/` passes with zero warnings
- [ ] `pytest tests/ -v` passes
- [ ] `pre-commit run --all-files` passes
- [ ] `docker compose up -d` starts api, redis, and ollama services
- [ ] CI pipeline runs green on a test push

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Dependency version conflicts between PyMC-Marketing and Celery | Medium | Pin compatible versions; test in isolated venv |
| Ollama image too large for CI | Low | Use `ollama/ollama:latest`; cache in CI |
| shadcn/ui v2 breaking changes | Low | Pin to specific version; test component installation early |

---

### Phase 1: Database Schema + Authentication

**Duration:** 4–5 days
**Dependencies:** Phase 0

#### Objectives

Create a fully typed, multi-tenant database schema in Supabase with Row-Level Security policies, and wire up authentication via Supabase Auth + NextAuth.js.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| Supabase project | Pro tier project created; connection strings configured |
| Database migrations | All core tables created via SQL migrations |
| RLS policies | Per-table policies enforcing org_id membership + role-based access |
| Supabase Auth | Email/password + Google OAuth sign-up/sign-in |
| NextAuth.js integration | Session management in Next.js with Supabase JWT |
| API auth middleware | FastAPI dependency that validates JWT and extracts org_id, user_id, role |
| Seed script | Development seed data (1 org, 2 users, 2 clients) |

#### Database Schema (Tables)

```sql
-- Organizations (agencies)
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  logo_url TEXT,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Users (profiles mirroring auth.users)
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_login_at TIMESTAMPTZ,
  UNIQUE(email)
);

-- Organization memberships
CREATE TABLE memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('agency_owner', 'analyst', 'viewer')),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, user_id)
);

-- Clients (belong to org)
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  industry TEXT,
  website TEXT,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Data sources (per client)
CREATE TABLE data_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  connector_type TEXT NOT NULL CHECK (connector_type IN (
    'csv', 'meta_ads', 'google_ads', 'ga4', 'tiktok', 'shopify'
  )),
  status TEXT DEFAULT 'pending' CHECK (status IN ('active', 'error', 'pending', 'disabled')),
  config JSONB NOT NULL DEFAULT '{}',          -- connector-specific config
  credentials_encrypted BYTEA,                 -- encrypted credentials
  last_sync_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Canonical data (normalized marketing data)
CREATE TABLE marketing_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  data_source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  channel TEXT NOT NULL,
  spend NUMERIC(12,2) DEFAULT 0,
  impressions BIGINT DEFAULT 0,
  clicks BIGINT DEFAULT 0,
  conversions BIGINT DEFAULT 0,
  revenue NUMERIC(12,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Model jobs (training runs)
CREATE TABLE model_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'queued' CHECK (status IN (
    'queued', 'running', 'succeeded', 'failed', 'canceled'
  )),
  config JSONB NOT NULL,                       -- model config snapshot
  result_summary JSONB,                        -- R², MAPE, channel contributions, etc.
  artifact_key TEXT,                           -- S3/R2 path to NetCDF trace
  celery_task_id TEXT,
  error TEXT,
  duration_seconds NUMERIC(8,2),
  created_at TIMESTAMPTZ DEFAULT now(),
  finished_at TIMESTAMPTZ
);

-- Channel results (per-model channel attribution)
CREATE TABLE channel_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  model_job_id UUID REFERENCES model_jobs(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  contribution DOUBLE PRECISION NOT NULL,
  share DOUBLE PRECISION NOT NULL,
  roas DOUBLE PRECISION NOT NULL,
  spend DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(model_job_id, channel)
);

-- Budget optimizations (constraint config + allocation results)
CREATE TABLE budget_optimizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  model_job_id UUID REFERENCES model_jobs(id) ON DELETE CASCADE,
  constraints JSONB NOT NULL,
  allocations JSONB NOT NULL,
  total_budget DOUBLE PRECISION NOT NULL,
  expected_total_revenue DOUBLE PRECISION NOT NULL,
  is_feasible BOOLEAN NOT NULL,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Reports (generated per model run)
CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_job_id UUID REFERENCES model_jobs(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  content JSONB NOT NULL,                      -- structured report content
  share_token TEXT UNIQUE,                     -- public link token
  share_expires_at TIMESTAMPTZ,
  pdf_path TEXT,                               -- S3/R2 path to generated PDF
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Usage records (for billing)
CREATE TABLE usage_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  metric_type TEXT NOT NULL CHECK (metric_type IN (
    'model_train', 'data_sync', 'report_generate', 'api_call'
  )),
  quantity NUMERIC(10,2) NOT NULL,
  metadata JSONB DEFAULT '{}',
  recorded_at TIMESTAMPTZ DEFAULT now()
);

-- Tenant LLM settings (per-org LLM provider config)
CREATE TABLE tenant_llm_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'ollama' CHECK (provider IN ('ollama', 'openai', 'anthropic')),
  model TEXT NOT NULL DEFAULT 'qwen2.5:7b',
  base_url TEXT,
  api_key_encrypted TEXT,
  temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
  max_tokens INTEGER NOT NULL DEFAULT 2048,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id)
);

-- Insights (AI-generated per-model insights)
CREATE TABLE insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  model_job_id UUID REFERENCES model_jobs(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  metrics JSONB DEFAULT '{}',
  source TEXT NOT NULL DEFAULT 'llm' CHECK (source IN ('llm', 'template')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_memberships_org ON memberships(org_id);
CREATE INDEX idx_memberships_user ON memberships(user_id);
CREATE INDEX idx_clients_org ON clients(org_id);
CREATE INDEX idx_data_sources_client ON data_sources(client_id);
CREATE INDEX idx_data_sources_org ON data_sources(org_id);
CREATE INDEX idx_marketing_data_client_date ON marketing_data(client_id, date);
CREATE INDEX idx_marketing_data_client_channel ON marketing_data(client_id, channel);
CREATE INDEX idx_model_jobs_client ON model_jobs(client_id, created_at DESC);
CREATE INDEX idx_model_jobs_org_status ON model_jobs(org_id, status);
CREATE INDEX idx_model_jobs_status ON model_jobs(status) WHERE status IN ('queued', 'running');
CREATE INDEX idx_channel_results_job ON channel_results(model_job_id);
CREATE INDEX idx_channel_results_client ON channel_results(client_id, created_at DESC);
CREATE INDEX idx_budget_optimizations_job ON budget_optimizations(model_job_id);
CREATE INDEX idx_budget_optimizations_client ON budget_optimizations(client_id, created_at DESC);
CREATE INDEX idx_reports_client ON reports(client_id, created_at DESC);
CREATE INDEX idx_reports_model_job ON reports(model_job_id);
CREATE INDEX idx_reports_share_token ON reports(share_token);
CREATE INDEX idx_usage_records_org ON usage_records(org_id, recorded_at DESC);
CREATE INDEX idx_tenant_llm_settings_org ON tenant_llm_settings(org_id);
CREATE INDEX idx_insights_job ON insights(model_job_id);
CREATE INDEX idx_insights_client_type ON insights(client_id, type);
```

#### RLS Policies (Pattern)

```sql
-- Example: memberships RLS
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own memberships"
  ON memberships FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "Org owners can manage memberships"
  ON memberships FOR ALL
  USING (
    org_id IN (
      SELECT org_id FROM memberships
      WHERE user_id = auth.uid() AND role = 'agency_owner'
    )
  );

-- Example: clients RLS (all org members can read; owners/analysts can write)
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Org members can read clients"
  ON clients FOR SELECT
  USING (
    org_id IN (
      SELECT org_id FROM memberships WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Owners and analysts can manage clients"
  ON clients FOR ALL
  USING (
    org_id IN (
      SELECT org_id FROM memberships
      WHERE user_id = auth.uid() AND role IN ('agency_owner', 'analyst')
    )
  );

-- Apply the same pattern to: data_sources, marketing_data, model_jobs, reports, usage_records
-- Each table gets SELECT for all org members, ALL for owner+analyst
-- usage_records gets SELECT for owner only
```

#### Files to Create/Modify

```
# Supabase migrations
# NOTE: The authoritative migration is supabase/migrations/001_init.sql
# (the complete schema from docs/05-backend-schema.md section 5). Phase 1
# should apply that single file. The per-table files below are optional
# references; do not create divergent DDL.
supabase/migrations/001_init.sql                      # CREATE: authoritative full schema (enums, tables, indexes, RLS) per 05-backend-schema.md
supabase/migrations/002_create_memberships.sql        # REFERENCE (covered by 001_init.sql)
supabase/migrations/003_create_clients.sql            # REFERENCE (covered by 001_init.sql)
supabase/migrations/004_create_data_sources.sql       # REFERENCE (covered by 001_init.sql)
supabase/migrations/005_create_marketing_data.sql     # REFERENCE (covered by 001_init.sql)
supabase/migrations/006_create_model_jobs.sql         # REFERENCE (covered by 001_init.sql)
supabase/migrations/007_create_reports.sql            # REFERENCE (covered by 001_init.sql)
supabase/migrations/008_create_usage_records.sql      # REFERENCE (covered by 001_init.sql)
supabase/migrations/009_create_indexes.sql            # REFERENCE (covered by 001_init.sql)
supabase/migrations/010_rls_policies.sql              # REFERENCE (covered by 001_init.sql)
supabase/seed.sql                                     # CREATE: dev seed data

# Backend auth
src/mmm/api/deps.py                                  # CREATE: get_current_user, get_org, require_role
src/mmm/api/auth.py                                   # CREATE: Supabase JWT validation
src/mmm/db.py                                         # CREATE: Supabase client singleton
src/mmm/config.py                                     # MODIFY: add Supabase settings

# Frontend auth
app/app/providers.tsx                                 # CREATE: QueryClientProvider + SessionProvider
app/app/(auth)/login/page.tsx                         # CREATE: login page
app/app/(auth)/register/page.tsx                      # CREATE: registration page
app/app/(auth)/layout.tsx                             # CREATE: auth layout (no nav)
app/lib/supabase.ts                                   # CREATE: Supabase browser client
app/lib/auth.ts                                       # CREATE: NextAuth configuration
app/hooks/use-auth.ts                                 # CREATE: useUser, useOrg hooks
app/middleware.ts                                      # CREATE: auth route protection

# Tests
tests/test_auth.py                                    # CREATE: JWT validation tests
tests/test_db_schema.py                               # CREATE: schema consistency tests

# Environment
.env.example                                          # MODIFY: add NEXTAUTH_SECRET, NEXTAUTH_URL
app/.env.local.example                                # CREATE: frontend env template
```

#### Verification Criteria

- [ ] All migrations run successfully: `supabase db push`
- [ ] `supabase status` shows all services running
- [ ] RLS prevents cross-org data access (verified by test scripts)
- [ ] Sign-up creates a user in `auth.users` + membership in `memberships`
- [ ] Login returns a valid JWT with `org_id`, `user_id`, `role` claims
- [ ] FastAPI `/health` endpoint validates JWT and returns user info
- [ ] Frontend login/register pages render and submit correctly
- [ ] Unauthenticated requests to protected routes return 401

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Supabase free tier limits (500MB DB, 1GB storage) | High | Use Pro tier ($25/mo) for dev; document resource limits |
| RLS policy bugs cause data leakage | Medium | Write integration tests that verify cross-org isolation |
| JWT claim format mismatch between Supabase and FastAPI | Medium | Validate claim structure in `auth.py`; test with real tokens |
| NextAuth + Supabase integration complexity | Medium | Use `@auth/supabase-adapter`; keep auth flow simple (email + Google only) |

---

### Phase 2: Core MMM Engine (Production Hardening)

**Duration:** 4–5 days
**Dependencies:** Phase 1 (for DB integration)

#### Objectives

Harden the existing MMM engine scaffold into a production-ready, Celery-backgrounded training pipeline with persistent model artifacts and real-time progress tracking.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| Celery app | Configured with Redis broker; task autodiscovery |
| Train task | Background Celery task that trains a model, saves artifacts, writes results to DB |
| Model artifact storage | S3/R2 (or local filesystem for dev) with tenant+client keying |
| Progress tracking | Redis pub/sub or SSE for real-time training progress |
| Preprocessor pipeline | Data ingestion from `marketing_data` table, validation, feature engineering |
| Diagnostics | R-hat, R², MAPE, posterior predictive check — all persisted to `model_jobs.result_summary` |
| Optimizer | Production-ready budget optimizer wired to trained model artifacts |
| CLI | Updated CLI commands that work with the DB-persisted models |

#### Celery Task Flow

```
1. Frontend calls POST /api/models/train { client_id, config }
2. FastAPI validates auth, creates model_jobs row (status=queued)
3. FastAPI dispatches Celery task: train_model.delay(model_job_id)
4. Celery task:
   a. Updates status to running
   b. Fetches marketing_data for client_id
   c. Preprocesses data (aggregation, feature engineering)
   d. Builds MMM config from model_jobs.config
   e. Fits PyMC-Marketing model
   f. Computes diagnostics (R-hat, R², MAPE)
   g. Saves artifact to S3/R2
   h. Updates model_jobs: status=succeeded, result_summary, artifact_key
   i. Records usage
5. Frontend polls GET /api/models/{id}/status or listens to SSE
```

#### Files to Create/Modify

```
# Celery setup
src/mmm/celery_app.py                               # CREATE: Celery app configuration
src/mmm/tasks/__init__.py                            # CREATE: task registry
src/mmm/tasks/train.py                               # CREATE: train_model Celery task
src/mmm/tasks/sync_data.py                           # CREATE: sync_data_source Celery task
src/mmm/tasks/generate_report.py                     # CREATE: report generation task

# Core engine hardening
src/mmm/core/engine.py                               # MODIFY: add artifact save/load to S3
src/mmm/core/preprocessor.py                         # MODIFY: read from DB, handle edge cases
src/mmm/core/diagnostics.py                          # MODIFY: return structured dict for DB storage
src/mmm/core/optimizer.py                            # MODIFY: load model from artifact path
src/mmm/core/config.py                               # MODIFY: add validation, defaults for all fields

# Storage
src/mmm/storage/__init__.py                          # CREATE
src/mmm/storage/base.py                              # CREATE: StorageBackend protocol
src/mmm/storage/local.py                             # CREATE: local filesystem backend
src/mmm/storage/s3.py                                # CREATE: S3/R2 backend

# API endpoints (thin; logic in tasks)
src/mmm/api/main.py                                  # MODIFY: add full endpoint set
src/mmm/api/routes/models.py                         # CREATE: /api/models/* endpoints
src/mmm/api/routes/data.py                           # CREATE: /api/data/* endpoints

# Schemas
src/mmm/models/schemas.py                            # MODIFY: expand with all API request/response schemas

# Tests
tests/test_celery_tasks.py                           # CREATE: task unit tests (mock PyMC)
tests/test_engine_integration.py                     # CREATE: end-to-end engine test
tests/test_diagnostics.py                            # CREATE: diagnostic computation tests
tests/test_optimizer.py                              # MODIFY: add constraint validation tests

# CLI
src/mmm/cli.py                                       # MODIFY: add db-backed train/allocate/contributions commands
```

#### Verification Criteria

- [ ] `celery -A mmm.celery_app worker --loglevel=info` starts and discovers tasks
- [ ] `POST /api/models/train` creates a job, dispatches Celery task, returns job ID
- [ ] Training completes for sample data (5 channels, 104 weeks) in <5 min on CPU
- [ ] Model artifact is saved to storage and `artifact_key` is written to DB
- [ ] Diagnostics (R-hat, R², MAPE) are computed and stored in `result_summary`
- [ ] `GET /api/models/{id}/status` returns correct status transitions (queued -> running -> succeeded)
- [ ] `POST /api/models/{id}/allocate` loads model from artifact and returns allocation
- [ ] CLI `mmm train --client-id <uuid>` works end-to-end
- [ ] All existing tests pass; new tests cover Celery task paths

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| PyMC-Marketing training exceeds 5-min target on CPU | Medium | Preprocessing pipeline aggregates to weekly; channel count <10 recommended; progress bar with ETA |
| Celery task failure leaves orphan status | Medium | Task has try/except that writes `failed` status + `error` on any exception |
| S3/R2 credentials not configured in dev | Low | Local filesystem backend as default; S3 backend for production |
| Redis connection failures | Low | Celery retry with exponential backoff; health check endpoint |

---

### Phase 3: Data Connectors (Production)

**Duration:** 5–6 days
**Dependencies:** Phase 1 (DB), Phase 2 (Celery tasks)

#### Objectives

Wire the existing connector stubs to the database, add OAuth flows for platform connectors, implement scheduled sync via Celery Beat, and build a connector management UI.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| CSV upload endpoint | Multipart upload, schema validation, data normalization, DB insert |
| Meta Ads connector | OAuth2 flow, token refresh, insights pull, canonical normalization |
| Google Ads connector | OAuth2 flow, GAQL queries, cost_micros conversion, canonical normalization |
| GA4 connector | Service account auth, data API pull, canonical normalization |
| Shopify connector | Access token auth, orders endpoint, revenue pull |
| TikTok connector | Access token auth, report endpoint pull |
| Connector management UI | List, add, test, disconnect, schedule sync |
| Scheduled sync | Celery Beat schedule for weekly auto-pull per data source |
| Data preview | Table view of `marketing_data` for selected client + date range |

#### Connector Architecture

```python
# src/mmm/connectors/base.py
from typing import Protocol
import pandas as pd

class DataConnector(Protocol):
    async def fetch_spend(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame: ...

    def is_configured(self) -> bool: ...

    @property
    def connector_type(self) -> str: ...

# Each connector (meta_ads.py, google_ads.py, etc.) implements this protocol
# and normalizes to canonical schema: date, channel, spend, impressions, clicks, conversions, revenue
```

#### OAuth Flow (Meta Example)

```
1. User clicks "Connect Meta Ads" on frontend
2. Frontend redirects to Meta OAuth consent URL
3. User grants permission
4. Meta redirects back to /api/connectors/meta/callback?code=xxx
5. Backend exchanges code for long-lived token
6. Token encrypted and stored in data_sources.credentials_encrypted
7. Data source created with status=active
8. Initial historical data pull triggered as Celery task
```

#### Files to Create/Modify

```
# Backend - API routes
src/mmm/api/routes/connectors.py                     # CREATE: CRUD + OAuth + sync endpoints
src/mmm/api/routes/data.py                           # MODIFY: add data preview endpoint

# Backend - connectors
src/mmm/connectors/base.py                           # MODIFY: add fetch_spend signature
src/mmm/connectors/meta_ads.py                       # MODIFY: implement OAuth + API pull
src/mmm/connectors/google_ads.py                     # MODIFY: implement OAuth + GAQL queries
src/mmm/connectors/ga4.py                            # MODIFY: implement service account pull
src/mmm/connectors/shopify.py                        # MODIFY: implement orders pull
src/mmm/connectors/tiktok.py                         # MODIFY: implement report pull
src/mmm/connectors/csv_upload.py                     # MODIFY: add file validation, DB insert
src/mmm/connectors/factory.py                        # CREATE: connector factory (type -> connector class)

# Backend - OAuth
src/mmm/oauth/__init__.py                            # CREATE
src/mmm/oauth/meta.py                                # CREATE: Meta OAuth flow
src/mmm/oauth/google.py                              # CREATE: Google OAuth flow

# Backend - tasks
src/mmm/tasks/sync_data.py                           # MODIFY: implement per-connector sync task
src/mmm/tasks/celery_beat.py                         # CREATE: periodic sync schedule

# Backend - crypto
src/mmm/crypto.py                                    # CREATE: credential encryption/decryption

# Frontend
app/app/clients/[clientId]/connectors/page.tsx       # CREATE: connector management page
app/app/clients/[clientId]/connectors/components/connector-card.tsx  # CREATE
app/app/clients/[clientId]/connectors/components/add-connector-dialog.tsx  # CREATE
app/app/clients/[clientId]/data/page.tsx             # CREATE: data preview page
app/components/data-table.tsx                        # CREATE: reusable data table component

# Tests
tests/test_connectors/test_csv.py                    # CREATE: CSV upload + validation tests
tests/test_connectors/test_meta.py                   # CREATE: Meta connector tests (mock API)
tests/test_connectors/test_shopify.py                # CREATE: Shopify connector tests (mock API)
tests/test_connectors/test_sync_task.py              # CREATE: Celery sync task tests
tests/test_crypto.py                                 # CREATE: credential encryption tests
```

#### Verification Criteria

- [ ] CSV upload validates schema, normalizes to canonical format, inserts into `marketing_data`
- [ ] Meta Ads OAuth flow completes end-to-end; data source appears as "active"
- [ ] Shopify connector pulls order data and normalizes revenue
- [ ] Celery Beat triggers weekly sync for active connectors
- [ ] Connector status page shows correct status (active/error/pending) per data source
- [ ] Data preview table shows marketing data for selected client and date range
- [ ] Credentials are encrypted at rest (verified via direct DB query)
- [ ] Connector factory correctly routes `connector_type` to the right class
- [ ] All connector tests pass with mocked API responses

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| OAuth token expiration mid-sync | High | Implement token refresh logic; alert on auth failure |
| Platform API rate limits (Meta: 200 calls/hour) | High | Exponential backoff; batch requests; cache recent pulls |
| API version breaking changes (Meta Marketing API v19+) | Medium | Pin API version; abstract response parsing; monitor changelog |
| Large data volumes cause slow sync | Medium | Paginate API responses; batch DB inserts; streaming processing |
| Google Ads requires developer token approval | High | Allow manual CSV upload while waiting; document approval process |

---

### Phase 4: AI Insights Layer (Production)

**Duration:** 3–4 days
**Dependencies:** Phase 2 (engine), Phase 1 (DB)

#### Objectives

Production-harden the LLM provider abstraction, wire insights to real model outputs, add streaming support, and implement the scenario Q&A chat interface.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| LLM provider abstraction | `LLMProvider` protocol with OpenAI (serving Ollama), Anthropic implementations |
| Structured output | Pydantic validation on all LLM responses; `response_format` for JSON schemas |
| Streaming | SSE streaming for insights and chat responses |
| Channel insights | Auto-generated per-channel analysis from model diagnostics |
| Budget recommendations | NL reallocation suggestions with expected revenue impact |
| Anomaly detection | Statistical anomaly alerts on spend/CPM/ROAS deviations |
| Executive summary | One-page narrative report section |
| Scenario Q&A | Chat interface: "What if I shift 20% from TV to Meta?" |
| Template fallback | `_fallback_report` when LLM is unavailable |
| Guardrails | All insights cite actual model numbers; no fabrication |

#### LLM Provider Protocol

```python
from typing import Protocol, AsyncIterator
from pydantic import BaseModel

class ChatRequest(BaseModel):
    messages: list[dict]
    system_prompt: str
    temperature: float = 0.1
    max_tokens: int = 2048
    response_format: dict | None = None

class ChatResponse(BaseModel):
    content: str
    model: str
    usage: dict

class StreamChunk(BaseModel):
    delta: str
    finished: bool

class LLMProvider(Protocol):
    async def complete(self, req: ChatRequest) -> ChatResponse: ...
    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]: ...
    async def extract(self, req: ChatRequest, schema: type[BaseModel]) -> BaseModel: ...
```

#### Files to Create/Modify

```
# Backend
src/mmm/ai/providers.py                              # MODIFY: implement OpenAIProvider (Ollama compat) + AnthropicProvider
src/mmm/ai/insights.py                               # MODIFY: wire to real model output, add anomaly detection
src/mmm/ai/report.py                                 # MODIFY: implement full report generation with all sections
src/mmm/ai/prompts.py                                # MODIFY: add scenario Q&A prompt, anomaly detection prompt
src/mmm/ai/structured.py                             # CREATE: structured output validation utilities
src/mmm/api/routes/insights.py                       # CREATE: /api/insights/* endpoints
src/mmm/api/routes/chat.py                           # CREATE: /api/chat/* endpoints (scenario Q&A)

# Frontend
app/app/clients/[clientId]/insights/page.tsx         # CREATE: insights page
app/app/clients/[clientId]/insights/components/channel-insight-card.tsx  # CREATE
app/app/clients/[clientId]/insights/components/budget-recommendation.tsx  # CREATE
app/app/clients/[clientId]/insights/components/anomaly-alert.tsx         # CREATE
app/app/clients/[clientId]/chat/page.tsx             # CREATE: scenario Q&A chat page
app/components/chat-message.tsx                      # CREATE: chat message component
app/hooks/use-chat.ts                                # CREATE: streaming chat hook

# Tests
tests/test_ai/test_providers.py                      # CREATE: provider abstraction tests (mock LLM)
tests/test_ai/test_insights.py                       # CREATE: insight generation tests
tests/test_ai/test_report.py                         # CREATE: report generation tests
tests/test_ai/test_structured.py                     # CREATE: structured output validation tests
```

#### Verification Criteria

- [ ] Ollama provider connects to local Ollama and returns valid JSON
- [ ] Anthropic provider works when `ANTHROPIC_API_KEY` is set
- [ ] All LLM responses are validated against Pydantic schemas
- [ ] Channel insights include actual ROAS and contribution numbers from model
- [ ] Anomaly detection identifies unusual spend patterns in test data
- [ ] Executive summary generates coherent narrative from model output
- [ ] Scenario Q&A returns modeled revenue impact with confidence interval
- [ ] Template fallback produces valid report when LLM is unavailable
- [ ] Streaming works end-to-end: frontend receives SSE chunks
- [ ] All AI tests pass with mocked LLM responses

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Ollama produces invalid JSON or hallucinated metrics | High | Pydantic validation; retry with temperature=0; template fallback |
| Ollama response latency (>30s for complex prompts) | Medium | Streaming; async generation in background; cache recent insights |
| Anthropic API cost for heavy usage | Medium | Per-tenant LLM settings; usage tracking; configurable provider per org |
| Prompt injection via scenario Q&A | Low | System prompt isolation; input sanitization; max token limits |

---

### Phase 5: Backend API (Complete)

**Duration:** 4–5 days
**Dependencies:** Phases 1–4

#### Objectives

Complete all FastAPI endpoints for the full application: CRUD, training, optimization, reports, sharing, and admin operations. Add OpenAPI documentation, rate limiting, and error handling.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| Full CRUD endpoints | Organizations, clients, data sources, model jobs, reports |
| Training endpoints | Start training, check status, cancel, view results |
| Optimization endpoints | Run budget optimizer, save scenarios, compare allocations |
| Report endpoints | Generate report, get report, list reports, share link |
| Data endpoints | Upload CSV, preview data, data quality checks |
| Admin endpoints | Usage stats, org settings, team management |
| OpenAPI docs | Auto-generated Swagger UI at `/docs` |
| Error handling | Consistent error response format across all endpoints |
| Rate limiting | Per-endpoint rate limits via middleware |

#### API Endpoint Map

```
# Auth
POST   /api/auth/signup                              # Register new user
POST   /api/auth/login                               # Login (returns JWT)
GET    /api/auth/me                                   # Current user info

# Organizations
GET    /api/orgs                                     # List user's orgs
GET    /api/orgs/{id}                                # Get org details
PUT    /api/orgs/{id}                                # Update org settings

# Team
GET    /api/orgs/{id}/members                        # List members
POST   /api/orgs/{id}/members/invite                 # Invite member
PUT    /api/orgs/{id}/members/{userId}               # Update role
DELETE /api/orgs/{id}/members/{userId}               # Remove member

# Clients
GET    /api/clients                                  # List clients in org
POST   /api/clients                                  # Create client
GET    /api/clients/{id}                             # Get client details
PUT    /api/clients/{id}                             # Update client
DELETE /api/clients/{id}                             # Delete client

# Data Sources
GET    /api/clients/{id}/datasources                 # List data sources
POST   /api/clients/{id}/datasources                 # Add data source (or upload CSV)
GET    /api/datasources/{id}                         # Get data source details
DELETE /api/datasources/{id}                         # Remove data source
POST   /api/datasources/{id}/sync                    # Trigger manual sync

# Marketing Data
GET    /api/clients/{id}/data                        # Preview marketing data (paginated)
GET    /api/clients/{id}/data/summary                # Data summary stats

# Models
POST   /api/clients/{id}/models/train                # Start training job
GET    /api/clients/{id}/models                      # List model jobs
GET    /api/models/{jobId}                           # Get model job details
GET    /api/models/{jobId}/status                    # Get training status
POST   /api/models/{jobId}/cancel                    # Cancel training
GET    /api/models/{jobId}/diagnostics               # Get diagnostics
GET    /api/models/{jobId}/contributions             # Get channel contributions
GET    /api/models/{jobId}/response-curves           # Get response curves

# Optimizer
POST   /api/models/{jobId}/optimize                  # Run budget optimizer
GET    /api/models/{jobId}/scenarios                 # List saved scenarios
GET    /api/scenarios/{id}                           # Get scenario details

# Insights
GET    /api/models/{jobId}/insights                  # Get channel insights
GET    /api/models/{jobId}/insights/summary          # Get executive summary
GET    /api/models/{jobId}/anomalies                 # Get anomaly alerts
POST   /api/models/{jobId}/chat                      # Scenario Q&A (streaming)

# Reports
POST   /api/models/{jobId}/reports/generate          # Generate report
GET    /api/clients/{id}/reports                      # List reports
GET    /api/reports/{id}                              # Get report content
GET    /api/reports/{id}/pdf                          # Download PDF
GET    /api/reports/shared/{token}                    # Public shared report (no auth)

# Usage
GET    /api/orgs/{id}/usage                          # Get usage stats
```

#### Files to Create/Modify

```
# Backend
src/mmm/api/main.py                                  # MODIFY: add all routers, CORS, error handlers
src/mmm/api/deps.py                                  # MODIFY: add pagination, filtering helpers
src/mmm/api/routes/__init__.py                        # CREATE: route registry
src/mmm/api/routes/orgs.py                           # CREATE: org CRUD endpoints
src/mmm/api/routes/team.py                           # CREATE: team management endpoints
src/mmm/api/routes/clients.py                        # CREATE: client CRUD endpoints
src/mmm/api/routes/datasources.py                    # CREATE: data source CRUD + sync endpoints
src/mmm/api/routes/models.py                         # MODIFY: complete all model endpoints
src/mmm/api/routes/optimizer.py                      # CREATE: optimizer endpoints
src/mmm/api/routes/insights.py                       # MODIFY: complete insight endpoints
src/mmm/api/routes/reports.py                        # CREATE: report generation + sharing endpoints
src/mmm/api/routes/usage.py                          # CREATE: usage tracking endpoints
src/mmm/api/errors.py                                # CREATE: consistent error response format
src/mmm/api/middleware.py                             # CREATE: rate limiting, request logging

# Tests
tests/test_api/test_orgs.py                          # CREATE
tests/test_api/test_clients.py                       # CREATE
tests/test_api/test_datasources.py                   # CREATE
tests/test_api/test_models.py                        # CREATE
tests/test_api/test_optimizer.py                     # CREATE
tests/test_api/test_reports.py                       # CREATE
tests/test_api/conftest.py                           # CREATE: shared fixtures (test client, mock auth)
```

#### Verification Criteria

- [ ] `GET /docs` renders full OpenAPI documentation with all endpoints
- [ ] Every endpoint requires authentication (401 for unauthenticated requests)
- [ ] Org-scoped endpoints enforce RLS (403 for cross-org access)
- [ ] Training endpoint creates Celery task and returns job ID
- [ ] Optimizer endpoint loads model and returns allocation result
- [ ] Report generation produces structured JSON content
- [ ] Share token renders public report without authentication
- [ ] Error responses follow consistent format: `{ detail: string, code: string }`
- [ ] Rate limiting returns 429 after threshold exceeded
- [ ] All API tests pass with mocked services

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Endpoint surface area too large for single PR | High | Group by router; merge incrementally; test each group independently |
| Auth middleware performance on every request | Low | JWT validation is stateless; no DB hit on most requests |
| OpenAPI docs become outdated | Medium | Auto-generated from type annotations; CI checks OpenAPI spec |
| Rate limiting too aggressive for training endpoints | Medium | Higher limits for compute endpoints; separate rate limit tiers |

---

### Phase 6: Frontend (Complete Dashboard)

**Duration:** 8–10 days
**Dependencies:** Phases 1, 5 (API endpoints)

#### Objectives

Build the complete frontend with all pages, real data fetching, responsive layouts, and a polished UI using shadcn/ui components and Tailwind CSS.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| Design system | shadcn/ui components configured with MMM brand theme |
| Layout | Sidebar navigation, client switcher, responsive shell |
| Dashboard page | KPI cards, channel performance, recent model runs |
| Clients page | Client list, create/edit/delete, client detail |
| Connectors page | Data source management, OAuth flows, data preview |
| Training page | Model configuration form, training progress, results |
| Optimizer page | Budget optimizer form, scenario comparison |
| Insights page | Channel insights, budget recommendations, anomaly alerts |
| Chat page | Scenario Q&A chat interface with streaming |
| Reports page | Report list, generate, preview, PDF download, share link |

#### Page Structure

```
app/app/
├── layout.tsx                                    # Root layout with sidebar + client switcher
├── globals.css                                   # Tailwind base + shadcn theme
├── page.tsx                                      # Dashboard (redirects to /dashboard if authed)
├── (auth)/
│   ├── login/page.tsx
│   └── register/page.tsx
├── (dashboard)/
│   ├── layout.tsx                                # Sidebar layout
│   ├── dashboard/page.tsx                        # Agency overview + KPIs
│   ├── clients/
│   │   ├── page.tsx                              # Client list
│   │   ├── new/page.tsx                          # Create client form
│   │   └── [clientId]/
│   │       ├── page.tsx                          # Client dashboard
│   │       ├── data/page.tsx                     # Data preview
│   │       ├── connectors/page.tsx               # Connector management
│   │       ├── train/page.tsx                    # Model training
│   │       ├── models/
│   │       │   └── [jobId]/page.tsx              # Model results + diagnostics
│   │       ├── optimize/page.tsx                 # Budget optimizer
│   │       ├── insights/page.tsx                 # AI insights
│   │       ├── chat/page.tsx                     # Scenario Q&A
│   │       └── reports/
│   │           ├── page.tsx                      # Report list
│   │           └── [reportId]/page.tsx           # Report view + PDF
│   └── settings/
│       └── page.tsx                              # Org settings, team, billing
├── shared/
│   └── [token]/page.tsx                          # Public shared report (no auth)

app/components/
├── ui/                                           # shadcn/ui components
├── layout/
│   ├── sidebar.tsx                               # Main navigation sidebar
│   ├── client-switcher.tsx                       # Client context dropdown
│   ├── header.tsx                                # Top header bar
│   └── breadcrumbs.tsx                           # Breadcrumb navigation
├── dashboard/
│   ├── kpi-card.tsx                              # KPI metric card
│   ├── channel-performance-chart.tsx              # Channel bar/area chart
│   └── recent-model-runs.tsx                     # Model run timeline
├── clients/
│   ├── client-table.tsx                          # Client list table
│   └── client-form.tsx                           # Create/edit client form
├── connectors/
│   ├── connector-card.tsx                        # Data source card
│   ├── add-connector-dialog.tsx                  # Add connector modal
│   └── data-preview-table.tsx                    # Marketing data preview
├── training/
│   ├── model-config-form.tsx                     # Training configuration form
│   ├── training-progress.tsx                     # Real-time progress bar
│   └── diagnostics-panel.tsx                     # R-hat, R², MAPE display
├── optimizer/
│   ├── budget-form.tsx                           # Budget + constraint inputs
│   ├── allocation-chart.tsx                      # Current vs optimized allocation
│   └── scenario-comparison.tsx                   # Side-by-side scenario view
├── insights/
│   ├── channel-insight-card.tsx                  # Per-channel NL insight
│   ├── budget-recommendation.tsx                 # Budget reallocation text
│   ├── anomaly-alert.tsx                         # Anomaly notification
│   └── executive-summary.tsx                     # Executive summary section
├── chat/
│   ├── chat-interface.tsx                        # Chat message list + input
│   └── chat-message.tsx                          # Individual message bubble
├── reports/
│   ├── report-preview.tsx                        # Report content renderer
│   ├── report-list.tsx                           # Report history table
│   └── share-dialog.tsx                          # Share link management

app/lib/
├── supabase.ts                                   # Supabase browser client
├── auth.ts                                       # NextAuth configuration
├── api.ts                                        # API client (fetch wrapper with auth)
└── utils.ts                                      # Shared utilities (formatting, etc.)

app/hooks/
├── use-auth.ts                                   # Current user + org hooks
├── use-clients.ts                                # Client CRUD hooks
├── use-model.ts                                  # Model training + status hooks
├── use-chat.ts                                   # Streaming chat hook
└── use-data.ts                                   # Marketing data hooks
```

#### Files to Create/Modify

```
# Layout & navigation
app/app/layout.tsx                                 # MODIFY: full sidebar layout with client switcher
app/components/layout/sidebar.tsx                  # CREATE
app/components/layout/client-switcher.tsx          # CREATE
app/components/layout/header.tsx                   # CREATE
app/components/layout/breadcrumbs.tsx              # CREATE

# Dashboard
app/app/(dashboard)/dashboard/page.tsx             # CREATE
app/components/dashboard/kpi-card.tsx              # CREATE
app/components/dashboard/channel-performance-chart.tsx  # CREATE
app/components/dashboard/recent-model-runs.tsx     # CREATE

# Clients
app/app/(dashboard)/clients/page.tsx               # CREATE
app/app/(dashboard)/clients/new/page.tsx           # CREATE
app/app/(dashboard)/clients/[clientId]/page.tsx    # CREATE
app/components/clients/client-table.tsx            # CREATE
app/components/clients/client-form.tsx             # CREATE

# Connectors
app/app/(dashboard)/clients/[clientId]/connectors/page.tsx  # CREATE
app/components/connectors/connector-card.tsx       # CREATE
app/components/connectors/add-connector-dialog.tsx # CREATE
app/components/connectors/data-preview-table.tsx   # CREATE

# Training
app/app/(dashboard)/clients/[clientId]/train/page.tsx  # CREATE
app/app/(dashboard)/clients/[clientId]/models/[jobId]/page.tsx  # CREATE
app/components/training/model-config-form.tsx      # CREATE
app/components/training/training-progress.tsx      # CREATE
app/components/training/diagnostics-panel.tsx      # CREATE

# Optimizer
app/app/(dashboard)/clients/[clientId]/optimize/page.tsx  # CREATE
app/components/optimizer/budget-form.tsx           # CREATE
app/components/optimizer/allocation-chart.tsx      # CREATE
app/components/optimizer/scenario-comparison.tsx   # CREATE

# Insights
app/app/(dashboard)/clients/[clientId]/insights/page.tsx  # CREATE
app/components/insights/channel-insight-card.tsx   # CREATE
app/components/insights/budget-recommendation.tsx  # CREATE
app/components/insights/anomaly-alert.tsx          # CREATE
app/components/insights/executive-summary.tsx      # CREATE

# Chat
app/app/(dashboard)/clients/[clientId]/chat/page.tsx  # CREATE
app/components/chat/chat-interface.tsx             # CREATE
app/components/chat/chat-message.tsx               # CREATE

# Reports
app/app/(dashboard)/clients/[clientId]/reports/page.tsx  # CREATE
app/app/(dashboard)/clients/[clientId]/reports/[reportId]/page.tsx  # CREATE
app/app/shared/[token]/page.tsx                    # CREATE (public route)
app/components/reports/report-preview.tsx          # CREATE
app/components/reports/report-list.tsx             # CREATE
app/components/reports/share-dialog.tsx            # CREATE

# Settings
app/app/(dashboard)/settings/page.tsx              # CREATE

# Lib & hooks
app/lib/api.ts                                     # CREATE
app/lib/utils.ts                                   # CREATE
app/hooks/use-clients.ts                           # CREATE
app/hooks/use-model.ts                             # CREATE
app/hooks/use-chat.ts                              # CREATE
app/hooks/use-data.ts                              # CREATE

# shadcn/ui components (install one by one)
app/components/ui/button.tsx                       # CREATE (via shadcn CLI)
app/components/ui/card.tsx                         # CREATE
app/components/ui/dialog.tsx                       # CREATE
app/components/ui/dropdown-menu.tsx                 # CREATE
app/components/ui/form.tsx                         # CREATE
app/components/ui/input.tsx                        # CREATE
app/components/ui/select.tsx                       # CREATE
app/components/ui/table.tsx                        # CREATE
app/components/ui/tabs.tsx                         # CREATE
app/components/ui/progress.tsx                     # CREATE
app/components/ui/badge.tsx                        # CREATE
app/components/ui/toast.tsx                        # CREATE
app/components/ui/sheet.tsx                        # CREATE
app/components/ui/slider.tsx                       # CREATE
app/components/ui/separator.tsx                    # CREATE
app/components/ui/avatar.tsx                       # CREATE
app/components/ui/tooltip.tsx                      # CREATE
app/components/ui/command.tsx                      # CREATE

# Tests
app/__tests__/dashboard.test.tsx                   # CREATE
app/__tests__/clients.test.tsx                     # CREATE
app/__tests__/training.test.tsx                    # CREATE
app/__tests__/optimizer.test.tsx                   # CREATE
app/lib/__tests__/api.test.ts                      # CREATE
app/hooks/__tests__/use-model.test.tsx             # CREATE
```

#### Verification Criteria

- [ ] `npm run build` succeeds with zero errors
- [ ] All pages render correctly at 375px, 768px, 1024px, 1440px viewports
- [ ] Sidebar navigation works; client switcher changes context
- [ ] Dashboard loads real KPI data from API (not hardcoded)
- [ ] Client CRUD operations work end-to-end
- [ ] CSV upload validates, shows data preview, creates data source
- [ ] Model training form submits, progress bar updates, results display
- [ ] Optimizer form runs optimization, shows comparison chart
- [ ] Insights page shows AI-generated channel analysis
- [ ] Chat page streams LLM responses in real time
- [ ] Report generation produces preview; PDF download works
- [ ] Public share link renders without authentication
- [ ] All frontend tests pass

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Frontend build time exceeds 60s | Medium | Dynamic imports for heavy pages; code splitting |
| shadcn/ui components don't match design vision | Medium | Customize via CSS variables; override component styles |
| Real-time training progress is laggy | Medium | SSE or WebSocket; poll as fallback; optimistic UI |
| Mobile layout breaks on complex pages | Low | Mobile-first design; sidebar collapses to hamburger on small screens |
| State management complexity across pages | Medium | TanStack Query for server state; URL params for client context |

---

### Phase 7: Integration, Polish & Error Handling

**Duration:** 4–5 days
**Dependencies:** Phases 5, 6

#### Objectives

Wire the complete end-to-end flow from data upload through training, optimization, insights, and report generation. Add production-quality error handling, loading states, empty states, and polish.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| End-to-end flow | Upload data -> train model -> view results -> optimize -> generate report |
| Error handling | Global error boundary, API error toasts, form validation messages |
| Loading states | Skeleton screens, progress indicators, optimistic updates |
| Empty states | Meaningful empty state designs for each page |
| PDF export | Generate PDF reports with agency branding |
| Client share links | Public report view with proper token validation |
| Data quality checks | Warn on missing data, outliers, insufficient history |
| Cross-browser testing | Chrome, Firefox, Safari, Edge |
| Accessibility | WCAG 2.1 AA compliance for key flows |

#### Error Handling Strategy

```
# Backend
- Global exception handler in FastAPI
- Pydantic validation errors return 422 with field details
- Business logic errors return 400/403/404 with descriptive messages
- Unexpected errors return 500 with correlation ID (no stack trace leak)

# Frontend
- React Error Boundary at route level
- API client intercepts errors and shows toast notifications
- Form validation via zod schemas with inline error messages
- Loading skeletons for all data-dependent components
- Empty states with call-to-action for each section
```

#### Files to Create/Modify

```
# Backend
src/mmm/api/errors.py                               # MODIFY: add all error classes
src/mmm/api/main.py                                 # MODIFY: add global exception handler
src/mmm/services/report_pdf.py                      # CREATE: PDF generation service

# Frontend
app/app/error.tsx                                   # CREATE: global error boundary
app/app/loading.tsx                                 # CREATE: root loading skeleton
app/app/(dashboard)/loading.tsx                     # CREATE: dashboard loading skeleton
app/components/ui/skeleton.tsx                      # CREATE: skeleton component
app/components/ui/toast-provider.tsx                # CREATE: toast notification system
app/components/ui/empty-state.tsx                   # CREATE: reusable empty state
app/components/ui/error-boundary.tsx                # CREATE: error boundary wrapper
app/lib/error-handler.ts                            # CREATE: API error handling utilities

# PDF generation
app/app/api/reports/[id]/pdf/route.ts               # CREATE: PDF generation API route (or backend endpoint)

# Integration tests
tests/integration/test_e2e_flow.py                  # CREATE: full flow integration test
app/__tests__/e2e-flow.test.tsx                     # CREATE: critical flow smoke tests

# Accessibility
app/components/ui/visually-hidden.tsx               # CREATE: screen reader helper
app/a11y/a11y.test.tsx                              # CREATE: automated a11y checks

# Performance
app/components/ui/lazy-load.tsx                     # CREATE: intersection observer wrapper
```

#### Verification Criteria

- [ ] Full flow works: upload CSV -> train model -> view diagnostics -> run optimizer -> generate report
- [ ] Error states display correctly: failed training, invalid CSV, expired tokens
- [ ] Loading skeletons appear during data fetches (no blank screens)
- [ ] Empty states guide users to take action (no dead-end pages)
- [ ] PDF report downloads with correct content and formatting
- [ ] Share link renders public report view correctly
- [ ] Browser console shows zero errors in production build
- [ ] WCAG 2.1 AA: keyboard navigation, screen reader labels, color contrast
- [ ] Performance: dashboard loads in <2s, model results in <1s

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| PDF generation fails for complex reports | Medium | Use battle-tested library (Puppeteer/WeasyPrint); test with real data |
| Share link security (token guessing) | Low | UUID v4 tokens; rate limit shared view endpoint |
| Loading state UX feels janky | Medium | Skeleton screens that match final layout; use Suspense boundaries |
| a11y audit reveals many issues | Medium | Start with key flows; fix progressively; automated checks in CI |

---

### Phase 8: Deployment & Launch

**Duration:** 3–4 days
**Dependencies:** Phase 7

#### Objectives

Deploy the complete platform to production infrastructure, set up monitoring, and prepare for beta user onboarding.

#### Deliverables

| Deliverable | Description |
|-------------|-------------|
| Vercel deployment | Next.js frontend deployed with environment variables |
| Railway deployment | FastAPI backend deployed with Celery worker |
| Supabase production | Production database with migrations applied |
| Redis | Railway-managed Redis for Celery broker |
| Ollama | Self-hosted on a GPU-enabled server or cloud VM |
| Monitoring | Application logging, error tracking (Sentry), uptime checks |
| Beta onboarding | Landing page, sign-up flow, first-client wizard |
| Documentation | User guide, API reference, troubleshooting |

#### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                   Vercel (Next.js 15)                        │
│              https://app.mmm-platform.com                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ API calls
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       Backend                                │
│              Railway (FastAPI + Celery)                       │
│         https://api.mmm-platform.com                         │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │ FastAPI  │  │ Celery Worker │  │ Celery Beat    │        │
│  │ (API)    │  │ (training)    │  │ (scheduled)    │        │
│  └──────────┘  └──────┬───────┘  └────────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Supabase    │ │    Redis     │ │   Ollama     │
│  (Postgres   │ │  (Celery     │ │  (Qwen2.5    │
│   + Auth)    │ │   broker)    │ │   7B)        │
└──────────────┘ └──────────────┘ └──────────────┘
         │
         ▼
┌──────────────┐
│  S3 / R2     │
│  (Model      │
│   artifacts) │
└──────────────┘
```

#### Files to Create/Modify

```
# Deployment configs
vercel.json                                           # CREATE: Vercel project config
railway.json                                          # CREATE: Railway project config
railway.toml                                          # CREATE: Railway service config

# Docker (production)
Dockerfile                                            # MODIFY: multi-stage production build
docker-compose.prod.yml                               # CREATE: production compose file

# Environment
.env.production.example                               # CREATE: production env template
app/.env.production.example                           # CREATE: frontend production env

# Monitoring
src/mmm/monitoring/__init__.py                        # CREATE
src/mmm/monitoring/logging.py                         # CREATE: structured logging config
src/mmm/monitoring/metrics.py                         # CREATE: request metrics middleware

# Documentation
docs/deployment.md                                    # CREATE: deployment guide
docs/user-guide.md                                    # CREATE: end-user documentation
docs/api-reference.md                                 # CREATE: API documentation
docs/troubleshooting.md                               # CREATE: common issues and fixes

# Beta launch
app/app/(marketing)/page.tsx                          # CREATE: landing page / marketing site
app/app/(marketing)/layout.tsx                        # CREATE: marketing layout (no sidebar)
app/app/(marketing)/pricing/page.tsx                  # CREATE: pricing page

# CI/CD (update)
.github/workflows/deploy.yml                          # MODIFY: add Supabase migration step
.github/workflows/production-check.yml                # CREATE: pre-deploy validation
```

#### Verification Criteria

- [ ] `vercel deploy` succeeds; frontend loads at production URL
- [ ] Railway service starts; FastAPI responds at production URL
- [ ] Supabase migrations applied to production database
- [ ] Celery worker connects to Redis and processes training tasks
- [ ] Ollama responds to LLM requests from backend
- [ ] End-to-end flow works in production: signup -> create client -> upload CSV -> train -> optimize -> report
- [ ] Sentry captures errors in production
- [ ] Uptime monitor shows all services healthy
- [ ] Share link works for external client view
- [ ] Documentation pages are accessible and accurate
- [ ] Beta landing page renders correctly

#### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Railway cold start delay (>30s) | High | Keep-alive ping; upgrade to always-on plan ($5/mo) |
| Ollama server unreachable from Railway | High | Deploy Ollama on same network or use cloud GPU instance; fallback to OpenAI |
| Supabase free tier limits hit during beta | Medium | Monitor usage; upgrade to Pro tier early |
| Vercel edge function limits for PDF generation | Medium | Generate PDF on backend (Railway) and serve from S3/R2 |
| DNS + SSL configuration delays | Low | Use Vercel managed DNS; Railway provides SSL automatically |

---

## Critical Path

The critical path through the implementation is:

```
Phase 0 (Setup)
    └── Phase 1 (DB + Auth)                          [5 days]
            └── Phase 2 (Engine + Celery)             [5 days]
                    └── Phase 3 (Connectors)           [6 days]
                    └── Phase 4 (AI Layer)             [4 days]  (parallel with Phase 3)
                            └── Phase 5 (API Complete) [5 days]
                                    └── Phase 6 (Frontend) [10 days]
                                            └── Phase 7 (Integration) [5 days]
                                                    └── Phase 8 (Deploy) [4 days]
```

**Critical path duration:** 2 + 5 + 5 + 6 + 5 + 10 + 5 + 4 = **42 days minimum**

The bottleneck is Phase 6 (frontend) at 10 days and Phase 3 (connectors) at 6 days.

---

## Parallelization Opportunities

| Parallel Track A | Parallel Track B | When |
|-----------------|-----------------|------|
| Phase 3: Data Connectors (backend) | Phase 4: AI Insights (backend) | After Phase 2 completes; both consume engine output but are independent |
| Phase 5: Backend API (routes) | Phase 6: Frontend (pages 1-3) | After Phase 1; frontend can use mocked API while API is built |
| Phase 6: Frontend (remaining pages) | Phase 7: Integration (early items) | After core pages are done; start error handling on completed pages |
| Phase 8: Deployment configs | Phase 7: Polish | Deployment infra can be set up while polish work continues |

**With 2 parallel engineers:**

```
Engineer A: P0(2d) -> P1(5d) -> P2(5d) -> P3(6d) -> P5(5d) -> P6-pages(7d) -> P7(5d) -> P8(4d)
Engineer B: P0(2d) -> P1(5d) -> P2(5d) -> P4(4d) -> P5(5d) -> P6-pages(7d) -> P7(5d) -> P8(4d)
                                                                         ^
                                                                         └── Merge: P6(10d total)
```

**Parallel estimate:** ~28 days with 2 engineers.

---

## Quality Gates

### Per-Phase Quality Gates

Each phase must pass these gates before proceeding:

| Gate | Criteria | Enforcement |
|------|----------|-------------|
| **Lint** | `ruff check src/` passes with 0 warnings; `eslint app/` passes | Pre-commit hook + CI |
| **Type check** | `mypy src/ --strict` passes (Python); `tsc --noEmit` passes (TypeScript) | CI |
| **Tests** | All existing tests pass; new code has tests | CI |
| **Coverage** | Overall: >=80%; new code: >=90% | CI with `pytest-cov` / Jest coverage |
| **Build** | `pip install -e ".[dev,api]"` succeeds; `npm run build` succeeds | CI |
| **No secrets** | No hardcoded API keys, passwords, tokens | Pre-commit hook + manual review |

### Phase Completion Criteria

| Phase | Must Pass Before Proceeding |
|-------|---------------------------|
| Phase 0 | CI runs green on both Python and TypeScript |
| Phase 1 | Auth flow works end-to-end; RLS prevents cross-org access |
| Phase 2 | Model trains in background; artifact is saved; diagnostics are computed |
| Phase 3 | CSV upload works; at least one API connector (Meta) is functional |
| Phase 4 | LLM returns validated insights; template fallback works |
| Phase 5 | All API endpoints documented in OpenAPI; auth enforced on all routes |
| Phase 6 | All pages render; data flows from API to UI; no console errors |
| Phase 7 | Full flow works end-to-end; no critical bugs; a11y baseline met |
| Phase 8 | Production deployment is live; monitoring is active; beta sign-ups work |

### Code Review Requirements

- Every phase-internal change: self-review against checklist
- Cross-phase changes: peer review (or agent code review via `code-reviewer`)
- Security-sensitive code (auth, credentials, RLS): mandatory `security-reviewer` agent
- Frontend components: visual review at 3 breakpoints

### Test Coverage Targets

| Component | Minimum Coverage | Target Coverage |
|-----------|-----------------|-----------------|
| `src/mmm/core/` | 85% | 95% |
| `src/mmm/connectors/` | 80% | 90% |
| `src/mmm/ai/` | 80% | 90% |
| `src/mmm/api/` | 80% | 85% |
| `app/lib/` + `app/hooks/` | 75% | 85% |
| `app/components/` | 70% | 80% |
| **Overall** | **80%** | **85%** |

---

## Dependency Summary

| Phase | Depends On | Blocks |
|-------|-----------|--------|
| Phase 0 | None | All |
| Phase 1 | Phase 0 | Phases 2, 3, 4, 5, 6 |
| Phase 2 | Phase 1 | Phases 3, 4, 5 |
| Phase 3 | Phases 1, 2 | Phase 5, 6, 7 |
| Phase 4 | Phases 1, 2 | Phases 5, 6, 7 |
| Phase 5 | Phases 1–4 | Phases 6, 7 |
| Phase 6 | Phases 1, 5 | Phases 7, 8 |
| Phase 7 | Phases 5, 6 | Phase 8 |
| Phase 8 | Phase 7 | None (launch) |

---

## Risk Register (Top 10)

| # | Risk | Phase | Likelihood | Impact | Mitigation |
|---|------|-------|-----------|--------|------------|
| 1 | PyMC-Marketing training exceeds time targets on CPU | 2 | Medium | High | Preprocessing aggregation; channel count limits; GPU option |
| 2 | Platform API reliability (OAuth expiry, rate limits) | 3 | High | Medium | Exponential backoff; manual CSV fallback; health dashboard |
| 3 | LLM insight quality with Ollama | 4 | High | High | Pydantic validation; template fallback; temperature tuning |
| 4 | Frontend complexity leads to slow development | 6 | High | Medium | Component-first approach; shadcn/ui; mock data early |
| 5 | Low agency adoption at beta | 8 | Medium | High | Design partner feedback loop; free trial; clear value prop |
| 6 | Cross-org data leakage via RLS bug | 1 | Low | Critical | RLS integration tests; security review; audit queries |
| 7 | Ollama deployment reliability in production | 8 | Medium | High | Fallback to OpenAI; health checks; alerting |
| 8 | Scope creep from beta user requests | 7-8 | High | Medium | Strict V1 scope; documented V2 backlog |
| 9 | Supabase vendor lock-in | 1 | Low | Medium | Standard PostgreSQL; documented RLS; migration tooling |
| 10 | Celery task failures leave orphan jobs | 2 | Medium | Medium | Task retry + status rollback; heartbeat monitoring |

---

## Appendix: File Count Estimate

| Category | Estimated Files | New | Modified |
|----------|----------------|-----|----------|
| Backend Python (`src/mmm/`) | ~45 | ~30 | ~15 |
| Frontend (`app/`) | ~80 | ~70 | ~10 |
| Tests | ~30 | ~25 | ~5 |
| Config / CI / Docker | ~15 | ~12 | ~3 |
| Docs | ~10 | ~8 | ~2 |
| Supabase migrations | ~12 | ~12 | 0 |
| **Total** | **~192** | **~157** | **~35** |

---

*End of Implementation Plan.*
