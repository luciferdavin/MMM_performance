# MMM Platform — Backend Schema Document

| | |
|---|---|
| **Document** | 05-backend-schema.md |
| **Version** | 1.0 |
| **Date** | 2026-08-01 |
| **Author** | Senior Backend Engineer (PostgreSQL + Supabase) |
| **Canonical source** | `docs/_spec.md`, `docs/02-trd.md` |
| **Code alignment** | `src/mmm/models/schemas.py` (Pydantic v2 models) |
| **Audience** | Backend engineers, AI coding agents, DB reviewers |

This document defines every database table, column, constraint, index, enum, RLS policy, and migration SQL for the MMM Platform. It is the single source of truth for the PostgreSQL schema hosted on Supabase. Where this document and scaffolded code diverge, this document wins.

---

## 1. Entity-Relationship Diagram

```
┌──────────────────┐
│   organizations   │
│   (tenants)       │
│──────────────────│
│ PK id             │
│    name           │
│    slug (UNIQUE)  │
│    plan_tier      │
│    created_at     │
│    settings       │
└───────┬──────────┘
        │
        ├──────────────────────────────────────────────────────────────┐
        │                                                              │
        ▼                                                              ▼
┌──────────────────┐                                          ┌─────────────────┐
│    memberships    │                                          │  usage_records   │
│──────────────────│                                          │─────────────────│
│ PK id             │                                          │ PK id            │
│ FK organization_id│                                          │ FK organization_id│
│ FK user_id ─────────►┌──────────────────┐                    │    record_type   │
│    role           │   │      users       │                    │    amount        │
│    created_at     │   │──────────────────│                    │    unit          │
└──────────────────┘   │ PK id (= auth)  │                    │    meta          │
                        │    email         │                    │    created_at    │
                        │    full_name     │                    └─────────────────┘
                        │    avatar_url    │
                        │    created_at    │                    ┌─────────────────┐
                        │    last_login_at │                    │tenant_llm_settings│
                        └──────────────────┘                    │─────────────────│
                                                                │ PK id            │
        ┌────────────────────────────────────────────────┐     │ FK organization_id│
        │                                                │     │    provider       │
        ▼                                                │     │    model          │
┌──────────────────┐                                     │     │    base_url       │
│     clients       │                                    │     │    api_key_enc    │
│──────────────────│                                    │     │    temperature    │
│ PK id             │                                    │     │    max_tokens     │
│ FK organization_id│                                    │     │    created_at     │
│    name           │                                    │     │    updated_at     │
│    slug           │                                    │     └─────────────────┘
│    industry       │                                    │
│    timezone       │                                    │
│    currency       │                                    │
│    target_column  │                                    │
│    control_columns│                                    │
│    created_at     │                                    │
│    archived       │                                    │
└───────┬──────────┘                                    │
        │                                               │
        ├───────────────────────────────────────────────┤
        │                                               │
        ├───────────┬───────────────┬───────────────────┤
        │           │               │                   │
        ▼           ▼               ▼                   ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ data_sources │ │  model_jobs  │ │  reports      │ │ (insights*)  │
│──────────────│ │──────────────│ │──────────────│ │──────────────│
│ PK id        │ │ PK id        │ │ PK id        │ │ PK id        │
│ FK client_id │ │ FK client_id │ │ FK client_id │ │FK model_job_id│
│ FK org_id    │ │ FK org_id    │ │ FK org_id    │ │ FK org_id    │
│ connector_type│ │    config    │ │ FK model_job │ │ FK client_id │
│    name      │ │    status    │ │    title     │ │    type      │
│    config    │ │    result_   │ │    content   │ │    title     │
│    credentials│ │     summary  │ │    pdf_key   │ │    body      │
│    _encrypted│ │    diagnostics│ │   share_token│ │  confidence  │
│    sync_sched│ │    artifact_ │ │    status    │ │   metrics    │
│    last_sync │ │     key      │ │   created_at │ │   source     │
│    enabled   │ │    metrics   │ │   updated_at │ │  created_at  │
│    created_at│ │    error     │ └──────────────┘ └──────────────┘
└──────────────┘ │    queued_at │
                 │    started_at│        ┌──────────────────┐
                 │    finished_at│       │ budget_optimizations│
                 │    created_by│        │──────────────────│
                 │    created_at│       │ PK id             │
                 └──────┬───────┘       │ FK model_job_id   │
                        │               │ FK org_id         │
                        ▼               │ FK client_id      │
                 ┌──────────────┐       │    constraints    │
                 │channel_results│       │    allocations    │
                 │──────────────│       │    expected_rev   │
                 │ PK id        │       │    created_at     │
                 │ FK model_job │       └──────────────────┘
                 │ FK org_id    │
                 │ FK client_id │
                 │    channel   │
                 │    contribution│
                 │    share     │
                 │    roas      │
                 │    spend     │
                 │    created_at│
                 └──────────────┘
```

**Legend:**
- `PK` = Primary Key
- `FK` = Foreign Key
- `*` = The `insights` table is defined in the TRD (§4.2) and included here for completeness; the spec's required tables focus on `reports` as the client-facing output entity. Both exist.
- Arrows show foreign key direction (child points to parent).

---

## 2. Enum Types

All enums are created as PostgreSQL `CREATE TYPE` before any table definitions.

| Enum Name | Values | Used By |
|-----------|--------|---------|
| `plan_tier` | `'starter'`, `'pro'`, `'enterprise'` | `organizations.plan_tier` |
| `membership_role` | `'agency_owner'`, `'analyst'`, `'viewer'` | `memberships.role` |
| `connector_type` | `'csv'`, `'meta_ads'`, `'google_ads'`, `'ga4'`, `'tiktok'`, `'shopify'`, `'linkedin'`, `'snap'`, `'pinterest'` | `data_sources.connector_type` |
| `job_status` | `'queued'`, `'running'`, `'succeeded'`, `'failed'`, `'canceled'` | `model_jobs.status` |
| `insight_source` | `'llm'`, `'template'` | `insights.source` |
| `report_status` | `'generating'`, `'ready'`, `'failed'` | `reports.status` |
| `usage_record_type` | `'compute_seconds'`, `'storage_mb'`, `'api_calls'`, `'llm_tokens'`, `'model_train'`, `'sync_run'` | `usage_records.record_type` |
| `llm_provider` | `'ollama'`, `'openai'`, `'anthropic'` | `tenant_llm_settings.provider` |

---

## 3. Table Definitions

### 3.1 `organizations`

