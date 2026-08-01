# MMM Platform — Canonical Specification

## App Overview
- **Name**: MMM Platform
- **Tagline**: AI-powered Marketing Mix Modeling for agencies — measure channels, optimize spend, grow clients faster
- **Problem**: Agencies can't trust click attribution. Traditional MMM is slow (4-8 week consultant cycles), expensive ($10-50k per engagement), and not built for multi-client management. Existing SaaS tools (Measured, Northbeam, Triple Whale) target enterprise brands, not agencies.
- **Solution**: Self-serve Bayesian MMM SaaS that agencies use to connect data, train models in minutes, get AI-powered NL insights, and run budget optimization scenarios for each client — all in one workspace.

## Target Users
- **Primary**: Marketing agencies (media planners, analysts, agency owners) managing 3-50+ client brands
- **Secondary**: DTC / ecommerce brands running in-house marketing
- **Tertiary**: Growth/strategy consultants advising on marketing spend

## User Roles
| Role | Permissions |
|------|------------|
| Agency Owner | Full access: manage team, clients, billing, all models |
| Analyst | Train models, run optimizer, generate reports, manage data connectors |
| Viewer | Read-only dashboard access |
| Client (external) | Read-only shared report view (link-based) |

## Tech Stack (Decided)
| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Frontend | Next.js 15 + React 19 + Tailwind CSS + shadcn/ui |
| Database | Supabase (PostgreSQL + Row-Level Security + Auth) |
| Job queue | Celery + Redis (model training, data sync) |
| MMM engine | PyMC-Marketing (Bayesian MMM on PyMC) |
| LLM | Ollama default (Qwen2.5-7B), pluggable Claude + OpenAI via LLMProvider protocol |
| Model storage | S3 / R2 (ArviZ NetCDF traces, keyed by tenant+client) |
| Auth | Supabase Auth (JWT) + NextAuth.js |
| Deployment | Vercel (frontend) + Railway/Fly.io (backend) + Supabase (DB) |

## Core Features (MVP)

### F1: Data Connectors
- One-click CSV upload (universal fallback)
- Meta Marketing API, Google Ads API, GA4 Data API, TikTok Marketing API, Shopify Admin API
- Canonical schema: date, channel, spend, impressions, clicks, conversions, revenue
- Scheduled sync (weekly auto-pull)

### F2: MMM Model Training
- Configure priors, adstock, saturation, sampler, chains/draws
- Train with PyMC-Marketing; background job via Celery
- Diagnostics: R-hat convergence, R², MAPE, posterior predictive check
- Save/load model artifacts

### F3: Channel Attribution
- Channel contribution %, ROAS, spend vs revenue
- Response curves (diminishing returns)
- Time decomposition (trend, seasonality, media)

### F4: Budget Optimizer
- Set total budget + per-channel constraints (min/max %, absolute floors)
- Scipy optimizer + PyMC allocate_budget fallback
- Expected revenue output per channel

### F5: AI Insights (NL)
- Auto-generated channel insights, budget recommendations, anomaly alerts
- Executive summary report (LLM-generated)
- Scenario Q&A: "What if I shift 20% from TV to Meta?"
- Template fallback when LLM down

### F6: Multi-Client Dashboard
- Agency workspace: list clients, switch between them
- Dashboard: KPIs, recent model runs, channel performance cards
- Model history (run date, status, diagnostics)

### F7: Reports & Export
- Auto-generated MMM report with sections: overview, channel analysis, budget recs, risks
- PDF export
- Shareable link (client view)

## Data Model (Key Entities)
- Organization (agency) → Users (memberships with roles)
- Clients (belong to org)
- DataSources (per client: connector type + encrypted credentials)
- ModelJobs (per client: config, status, result summary, artifact path)
- UsageRecords (org-level: compute, storage, API calls)

## Constraints & Non-MVP
- **V2 / later**: incrementality test calibration, A/B test integration, programmatic (DV360/TTD) connectors, white-label branding, SSO (SAML), Stripe billing, audit log, multi-geo MMM, mobile app
- **Not building**: MTA/pixel tracking, social media scheduling, creative tools, ad builder, SEO tools

## Success Metrics
- Time to first model: <15 min from CSV upload
- Model R² target: >0.7 for ecommerce datasets
- Agency activation: onboard 5 agencies in first month post-launch
- Model training: <5 min per model on CPU, <2 min on GPU

## Pricing (Hypothesis)
| Tier | Price | Clients | Model Trains/mo |
|------|-------|---------|----------------|
| Starter | $199/mo | 3 | 20 |
| Pro | $499/mo | 15 | 100 |
| Enterprise | Custom | Unlimited | Unlimited |