The top-level tenant. Every agency is an organization. All other entities are scoped to an org.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `name` | `text` | NOT NULL | — | Display name (e.g., "Acme Agency") |
| `slug` | `text` | NOT NULL | — | URL-safe unique identifier |
| `plan_tier` | `plan_tier` | NOT NULL | `'starter'` | Subscription tier |
| `settings` | `jsonb` | NOT NULL | `'{}'::jsonb` | Org-level config (branding, defaults) |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK organizations_pkey` ON (`id`)
- `UQ_organizations_slug` UNIQUE ON (`slug`)

**Indexes:**
- `idx_organizations_slug` B-tree ON (`slug`) — lookup by slug for URL routing

**Triggers:**
- `set_updated_at` fires `BEFORE UPDATE` to set `updated_at = now()`

---

### 3.2 `users`

Mirrors Supabase Auth users. The `id` column equals `auth.users.id`. This table stores profile data that Supabase Auth does not expose conveniently.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | — | PK, = `auth.users.id` |
| `email` | `text` | NOT NULL | — | Login email |
| `full_name` | `text` | NULL | — | Display name |
| `avatar_url` | `text` | NULL | — | Profile image |
| `created_at` | `timestamptz` | NOT NULL | `now()` | When user signed up |
| `last_login_at` | `timestamptz` | NULL | — | Last sign-in timestamp |

**Constraints:**
- `PK users_pkey` ON (`id`)
- `UQ_users_email` UNIQUE ON (`email`)

**Indexes:**
- `idx_users_email` B-tree ON (`email`) — login lookup

**Foreign Keys:**
- `id` references `auth.users(id)` ON DELETE CASCADE

**RLS:** Users can only see their own row (`WHERE id = auth.uid()`).

---

### 3.3 `memberships`

Maps users to organizations with a role. A user may belong to multiple orgs (e.g., freelancer across agencies).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `user_id` | `uuid` | NOT NULL | — | FK → `users.id` |
| `role` | `membership_role` | NOT NULL | `'analyst'` | Agency role |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK memberships_pkey` ON (`id`)
- `UQ_memberships_org_user` UNIQUE ON (`organization_id`, `user_id`) — one role per org per user

**Indexes:**
- `idx_memberships_org` B-tree ON (`organization_id`) — "all members of org X"
- `idx_memberships_user` B-tree ON (`user_id`) — "all orgs for user X"

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `user_id` → `users(id)` ON DELETE CASCADE

**RLS:** See Section 4.

---

### 3.4 `clients`

A client brand managed by an agency. Core entity for data isolation — most downstream tables reference both `organization_id` and `client_id`.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `name` | `text` | NOT NULL | — | Client display name |
| `slug` | `text` | NOT NULL | — | URL-safe identifier within org |
| `industry` | `text` | NULL | — | e.g., "DTC ecommerce", "SaaS" |
| `timezone` | `text` | NOT NULL | `'America/New_York'` | Client's timezone for date bucketing |
| `currency` | `text` | NOT NULL | `'USD'` | ISO 4217 currency code |
| `target_column` | `text` | NOT NULL | `'revenue'` | Dependent variable for MMM |
| `control_columns` | `jsonb` | NOT NULL | `'[]'::jsonb` | Array of control column names |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | |
| `archived` | `boolean` | NOT NULL | `false` | Soft-delete flag |

**Constraints:**
- `PK clients_pkey` ON (`id`)
- `UQ_clients_org_slug` UNIQUE ON (`organization_id`, `slug`) — slug unique within org
- `CHK_clients_target_column` CHECK (`target_column IN ('revenue', 'conversions', 'clicks')`)

**Indexes:**
- `idx_clients_org` B-tree ON (`organization_id`) — "all clients in org X"
- `idx_clients_org_active` B-tree ON (`organization_id`) WHERE `archived = false` — filtered dashboard query

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE

---

### 3.5 `data_sources`

Connector configurations per client. Stores encrypted credentials for each platform integration.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` (denormalized for RLS) |
| `client_id` | `uuid` | NOT NULL | — | FK → `clients.id` |
| `connector_type` | `connector_type` | NOT NULL | — | Platform enum |
| `name` | `text` | NOT NULL | — | User-friendly label (e.g., "Main Meta Account") |
| `config` | `jsonb` | NOT NULL | `'{}'::jsonb` | Non-secret connector settings (account IDs, property IDs) |
| `credentials_encrypted` | `text` | NULL | — | AES-256-GCM encrypted JSON blob (tokens, secrets) |
| `sync_schedule` | `text` | NOT NULL | `'weekly'` | Cron-like: `'daily'`, `'weekly'`, `'monthly'`, or null for manual only |
| `last_sync_at` | `timestamptz` | NULL | — | Timestamp of most recent successful sync |
| `sync_status` | `text` | NOT NULL | `'idle'` | `'idle'` / `'syncing'` / `'error'` |
| `last_error` | `text` | NULL | — | Error message from most recent failed sync |
| `enabled` | `boolean` | NOT NULL | `true` | Active/inactive toggle |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK data_sources_pkey` ON (`id`)
- `UQ_data_sources_client_type_name` UNIQUE ON (`client_id`, `connector_type`, `name`) — no duplicate connector names per type per client

**Indexes:**
- `idx_data_sources_client` B-tree ON (`client_id`) — "all connectors for client X"
- `idx_data_sources_org` B-tree ON (`organization_id`) — RLS helper
- `idx_data_sources_sync_schedule` B-tree ON (`sync_schedule`) WHERE `enabled = true` — cron scheduler query

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `client_id` → `clients(id)` ON DELETE CASCADE

---

### 3.6 `model_jobs`

One row per training run. This is the central entity for model lifecycle: config, status, diagnostics, artifact location, and timing.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `client_id` | `uuid` | NOT NULL | — | FK → `clients.id` |
| `name` | `text` | NOT NULL | `'default'` | User-facing job name (e.g., "Q3 weekly model") |
| `config` | `jsonb` | NOT NULL | — | Serialized `ModelConfig` (see §6 for mapping) |
| `status` | `job_status` | NOT NULL | `'queued'` | Lifecycle state |
| `diagnostics` | `jsonb` | NULL | — | Serialized `ModelDiagnostics` (rhat, r2, mape, warnings) |
| `result_summary` | `jsonb` | NULL | — | High-level: channels, total revenue, fit duration |
| `metrics` | `jsonb` | NOT NULL | `'{}'::jsonb` | Training metadata: duration_sec, data_points, channel_count, etc. |
| `artifact_key` | `text` | NULL | — | S3/R2 path to model artifacts (`{org}/{client}/{job}/`) |
| `error` | `text` | NULL | — | Error message on failure |
| `forecast_days` | `integer` | NOT NULL | `90` | Forecast horizon from config |
| `queued_at` | `timestamptz` | NOT NULL | `now()` | |
| `started_at` | `timestamptz` | NULL | — | When worker picked up the job |
| `finished_at` | `timestamptz` | NULL | — | When job reached terminal state |
| `created_by` | `uuid` | NOT NULL | — | FK → `users.id` (who initiated the training) |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK model_jobs_pkey` ON (`id`)
- `CHK_model_jobs_timing` CHECK (`started_at IS NULL OR started_at >= queued_at`)
- `CHK_model_jobs_finished` CHECK (`finished_at IS NULL OR finished_at >= started_at`)

**Indexes:**
- `idx_model_jobs_client_created` B-tree ON (`client_id`, `created_at DESC`) — dashboard "recent runs"
- `idx_model_jobs_org_status` B-tree ON (`organization_id`, `status`) — ops/queue queries
- `idx_model_jobs_created_by` B-tree ON (`created_by`) — "my jobs" query
- `idx_model_jobs_status` B-tree ON (`status`) WHERE `status IN ('queued', 'running')` — worker polling

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `client_id` → `clients(id)` ON DELETE CASCADE
- `created_by` → `users(id)` ON DELETE RESTRICT

---

### 3.7 `channel_results`

Per-model channel attribution data. One row per channel per model job. Derived from `MMMModel.get_channel_contributions()` and stored for fast reads without reloading model artifacts.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `client_id` | `uuid` | NOT NULL | — | FK → `clients.id` |
| `model_job_id` | `uuid` | NOT NULL | — | FK → `model_jobs.id` |
| `channel` | `text` | NOT NULL | — | Channel name (e.g., "meta", "google_ads", "tv") |
| `contribution` | `double precision` | NOT NULL | — | Absolute contribution value |
| `share` | `double precision` | NOT NULL | — | Percentage of total (0.0–1.0) |
| `roas` | `double precision` | NOT NULL | — | Return on ad spend (revenue / spend) |
| `spend` | `double precision` | NOT NULL | — | Total spend for this channel in training period |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK channel_results_pkey` ON (`id`)
- `UQ_channel_results_job_channel` UNIQUE ON (`model_job_id`, `channel`) — one row per channel per job
- `CHK_channel_results_share` CHECK (`share >= 0 AND share <= 1`)

**Indexes:**
- `idx_channel_results_job` B-tree ON (`model_job_id`) — "all channels for job X"
- `idx_channel_results_client` B-tree ON (`client_id`, `created_at DESC`) — historical channel performance
- `idx_channel_results_org` B-tree ON (`organization_id`) — RLS helper

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `client_id` → `clients(id)` ON DELETE CASCADE
- `model_job_id` → `model_jobs(id)` ON DELETE CASCADE

---

### 3.8 `budget_optimizations`

Stores constraint configuration and allocation results for each optimization run. Tied to a specific model job.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `client_id` | `uuid` | NOT NULL | — | FK → `clients.id` |
| `model_job_id` | `uuid` | NOT NULL | — | FK → `model_jobs.id` |
| `constraints` | `jsonb` | NOT NULL | — | Serialized `BudgetConstraints` (total_budget, min/max %, channel_bounds, channel_floors) |
| `allocations` | `jsonb` | NOT NULL | — | Serialized `AllocationResult.allocations[]` |
| `total_budget` | `double precision` | NOT NULL | — | Total budget input |
| `expected_total_revenue` | `double precision` | NOT NULL | — | Sum of expected revenue across channels |
| `is_feasible` | `boolean` | NOT NULL | — | Whether allocation satisfies constraints |
| `created_by` | `uuid` | NOT NULL | — | FK → `users.id` |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK budget_optimizations_pkey` ON (`id`)
- `CHK_budget_optimizations_budget` CHECK (`total_budget > 0`)

**Indexes:**
- `idx_budget_optimizations_job` B-tree ON (`model_job_id`) — "all optimizations for job X"
- `idx_budget_optimizations_client` B-tree ON (`client_id`, `created_at DESC`) — history
- `idx_budget_optimizations_org` B-tree ON (`organization_id`) — RLS helper

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `client_id` → `clients(id)` ON DELETE CASCADE
- `model_job_id` → `model_jobs(id)` ON DELETE CASCADE
- `created_by` → `users(id)` ON DELETE RESTRICT

---

### 3.9 `reports`

Generated MMM reports. Stores the rendered content (Markdown/HTML), PDF artifact path, and share token for client access.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `client_id` | `uuid` | NOT NULL | — | FK → `clients.id` |
| `model_job_id` | `uuid` | NOT NULL | — | FK → `model_jobs.id` |
| `title` | `text` | NOT NULL | — | Report title (e.g., "Q3 Marketing Mix Report") |
| `content` | `text` | NULL | — | LLM-generated Markdown content |
| `status` | `report_status` | NOT NULL | `'generating'` | Report generation state |
| `pdf_key` | `text` | NULL | — | S3/R2 path to rendered PDF |
| `share_token` | `uuid` | NOT NULL | `gen_random_uuid()` | Unguessable public token for client view |
| `share_expires_at` | `timestamptz` | NULL | — | Optional expiration for share link |
| `error` | `text` | NULL | — | Error if generation failed |
| `created_by` | `uuid` | NOT NULL | — | FK → `users.id` |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK reports_pkey` ON (`id`)
- `UQ_reports_share_token` UNIQUE ON (`share_token`) — public link lookup

**Indexes:**
- `idx_reports_client_created` B-tree ON (`client_id`, `created_at DESC`) — report list per client
- `idx_reports_org` B-tree ON (`organization_id`) — RLS helper
- `idx_reports_share_token` B-tree ON (`share_token`) — public report lookup (no auth)
- `idx_reports_model_job` B-tree ON (`model_job_id`) — "reports for this model run"

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `client_id` → `clients(id)` ON DELETE CASCADE
- `model_job_id` → `model_jobs(id)` ON DELETE CASCADE
- `created_by` → `users(id)` ON DELETE RESTRICT

---

### 3.10 `usage_records`

Org-level usage metering for billing and plan enforcement. Written asynchronously by Celery workers after each billable event.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `record_type` | `usage_record_type` | NOT NULL | — | What is being measured |
| `amount` | `numeric(12,4)` | NOT NULL | — | Quantity (seconds, MB, count, tokens) |
| `unit` | `text` | NOT NULL | — | Human-readable unit (e.g., "seconds", "megabytes", "tokens") |
| `meta` | `jsonb` | NOT NULL | `'{}'::jsonb` | Context: job_id, model_name, connector, provider, etc. |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK usage_records_pkey` ON (`id`)
- `CHK_usage_records_amount` CHECK (`amount >= 0`)

**Indexes:**
- `idx_usage_records_org_created` B-tree ON (`organization_id`, `created_at DESC`) — billing rollups
- `idx_usage_records_org_type_created` B-tree ON (`organization_id`, `record_type`, `created_at DESC`) — per-type aggregation

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE

**Write pattern:** Append-only. Workers INSERT after each train, sync, insight batch, and LLM call. Aggregated monthly for plan enforcement (Starter: 3 clients / 20 trains; Pro: 15 / 100; Enterprise: unlimited).

---

### 3.11 `tenant_llm_settings`

Per-organization LLM provider configuration. Allows each agency to use their own LLM provider, model, and API key. Falls back to global `Settings` when no row exists.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `provider` | `llm_provider` | NOT NULL | `'ollama'` | LLM backend |
| `model` | `text` | NOT NULL | `'qwen2.5:7b'` | Model identifier (provider-specific) |
| `base_url` | `text` | NULL | — | Custom endpoint (e.g., tenant-hosted Ollama) |
| `api_key_encrypted` | `text` | NULL | — | AES-256-GCM encrypted API key (null for Ollama default) |
| `temperature` | `double precision` | NOT NULL | `0.7` | LLM temperature |
| `max_tokens` | `integer` | NOT NULL | `2048` | Max output tokens |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK tenant_llm_settings_pkey` ON (`id`)
- `UQ_tenant_llm_settings_org` UNIQUE ON (`organization_id`) — one LLM config per org

**Indexes:**
- `idx_tenant_llm_settings_org` B-tree ON (`organization_id`) — lookup by org

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE

---

### 3.12 `insights` (TRD-aligned)

AI-generated insights tied to a model job. Stored as individual rows per insight for granular querying and UI rendering. Aligned with the `Insight` Pydantic schema in `schemas.py`.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NOT NULL | `gen_random_uuid()` | Primary key |
| `organization_id` | `uuid` | NOT NULL | — | FK → `organizations.id` |
| `client_id` | `uuid` | NOT NULL | — | FK → `clients.id` |
| `model_job_id` | `uuid` | NOT NULL | — | FK → `model_jobs.id` |
| `type` | `text` | NOT NULL | — | One of: `channel_performance`, `budget_recommendation`, `anomaly`, `benchmark`, `summary` |
| `title` | `text` | NOT NULL | — | Short headline |
| `body` | `text` | NOT NULL | — | Full insight text |
| `confidence` | `double precision` | NOT NULL | `0.0` | 0.0–1.0 confidence score |
| `metrics` | `jsonb` | NOT NULL | `'{}'::jsonb` | Numerical context (ROAS, spend, delta) |
| `source` | `insight_source` | NOT NULL | `'llm'` | Whether generated by LLM or template fallback |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**Constraints:**
- `PK insights_pkey` ON (`id`)
- `CHK_insights_confidence` CHECK (`confidence >= 0 AND confidence <= 1`)

**Indexes:**
- `idx_insights_job` B-tree ON (`model_job_id`) — "all insights for job X"
- `idx_insights_client_type` B-tree ON (`client_id`, `type`) — filter by insight type
- `idx_insights_org` B-tree ON (`organization_id`) — RLS helper

**Foreign Keys:**
- `organization_id` → `organizations(id)` ON DELETE CASCADE
- `client_id` → `clients(id)` ON DELETE CASCADE
- `model_job_id` → `model_jobs(id)` ON DELETE CASCADE

---

## 4. Row-Level Security (RLS) Policies

RLS is defense-in-depth. The FastAPI auth dependency (`api/deps.py`) is the primary enforcement layer; RLS guarantees that a compromised or buggy query cannot cross tenant boundaries.

### 4.1 Helper Function: `is_org_member`

Every tenant-scoped RLS policy calls this function. It checks whether the current authenticated user (`auth.uid()`) has an active membership in the given organization.

```sql
-- Helper: check if current user is a member of the given org
CREATE OR REPLACE FUNCTION public.is_org_member(org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
  );
$$;

-- Helper: check if current user has at least 'analyst' role in the org
CREATE OR REPLACE FUNCTION public.is_org_analyst_or_above(org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
      AND m.role IN ('agency_owner', 'analyst')
  );
$$;

-- Helper: check if current user is org owner
CREATE OR REPLACE FUNCTION public.is_org_owner(org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
      AND m.role = 'agency_owner'
  );
$$;
```

### 4.2 Per-Table RLS Policies

#### `organizations`

```sql
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

-- Members can view their own organizations
CREATE POLICY "org_select_members"
  ON public.organizations FOR SELECT
  USING (public.is_org_member(id));

-- Only org owners can update organization settings
CREATE POLICY "org_update_owner"
  ON public.organizations FOR UPDATE
  USING (public.is_org_owner(id))
  WITH CHECK (public.is_org_owner(id));

-- Any authenticated user can create an organization (initial setup)
CREATE POLICY "org_insert_authenticated"
  ON public.organizations FOR INSERT
  WITH CHECK (auth.uid() IS NOT NULL);
```

#### `users`

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Users can only see their own profile
CREATE POLICY "user_select_self"
  ON public.users FOR SELECT
  USING (id = auth.uid());

-- Users can update their own profile
CREATE POLICY "user_update_self"
  ON public.users FOR UPDATE
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- Profile created on signup (via Supabase Auth trigger)
CREATE POLICY "user_insert_own"
  ON public.users FOR INSERT
  WITH CHECK (id = auth.uid());
```

#### `memberships`

```sql
ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;

-- Users always see their own memberships; org members see all memberships in their org
CREATE POLICY "membership_select"
  ON public.memberships FOR SELECT
  USING (
    user_id = auth.uid()
    OR public.is_org_member(organization_id)
  );

-- Only org owners can insert new memberships (invite)
CREATE POLICY "membership_insert_owner"
  ON public.memberships FOR INSERT
  WITH CHECK (public.is_org_owner(organization_id));

-- Only org owners can update membership roles
CREATE POLICY "membership_update_owner"
  ON public.memberships FOR UPDATE
  USING (public.is_org_owner(organization_id))
  WITH CHECK (public.is_org_owner(organization_id));

-- Only org owners can remove members (or users can remove themselves)
CREATE POLICY "membership_delete_owner_or_self"
  ON public.memberships FOR DELETE
  USING (
    public.is_org_owner(organization_id)
    OR user_id = auth.uid()
  );
```

#### `clients`

```sql
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;

-- Org members can view all clients in their org
CREATE POLICY "client_select_member"
  ON public.clients FOR SELECT
  USING (public.is_org_member(organization_id));

-- Analysts and owners can create clients
CREATE POLICY "client_insert_analyst"
  ON public.clients FOR INSERT
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- Analysts and owners can update clients
CREATE POLICY "client_update_analyst"
  ON public.clients FOR UPDATE
  USING (public.is_org_analyst_or_above(organization_id))
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- Only owners can delete (archive) clients
CREATE POLICY "client_delete_owner"
  ON public.clients FOR DELETE
  USING (public.is_org_owner(organization_id));
```

#### `data_sources`

```sql
ALTER TABLE public.data_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ds_select_member"
  ON public.data_sources FOR SELECT
  USING (public.is_org_member(organization_id));

CREATE POLICY "ds_insert_analyst"
  ON public.data_sources FOR INSERT
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

CREATE POLICY "ds_update_analyst"
  ON public.data_sources FOR UPDATE
  USING (public.is_org_analyst_or_above(organization_id))
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

CREATE POLICY "ds_delete_analyst"
  ON public.data_sources FOR DELETE
  USING (public.is_org_analyst_or_above(organization_id));
```

#### `model_jobs`

```sql
ALTER TABLE public.model_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "mj_select_member"
  ON public.model_jobs FOR SELECT
  USING (public.is_org_member(organization_id));

CREATE POLICY "mj_insert_analyst"
  ON public.model_jobs FOR INSERT
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

CREATE POLICY "mj_update_analyst"
  ON public.model_jobs FOR UPDATE
  USING (public.is_org_analyst_or_above(organization_id))
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- No DELETE policy: jobs are never deleted via API (soft status only)
```

#### `channel_results`

```sql
ALTER TABLE public.channel_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "cr_select_member"
  ON public.channel_results FOR SELECT
  USING (public.is_org_member(organization_id));

CREATE POLICY "cr_insert_analyst"
  ON public.channel_results FOR INSERT
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- channel_results are read-only once created; no UPDATE or DELETE policies
```

#### `budget_optimizations`

```sql
ALTER TABLE public.budget_optimizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "bo_select_member"
  ON public.budget_optimizations FOR SELECT
  USING (public.is_org_member(organization_id));

CREATE POLICY "bo_insert_analyst"
  ON public.budget_optimizations FOR INSERT
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- Budget optimization results are read-only once created
```

#### `reports`

```sql
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "report_select_member"
  ON public.reports FOR SELECT
  USING (public.is_org_member(organization_id));

CREATE POLICY "report_insert_analyst"
  ON public.reports FOR INSERT
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

CREATE POLICY "report_update_analyst"
  ON public.reports FOR UPDATE
  USING (public.is_org_analyst_or_above(organization_id))
  WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- Public share access is handled via a dedicated API endpoint that
-- bypasses RLS using the service_role key, looking up by share_token.
-- No anonymous SELECT policy is needed.
```

#### `usage_records`

```sql
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;

-- Only org owners can view usage (billing context)
CREATE POLICY "usage_select_owner"
  ON public.usage_records FOR SELECT
  USING (public.is_org_owner(organization_id));

-- Insert is done by the service_role key (workers), not user JWT.
-- No user-facing INSERT/UPDATE/DELETE policies needed.
```

#### `tenant_llm_settings`

```sql
ALTER TABLE public.tenant_llm_settings ENABLE ROW LEVEL SECURITY;

-- Org members can view LLM settings
CREATE POLICY "llm_select_member"
  ON public.tenant_llm_settings FOR SELECT
  USING (public.is_org_member(organization_id));

-- Only owners can modify LLM settings
CREATE POLICY "llm_insert_owner"
  ON public.tenant_llm_settings FOR INSERT
  WITH CHECK (public.is_org_owner(organization_id));

CREATE POLICY "llm_update_owner"
  ON public.tenant_llm_settings FOR UPDATE
  USING (public.is_org_owner(organization_id))
  WITH CHECK (public.is_org_owner(organization_id));

CREATE POLICY "llm_delete_owner"
  ON public.tenant_llm_settings FOR DELETE
  USING (public.is_org_owner(organization_id));
```

#### `insights`

```sql
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "insight_select_member"
  ON public.insights FOR SELECT
  USING (public.is_org_member(organization_id));

-- Insights are inserted by workers using service_role key
-- No user-facing INSERT/UPDATE/DELETE policies needed
```

---

## 5. Supabase Migration SQL

The following is a single, ordered migration file that can be applied via Supabase SQL Editor or Alembic. It is structured for clarity and idempotent execution.

```sql
-- =====================================================
-- MMM Platform — Initial Schema Migration
-- Version: 001
-- Date: 2026-08-01
-- =====================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- ENUM TYPES
-- =====================================================

DO $$ BEGIN
  CREATE TYPE public.plan_tier AS ENUM ('starter', 'pro', 'enterprise');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.membership_role AS ENUM ('agency_owner', 'analyst', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.connector_type AS ENUM (
    'csv', 'meta_ads', 'google_ads', 'ga4', 'tiktok', 'shopify',
    'linkedin', 'snap', 'pinterest'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.job_status AS ENUM ('queued', 'running', 'succeeded', 'failed', 'canceled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.insight_source AS ENUM ('llm', 'template');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.report_status AS ENUM ('generating', 'ready', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.usage_record_type AS ENUM (
    'compute_seconds', 'storage_mb', 'api_calls', 'llm_tokens', 'model_train', 'sync_run'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.llm_provider AS ENUM ('ollama', 'openai', 'anthropic');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- HELPER FUNCTIONS (must precede RLS policies)
-- =====================================================

CREATE OR REPLACE FUNCTION public.is_org_member(org_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.memberships m
    WHERE m.organization_id = org_id AND m.user_id = auth.uid()
  );
$$;

CREATE OR REPLACE FUNCTION public.is_org_analyst_or_above(org_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
      AND m.role IN ('agency_owner', 'analyst')
  );
$$;

CREATE OR REPLACE FUNCTION public.is_org_owner(org_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
      AND m.role = 'agency_owner'
  );
$$;

-- updated_at trigger function
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- =====================================================
-- TABLE: organizations
-- =====================================================

CREATE TABLE public.organizations (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  slug       text NOT NULL,
  plan_tier  public.plan_tier NOT NULL DEFAULT 'starter',
  settings   jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_organizations_slug ON public.organizations (slug);
CREATE TRIGGER trg_organizations_updated_at
  BEFORE UPDATE ON public.organizations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: users
-- =====================================================

CREATE TABLE public.users (
  id           uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email        text NOT NULL,
  full_name    text,
  avatar_url   text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz
);

CREATE UNIQUE INDEX idx_users_email ON public.users (email);

-- =====================================================
-- TABLE: memberships
-- =====================================================

CREATE TABLE public.memberships (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role            public.membership_role NOT NULL DEFAULT 'analyst',
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_memberships_org_user UNIQUE (organization_id, user_id)
);

CREATE INDEX idx_memberships_org ON public.memberships (organization_id);
CREATE INDEX idx_memberships_user ON public.memberships (user_id);

-- =====================================================
-- TABLE: clients
-- =====================================================

CREATE TABLE public.clients (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name            text NOT NULL,
  slug            text NOT NULL,
  industry        text,
  timezone        text NOT NULL DEFAULT 'America/New_York',
  currency        text NOT NULL DEFAULT 'USD',
  target_column   text NOT NULL DEFAULT 'revenue'
    CHECK (target_column IN ('revenue', 'conversions', 'clicks')),
  control_columns jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  archived        boolean NOT NULL DEFAULT false,
  CONSTRAINT uq_clients_org_slug UNIQUE (organization_id, slug)
);

CREATE INDEX idx_clients_org ON public.clients (organization_id);
CREATE INDEX idx_clients_org_active ON public.clients (organization_id) WHERE archived = false;
CREATE TRIGGER trg_clients_updated_at
  BEFORE UPDATE ON public.clients
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: data_sources
-- =====================================================

CREATE TABLE public.data_sources (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id      uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id            uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  connector_type       public.connector_type NOT NULL,
  name                 text NOT NULL,
  config               jsonb NOT NULL DEFAULT '{}'::jsonb,
  credentials_encrypted text,
  sync_schedule        text NOT NULL DEFAULT 'weekly',
  last_sync_at         timestamptz,
  sync_status          text NOT NULL DEFAULT 'idle',
  last_error           text,
  enabled              boolean NOT NULL DEFAULT true,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_data_sources_client_type_name UNIQUE (client_id, connector_type, name)
);

CREATE INDEX idx_data_sources_client ON public.data_sources (client_id);
CREATE INDEX idx_data_sources_org ON public.data_sources (organization_id);
CREATE INDEX idx_data_sources_sync_schedule ON public.data_sources (sync_schedule) WHERE enabled = true;
CREATE TRIGGER trg_data_sources_updated_at
  BEFORE UPDATE ON public.data_sources
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: model_jobs
-- =====================================================

CREATE TABLE public.model_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  name            text NOT NULL DEFAULT 'default',
  config          jsonb NOT NULL,
  status          public.job_status NOT NULL DEFAULT 'queued',
  diagnostics     jsonb,
  result_summary  jsonb,
  metrics         jsonb NOT NULL DEFAULT '{}'::jsonb,
  artifact_key    text,
  error           text,
  forecast_days   integer NOT NULL DEFAULT 90,
  queued_at       timestamptz NOT NULL DEFAULT now(),
  started_at      timestamptz,
  finished_at     timestamptz,
  created_by      uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (started_at IS NULL OR started_at >= queued_at),
  CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE INDEX idx_model_jobs_client_created ON public.model_jobs (client_id, created_at DESC);
CREATE INDEX idx_model_jobs_org_status ON public.model_jobs (organization_id, status);
CREATE INDEX idx_model_jobs_created_by ON public.model_jobs (created_by);
CREATE INDEX idx_model_jobs_active ON public.model_jobs (status) WHERE status IN ('queued', 'running');

-- =====================================================
-- TABLE: channel_results
-- =====================================================

CREATE TABLE public.channel_results (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id    uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  channel         text NOT NULL,
  contribution    double precision NOT NULL,
  share           double precision NOT NULL CHECK (share >= 0 AND share <= 1),
  roas            double precision NOT NULL,
  spend           double precision NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_channel_results_job_channel UNIQUE (model_job_id, channel)
);

CREATE INDEX idx_channel_results_job ON public.channel_results (model_job_id);
CREATE INDEX idx_channel_results_client ON public.channel_results (client_id, created_at DESC);
CREATE INDEX idx_channel_results_org ON public.channel_results (organization_id);

-- =====================================================
-- TABLE: budget_optimizations
-- =====================================================

CREATE TABLE public.budget_optimizations (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id          uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id                uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id             uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  constraints              jsonb NOT NULL,
  allocations              jsonb NOT NULL,
  total_budget             double precision NOT NULL CHECK (total_budget > 0),
  expected_total_revenue   double precision NOT NULL,
  is_feasible              boolean NOT NULL,
  created_by               uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  created_at               timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_budget_optimizations_job ON public.budget_optimizations (model_job_id);
CREATE INDEX idx_budget_optimizations_client ON public.budget_optimizations (client_id, created_at DESC);
CREATE INDEX idx_budget_optimizations_org ON public.budget_optimizations (organization_id);

-- =====================================================
-- TABLE: reports
-- =====================================================

CREATE TABLE public.reports (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id    uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  title           text NOT NULL,
  content         text,
  status          public.report_status NOT NULL DEFAULT 'generating',
  pdf_key         text,
  share_token     uuid NOT NULL DEFAULT gen_random_uuid(),
  share_expires_at timestamptz,
  error           text,
  created_by      uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_reports_share_token ON public.reports (share_token);
CREATE INDEX idx_reports_client_created ON public.reports (client_id, created_at DESC);
CREATE INDEX idx_reports_org ON public.reports (organization_id);
CREATE INDEX idx_reports_model_job ON public.reports (model_job_id);
CREATE TRIGGER trg_reports_updated_at
  BEFORE UPDATE ON public.reports
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: usage_records
-- =====================================================

CREATE TABLE public.usage_records (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  record_type     public.usage_record_type NOT NULL,
  amount          numeric(12,4) NOT NULL CHECK (amount >= 0),
  unit            text NOT NULL,
  meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_usage_records_org_created ON public.usage_records (organization_id, created_at DESC);
CREATE INDEX idx_usage_records_org_type_created ON public.usage_records (organization_id, record_type, created_at DESC);

-- =====================================================
-- TABLE: tenant_llm_settings
-- =====================================================

CREATE TABLE public.tenant_llm_settings (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  provider         public.llm_provider NOT NULL DEFAULT 'ollama',
  model            text NOT NULL DEFAULT 'qwen2.5:7b',
  base_url         text,
  api_key_encrypted text,
  temperature      double precision NOT NULL DEFAULT 0.7,
  max_tokens       integer NOT NULL DEFAULT 2048,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_tenant_llm_settings_org UNIQUE (organization_id)
);

CREATE INDEX idx_tenant_llm_settings_org ON public.tenant_llm_settings (organization_id);
CREATE TRIGGER trg_tenant_llm_settings_updated_at
  BEFORE UPDATE ON public.tenant_llm_settings
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: insights
-- =====================================================

CREATE TABLE public.insights (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id    uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  type            text NOT NULL CHECK (type IN (
    'channel_performance', 'budget_recommendation', 'anomaly', 'benchmark', 'summary'
  )),
  title           text NOT NULL,
  body            text NOT NULL,
  confidence      double precision NOT NULL DEFAULT 0.0
    CHECK (confidence >= 0 AND confidence <= 1),
  metrics         jsonb NOT NULL DEFAULT '{}'::jsonb,
  source          public.insight_source NOT NULL DEFAULT 'llm',
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_insights_job ON public.insights (model_job_id);
CREATE INDEX idx_insights_client_type ON public.insights (client_id, type);
CREATE INDEX idx_insights_org ON public.insights (organization_id);

-- =====================================================
-- ENABLE ROW-LEVEL SECURITY
-- =====================================================

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.budget_optimizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_llm_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS POLICIES (see Section 4 for full definitions)
-- =====================================================

-- organizations
CREATE POLICY "org_select_members" ON public.organizations FOR SELECT USING (public.is_org_member(id));
CREATE POLICY "org_update_owner" ON public.organizations FOR UPDATE USING (public.is_org_owner(id)) WITH CHECK (public.is_org_owner(id));
CREATE POLICY "org_insert_authenticated" ON public.organizations FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- users
CREATE POLICY "user_select_self" ON public.users FOR SELECT USING (id = auth.uid());
CREATE POLICY "user_update_self" ON public.users FOR UPDATE USING (id = auth.uid()) WITH CHECK (id = auth.uid());
CREATE POLICY "user_insert_own" ON public.users FOR INSERT WITH CHECK (id = auth.uid());

-- memberships
CREATE POLICY "membership_select" ON public.memberships FOR SELECT USING (user_id = auth.uid() OR public.is_org_member(organization_id));
CREATE POLICY "membership_insert_owner" ON public.memberships FOR INSERT WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "membership_update_owner" ON public.memberships FOR UPDATE USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "membership_delete_owner_or_self" ON public.memberships FOR DELETE USING (public.is_org_owner(organization_id) OR user_id = auth.uid());

-- clients
CREATE POLICY "client_select_member" ON public.clients FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "client_insert_analyst" ON public.clients FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "client_update_analyst" ON public.clients FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "client_delete_owner" ON public.clients FOR DELETE USING (public.is_org_owner(organization_id));

-- data_sources
CREATE POLICY "ds_select_member" ON public.data_sources FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "ds_insert_analyst" ON public.data_sources FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "ds_update_analyst" ON public.data_sources FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "ds_delete_analyst" ON public.data_sources FOR DELETE USING (public.is_org_analyst_or_above(organization_id));

-- model_jobs
CREATE POLICY "mj_select_member" ON public.model_jobs FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "mj_insert_analyst" ON public.model_jobs FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "mj_update_analyst" ON public.model_jobs FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- channel_results
CREATE POLICY "cr_select_member" ON public.channel_results FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "cr_insert_analyst" ON public.channel_results FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- budget_optimizations
CREATE POLICY "bo_select_member" ON public.budget_optimizations FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "bo_insert_analyst" ON public.budget_optimizations FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- reports
CREATE POLICY "report_select_member" ON public.reports FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "report_insert_analyst" ON public.reports FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "report_update_analyst" ON public.reports FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- usage_records
CREATE POLICY "usage_select_owner" ON public.usage_records FOR SELECT USING (public.is_org_owner(organization_id));

-- tenant_llm_settings
CREATE POLICY "llm_select_member" ON public.tenant_llm_settings FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "llm_insert_owner" ON public.tenant_llm_settings FOR INSERT WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "llm_update_owner" ON public.tenant_llm_settings FOR UPDATE USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "llm_delete_owner" ON public.tenant_llm_settings FOR DELETE USING (public.is_org_owner(organization_id));

-- insights
CREATE POLICY "insight_select_member" ON public.insights FOR SELECT USING (public.is_org_member(organization_id));

-- =====================================================
-- SUPABASE AUTH TRIGGER: auto-create user profile
-- =====================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name'),
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

---

## 6. Pydantic to Database Type Mapping

The following table maps every Pydantic model in `src/mmm/models/schemas.py` to the corresponding database column(s) and storage format.

| Pydantic Model | DB Table(s) | Column(s) | Storage Format |
|---|---|---|---|
| `ModelConfig` | `model_jobs` | `config` | `jsonb` — serialized via `model_dump()` |
| `ModelDiagnostics` | `model_jobs` | `diagnostics` | `jsonb` — serialized via `model_dump()` |
| `FitResult` | `model_jobs` | `status`, `error`, `result_summary`, `metrics` | Decomposed: `status` maps to `job_status` enum, `error` → `text`, diagnostics/error from `FitResult.diagnostics`/`FitResult.error` → `jsonb` columns |
| `ChannelContribution` | `channel_results` | `channel`, `contribution`, `share`, `roas`, `spend` | Direct column mapping (one row per channel per job) |
| `BudgetConstraints` | `budget_optimizations` | `constraints` | `jsonb` — serialized via `model_dump()` |
| `AllocationResult` | `budget_optimizations` | `allocations`, `total_budget`, `expected_total_revenue`, `is_feasible` | Decomposed: `allocations` → `jsonb` (serialized list), scalar fields → `double precision` / `boolean` |
| `Allocation` | `budget_optimizations` | (nested in `allocations` jsonb) | Array element inside `jsonb` |
| `Insight` | `insights` | `type`, `title`, `body`, `confidence`, `metrics` | Direct column mapping (one row per insight) |
| `MMMDataset` | (transient, not stored) | — | Built in-memory from `data_sources` sync; stored as Parquet/pickle in S3 under `artifact_key` |
| `MediaRecord` | (transient, not stored) | — | Parsed from CSV/API into DataFrame; validated before ingestion into `MMMDataset` |
| `Granularity` | `model_jobs` | `config.granularity` (nested) | `jsonb` — string value (`'day'`, `'week'`, `'month'`) inside the `config` blob |
| `ForecastPoint` | `model_jobs` | `result_summary.forecast` (nested) | `jsonb` — array of forecast points inside `result_summary` |
| `ConnectorConfig` | `data_sources` | `name`, `config`, `credentials_encrypted` | `name` → `text`, `config` → `jsonb`, `credentials` → `text` (AES-256-GCM encrypted JSON) |

### 6.1 Serialization Conventions

- All Pydantic models serialize to JSONB via `model.model_dump(mode="json")`.
- `datetime` fields are stored as `timestamptz` in PostgreSQL and serialized as ISO-8601 strings in JSONB.
- `Enum` fields (e.g., `Granularity`) are serialized as their string value in JSONB, not as integers.
- Encrypted fields (`credentials_encrypted`, `api_key_encrypted`) store AES-256-GCM ciphertext as a base64 string with a key-id prefix: `v1:<key_id>:<base64_ciphertext>`.

---

## 7. Data Ownership Rules

### 7.1 Ownership Hierarchy

```
Organization (tenant)
  └── Memberships (users with roles)
  └── Clients
       ├── DataSources (encrypted credentials)
       ├── ModelJobs
       │    ├── ChannelResults (per-channel attribution)
       │    ├── BudgetOptimizations (constraint + allocation)
       │    ├── Insights (LLM/template generated)
       │    └── Reports (PDF, share token)
       └── (all scoped by organization_id for RLS)
  └── UsageRecords (org-level metering)
  └── TenantLLMSettings (org-level LLM config)
```

### 7.2 Who Owns What

| Entity | Owner | Can Read | Can Write | Can Delete |
|--------|-------|----------|-----------|------------|
| `organizations` | `agency_owner` | Org members | Owner only | Owner only (hard delete) |
| `users` | Self | Self only | Self only (profile fields) | Via Supabase Auth |
| `memberships` | Org | Org members | Owner only | Owner or self (leave org) |
| `clients` | Org | Org members | Analyst + Owner | Owner only |
| `data_sources` | Org / Client | Org members | Analyst + Owner | Analyst + Owner |
| `model_jobs` | Org / Client | Org members | Analyst + Owner | Never deleted (status=canceled) |
| `channel_results` | Org / Client / Job | Org members | Worker (service role) | Cascade from job |
| `budget_optimizations` | Org / Client / Job | Org members | Analyst + Owner | Cascade from job |
| `reports` | Org / Client / Job | Org members + public (share_token) | Analyst + Owner | Cascade from job |
| `insights` | Org / Client / Job | Org members | Worker (service role) | Cascade from job |
| `usage_records` | Org | Owner only | Worker (service role) | Cascade from org |
| `tenant_llm_settings` | Org | Org members | Owner only | Owner only |

### 7.3 Cascade Delete Rules

| Parent | Child | Behavior | Rationale |
|--------|-------|----------|-----------|
| `organizations` | `memberships` | CASCADE | Dissolving an org removes all memberships |
| `organizations` | `clients` | CASCADE | Dissolving an org removes all clients |
| `organizations` | `data_sources` | CASCADE | Dissolving an org removes all connector configs |
| `organizations` | `model_jobs` | CASCADE | Dissolving an org removes all training history |
| `organizations` | `usage_records` | CASCADE | Dissolving an org removes billing history |
| `organizations` | `tenant_llm_settings` | CASCADE | Dissolving an org removes LLM config |
| `organizations` | `reports` | CASCADE | Dissolving an org removes all reports |
| `organizations` | `channel_results` | CASCADE | Dissolving an org removes attribution data |
| `organizations` | `budget_optimizations` | CASCADE | Dissolving an org removes optimization history |
| `organizations` | `insights` | CASCADE | Dissolving an org removes all insights |
| `clients` | `data_sources` | CASCADE | Deleting a client removes its connectors |
| `clients` | `model_jobs` | CASCADE | Deleting a client removes its model history |
| `clients` | `channel_results` | CASCADE | Deleting a client removes its attribution data |
| `clients` | `budget_optimizations` | CASCADE | Deleting a client removes its optimization history |
| `clients` | `reports` | CASCADE | Deleting a client removes its reports |
| `clients` | `insights` | CASCADE | Deleting a client removes its insights |
| `model_jobs` | `channel_results` | CASCADE | Deleting a job removes its channel results |
| `model_jobs` | `budget_optimizations` | CASCADE | Deleting a job removes its optimizations |
| `model_jobs` | `reports` | CASCADE | Deleting a job removes its reports |
| `model_jobs` | `insights` | CASCADE | Deleting a job removes its insights |
| `users` | `memberships` | CASCADE | Deleting a user removes their memberships |
| `users` | `model_jobs` | RESTRICT | Cannot delete a user who created model jobs (preserves audit trail) |
| `users` | `reports` | RESTRICT | Cannot delete a user who created reports |
| `users` | `budget_optimizations` | RESTRICT | Cannot delete a user who created optimizations |
| `auth.users` | `users` (profile) | CASCADE | Supabase auth deletion cascades to profile |

### 7.4 S3/R2 Artifact Lifecycle

Model artifacts in S3/R2 follow the same ownership rules but are not managed by PostgreSQL CASCADE:

| Artifact | Trigger for Deletion | Mechanism |
|----------|---------------------|-----------|
| `{org}/{client}/{job}/` prefix | Job deleted from DB | Celery task `cleanup_artifacts(job_id)` called on delete; S3 `delete_objects` for the prefix |
| Partial artifacts from failed jobs | 30 days after `finished_at` | S3 lifecycle rule: tag-based expiration on `status=failed` prefix |
| Org-level artifact root | Org deleted | Celery task `cleanup_org_artifacts(org_id)` called before org deletion; bulk delete |
| PDF reports (`reports.pdf_key`) | Report deleted | Cascade from `model_jobs` → `reports` → S3 delete |

### 7.5 Soft Delete vs Hard Delete

| Entity | Strategy | Notes |
|--------|----------|-------|
| `organizations` | Hard delete | Full cascade; no recovery |
| `clients` | Soft delete (`archived=true`) | Preserves model history and reports for audit |
| `model_jobs` | Status set to `canceled` | Never row-deleted; artifact cleanup after 30 days |
| `data_sources` | Hard delete (cascade from client) | Credentials wiped |
| `reports` | Hard delete (cascade from job) | PDF artifacts cleaned up |
| `users` | Profile row deleted via CASCADE | Supabase auth record managed by admin API |

---

## 8. Index Strategy Summary

### 8.1 B-Tree Indexes (Primary Access Patterns)

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| `organizations` | `idx_organizations_slug` | `slug` | URL routing |
| `users` | `idx_users_email` | `email` | Login lookup |
| `memberships` | `idx_memberships_org` | `organization_id` | Org member listing |
| `memberships` | `idx_memberships_user` | `user_id` | User's org listing |
| `clients` | `idx_clients_org` | `organization_id` | Org client listing |
| `clients` | `idx_clients_org_active` | `organization_id` WHERE `archived=false` | Dashboard filtered query |
| `data_sources` | `idx_data_sources_client` | `client_id` | Client connector listing |
| `data_sources` | `idx_data_sources_org` | `organization_id` | RLS helper |
| `data_sources` | `idx_data_sources_sync_schedule` | `sync_schedule` WHERE `enabled=true` | Cron scheduler |
| `model_jobs` | `idx_model_jobs_client_created` | `(client_id, created_at DESC)` | Dashboard recent runs |
| `model_jobs` | `idx_model_jobs_org_status` | `(organization_id, status)` | Ops/queue queries |
| `model_jobs` | `idx_model_jobs_created_by` | `created_by` | User's job history |
| `model_jobs` | `idx_model_jobs_active` | `status` WHERE `status IN ('queued','running')` | Worker polling |
| `channel_results` | `idx_channel_results_job` | `model_job_id` | Job detail page |
| `channel_results` | `idx_channel_results_client` | `(client_id, created_at DESC)` | Historical performance |
| `budget_optimizations` | `idx_budget_optimizations_job` | `model_job_id` | Job detail page |
| `budget_optimizations` | `idx_budget_optimizations_client` | `(client_id, created_at DESC)` | Optimization history |
| `reports` | `idx_reports_share_token` | `share_token` | Public report lookup |
| `reports` | `idx_reports_client_created` | `(client_id, created_at DESC)` | Report listing |
| `reports` | `idx_reports_model_job` | `model_job_id` | Reports for a model run |
| `usage_records` | `idx_usage_records_org_created` | `(organization_id, created_at DESC)` | Billing rollups |
| `insights` | `idx_insights_job` | `model_job_id` | Insights for a job |
| `insights` | `idx_insights_client_type` | `(client_id, type)` | Filtered insight listing |
| `tenant_llm_settings` | `idx_tenant_llm_settings_org` | `organization_id` | LLM config lookup |

### 8.2 GIN Indexes (JSONB Queries)

No GIN indexes are required for MVP. The JSONB columns (`config`, `diagnostics`, `result_summary`, `constraints`, `allocations`, `metrics`, `meta`, `settings`, `control_columns`) are accessed via direct column reads in the API layer, not via JSON path queries. If future features require JSONB path queries (e.g., "find all jobs where config.sampler = 'numpyro'"), GIN indexes should be added at that time.

### 8.3 Unique Constraints (Implicit Indexes)

| Table | Columns | Purpose |
|-------|---------|---------|
| `organizations.slug` | `slug` | URL-safe identifier uniqueness |
| `users.email` | `email` | Login uniqueness |
| `memberships.(organization_id, user_id)` | composite | One role per org per user |
| `clients.(organization_id, slug)` | composite | Slug unique within org |
| `data_sources.(client_id, connector_type, name)` | composite | No duplicate connector names |
| `channel_results.(model_job_id, channel)` | composite | One row per channel per job |
| `reports.share_token` | `share_token` | Public link uniqueness |
| `tenant_llm_settings.organization_id` | `organization_id` | One LLM config per org |

---

## 9. Cross-Reference to Pydantic Schemas

This section provides a quick-reference for the AI coding agent to align DB reads/writes with the existing Pydantic models.

### 9.1 ModelConfig -> model_jobs.config

```python
# Writing: serialize ModelConfig to JSONB
job_row["config"] = model_config.model_dump(mode="json")

# Reading: deserialize JSONB to ModelConfig
model_config = ModelConfig(**job_row["config"])
```

### 9.2 FitResult -> model_jobs (decomposed)

```python
# Writing a completed job:
UPDATE model_jobs SET
  status = 'succeeded',
  diagnostics = fit_result.diagnostics.model_dump(mode="json"),
  result_summary = {"model_id": fit_result.model_id, ...},
  finished_at = now()
WHERE id = :job_id;
```

### 9.3 ChannelContribution -> channel_results

```python
# Writing: bulk insert after training
rows = [
    {
        "organization_id": org_id,
        "client_id": client_id,
        "model_job_id": job_id,
        "channel": c.channel,
        "contribution": c.contribution,
        "share": c.share,
        "roas": c.roas,
        "spend": c.spend,
    }
    for c in contributions
]
# INSERT INTO channel_results ...

# Reading:
contributions = [ChannelContribution(**row) for row in query_result]
```

### 9.4 BudgetConstraints -> budget_optimizations.constraints

```python
# Writing:
opt_row["constraints"] = constraints.model_dump(mode="json")

# Reading:
constraints = BudgetConstraints(**opt_row["constraints"])
```

### 9.5 AllocationResult -> budget_optimizations (decomposed)

```python
# Writing:
INSERT INTO budget_optimizations (
    organization_id, client_id, model_job_id,
    constraints, allocations, total_budget,
    expected_total_revenue, is_feasible, created_by
) VALUES (
    :org_id, :client_id, :job_id,
    :constraints_json, :allocations_json, :total_budget,
    :expected_revenue, :is_feasible, :user_id
);

# Reading:
result = AllocationResult(
    total_budget=row["total_budget"],
    allocations=[Allocation(**a) for a in row["allocations"]],
    expected_total_revenue=row["expected_total_revenue"],
)
```

### 9.6 Insight -> insights

```python
# Writing: bulk insert after LLM generation
for insight in insights_list:
    INSERT INTO insights (organization_id, client_id, model_job_id,
        type, title, body, confidence, metrics, source)
    VALUES (...)

# Reading:
insights = [Insight(**row) for row in query_result]
```

---

## 10. Table Count Summary

| # | Table Name | RLS Enabled | FK Count | Description |
|---|-----------|-------------|----------|-------------|
| 1 | `organizations` | Yes | 0 | Top-level tenant |
| 2 | `users` | Yes | 1 | Auth user profile |
| 3 | `memberships` | Yes | 2 | User-org-role mapping |
| 4 | `clients` | Yes | 1 | Client brands |
| 5 | `data_sources` | Yes | 2 | Connector configs |
| 6 | `model_jobs` | Yes | 3 | Training runs |
| 7 | `channel_results` | Yes | 3 | Per-channel attribution |
| 8 | `budget_optimizations` | Yes | 4 | Optimization results |
| 9 | `reports` | Yes | 4 | Generated reports |
| 10 | `usage_records` | Yes | 1 | Billing metering |
| 11 | `tenant_llm_settings` | Yes | 1 | Per-org LLM config |
| 12 | `insights` | Yes | 3 | AI-generated insights |
| | **Total** | **12** | **25** | |

---

*End of Backend Schema Document.*
