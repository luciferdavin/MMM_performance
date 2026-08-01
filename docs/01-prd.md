# Product Requirements Document: MMM Platform

**Version:** 1.0
**Date:** 2026-08-01
**Author:** Senior Product Manager
**Status:** Draft for review

---

## 1. App Name and Description

**MMM Platform** — AI-powered Marketing Mix Modeling for agencies: measure channels, optimize spend, grow clients faster.

MMM Platform is a self-serve, multi-tenant SaaS tool that enables marketing agencies to connect advertising data, train Bayesian Marketing Mix Models, receive AI-generated natural-language insights, and run budget optimization scenarios for each of their clients — all from a single workspace.

---

## 2. Target Users (Personas)

### Primary: Marketing Agency Teams

| Persona | Role | Daily Work | Key Frustration |
|---------|------|-----------|-----------------|
| **Maya, Agency Owner** | Founder of a 15-person digital agency managing 20 DTC clients | Oversees client strategy, reports to stakeholders, manages billing and team capacity | Cannot justify $10–50k per client for MMM consulting; needs scalable measurement across all accounts |
| **Jordan, Media Planner** | Senior planner running campaigns across Meta, Google, TikTok, Shopify for 8 clients | Allocates budgets, evaluates channel performance, builds quarterly media plans | Relies on platform-reported ROAS that conflicts across channels; no unified view of true incrementality |
| **Alex, Data Analyst** | In-house analyst responsible for measurement and reporting for the agency | Pulls data from ad platforms, builds dashboards, trains models, generates reports | Spends 3–4 days per week stitching data from 6+ platforms; model training takes weeks via external consultants |

### Secondary: In-House Marketing Teams

| Persona | Role | Key Frustration |
|---------|------|-----------------|
| **Priya, DTC Brand Marketing Lead** | Runs paid media for a Shopify brand doing $5M ARR | Cannot attribute revenue across channels; wastes budget on over-reported platforms |
| **Sam, Growth Consultant** | Advises 3–5 brands on marketing spend allocation | No affordable self-serve MMM tool; relies on spreadsheets and ad-hoc analysis |

### Tertiary: External Stakeholders

| Persona | Role | Key Frustration |
|---------|------|-----------------|
| **Client Executive** | Receives reports from agency; makes budget decisions | Reports are static PDFs with no way to explore scenarios interactively |

---

## 3. Problem Statement

**Core problem:** Marketing agencies cannot trust click-based attribution as third-party cookies decay and platform-reported ROAS inflates. Traditional Marketing Mix Modeling is too slow (4–8 week consultant cycles), too expensive ($10–50k per engagement), and not designed for multi-client management.

**Context:**

1. **Attribution decay.** Platform-reported metrics (Meta ROAS, Google attributed conversions) over-credit their own channels. Agencies lack a neutral, cross-channel view of true contribution.

2. **Consultant MMM is not scalable.** A typical agency engagement costs $10–50k and takes 4–8 weeks per client. For an agency managing 20 clients, this means $200k–$1M annually just for measurement, with results arriving too late to act on.

3. **Existing SaaS tools target brands, not agencies.** Measured targets enterprise brands directly. Northbeam and Triple Whale support some agency use cases but are MTA-first (pixel-based), not MMM-native, and price at enterprise levels.

4. **Data collection is manual and fragmented.** Analysts spend most of their time pulling CSVs from 6+ ad platforms, normalizing schemas, and reconciling discrepancies — not analyzing results.

5. **Client education is hard.** Non-technical client stakeholders cannot interpret statistical output; agencies need plain-English insights and scenario planning to drive decisions.

---

## 4. Core Solution

MMM Platform provides a self-serve, agency-first Bayesian MMM SaaS that:

1. **Connects data in minutes** — one-click CSV upload (universal fallback) plus native API connectors for Meta, Google Ads, GA4, TikTok, and Shopify. All connectors normalize to a canonical schema (date, channel, spend, impressions, clicks, conversions, revenue).

2. **Trains models fast** — wraps PyMC-Marketing (Bayesian MMM on PyMC) with a Celery job queue. Agencies configure priors, adstock, and saturation, then train models in under 5 minutes on CPU (under 2 minutes on GPU). No statistical expertise required for defaults.

3. **Delivers AI-powered insights** — generates natural-language channel analysis, budget recommendations, anomaly alerts, and executive summaries using a pluggable LLM layer. Default: self-hosted Ollama (Qwen2.5-7B) for zero API cost; swappable to Claude or OpenAI.

4. **Optimizes budgets** — run budget scenarios: set total budget, per-channel constraints (min/max percentages, absolute floors), and get expected revenue output per channel via scipy-based optimization.

5. **Manages multiple clients** — agency workspace with client switching, per-client data isolation, role-based access (Owner, Analyst, Viewer, Client), and shareable report links.

---

## 5. Main Features

### F1: Data Connectors

**Purpose:** Eliminate manual data wrangling so analysts can start modeling immediately.

| Aspect | Detail |
|--------|--------|
| **CSV Upload** | Universal fallback. Drag-and-drop or file picker. Validates schema (date, channel, spend, impressions, clicks, conversions, revenue). Supports pasted tabular data. |
| **Meta Marketing API** | OAuth2 long-lived token. Pulls insights endpoint with `time_increment=1`. Maps campaign-level spend, impressions, clicks, conversions, revenue. |
| **Google Ads API** | OAuth2 + developer token. GAQL queries. Converts `cost_micros` to spend. Pulls campaign-level performance. |
| **GA4 Data API** | Service account auth. Pulls organic sessions, revenue, and traffic source data. |
| **TikTok Marketing API** | Access token auth. Integrated report endpoint. Maps spend, impressions, clicks, conversions. |
| **Shopify Admin API** | `X-Shopify-Access-Token` auth. Orders endpoint for revenue data. Essential for ecommerce clients. |
| **Scheduled Sync** | Weekly auto-pull per data source. Configurable schedule (daily/weekly/monthly). Background Celery job. |
| **Canonical Schema** | Every connector normalizes to: `date` (datetime), `channel` (str), `pend` (float), `impressions` (int), `clicks` (int), `conversions` (int), `revenue` (float). |
| **Credential Storage** | Encrypted per-tenant `data_sources` table. Never in code. Secret reference pattern. |
| **Error Handling** | Rate limiting with exponential backoff on HTTP 429. Connector status dashboard (configured/not configured/error). Retry logic for transient failures. |

**Connector Priority (MVP):**

| Priority | Connector | Status |
|----------|-----------|--------|
| P0 | CSV Upload | MVP |
| P0 | Shopify | MVP |
| P1 | Meta Ads | MVP |
| P1 | Google Ads | MVP |
| P1 | GA4 | MVP |
| P2 | TikTok | MVP |
| P2 | LinkedIn / Snap / Pinterest | Post-MVP |
| P3 | Programmatic (DV360/TTD) | Post-MVP |

### F2: MMM Model Training

**Purpose:** Enable agencies to train statistically rigorous MMM models without hiring data scientists.

| Aspect | Detail |
|--------|--------|
| **Engine** | PyMC-Marketing (Bayesian MMM on PyMC). Apache 2.0 license. Scikit-learn-style `fit()` / `predict()` API. |
| **Configuration UI** | Form-based setup: select data source, date range, channels, prior distributions, adstock type (geometric, delayed, Weibull left/right), saturation function (Hill, Michaelis-Menten), sampler (NUTS, NumPyro), chains, draws. |
| **Sensible Defaults** | Pre-configured industry priors for DTC/ecommerce. One-click "recommended settings" button. |
| **Training Execution** | Background Celery job. Real-time progress bar (sampling iterations). Estimated time remaining. |
| **Diagnostics Dashboard** | R-hat convergence (target <1.05), R-squared, MAPE, posterior predictive check visualization. Traffic-light indicators (green/yellow/red). |
| **Model Artifacts** | Saved as ArviZ NetCDF traces. Stored in S3/R2, keyed by tenant + client + model ID. Versioned (not overwritten). |
| **Model History** | Timeline view: run date, config snapshot, status, diagnostics, artifact link. Compare two models side by side. |
| **Control Variables** | Support for: holiday calendar (US + target markets), Google Trends index, pricing changes/promos, macro indicators (CPI, seasonality dummies). Optional, not required. |

### F3: Channel Attribution

**Purpose:** Show agencies and their clients which channels actually drive revenue.

| Aspect | Detail |
|--------|--------|
| **Channel Contribution %** | Percentage of total revenue attributed to each channel, with credible intervals. |
| **ROAS per Channel** | Revenue attributed / spend per channel. |
| **Spend vs. Revenue Chart** | Stacked area or grouped bar showing spend allocation alongside attributed revenue over time. |
| **Response Curves** | Per-channel diminishing returns curves. Shows marginal ROI at current spend level. Identifies channels with room to scale vs. those at saturation. |
| **Time Decomposition** | Decompose revenue into: trend, seasonality, media contribution, baseline. |
| **Comparison Mode** | Compare attribution across two time periods (e.g., Q1 vs. Q2, pre/post campaign). |

### F4: Budget Optimizer

**Purpose:** Replace gut-feel budget allocation with data-driven optimization.

| Aspect | Detail |
|--------|--------|
| **Total Budget Input** | User enters total monthly/quarterly budget. |
| **Per-Channel Constraints** | Min %, max %, absolute floor (dollar amount) per channel. Lock channels at current spend. |
| **Optimization Engine** | Scipy optimizer + PyMC `allocate_budget()` fallback. Maximizes expected revenue subject to constraints. |
| **Output** | Recommended spend per channel, expected revenue per channel, total expected revenue, marginal ROAS per channel. |
| **Scenario Comparison** | Side-by-side view: current allocation vs. optimized allocation vs. custom scenario. |
| **Sensitivity Analysis** | What happens to total revenue if budget changes by +/-10%, 20%, 50%? |

### F5: AI Insights (Natural Language)

**Purpose:** Translate statistical output into actionable business language.

| Aspect | Detail |
|--------|--------|
| **Channel Insights** | Auto-generated per-channel analysis: ROAS trends, contribution changes, anomalies. |
| **Budget Recommendations** | Natural-language reallocation suggestions with expected revenue impact. |
| **Anomaly Alerts** | Detect unusual spend/CPM/ROAS deviations and explain likely causes. |
| **Executive Summary** | One-page narrative: key findings, top 3 recommendations, risks. Generated as part of report. |
| **Scenario Q&A** | Conversational interface: "What if I shift 20% from TV to Meta?" — returns modeled impact in plain English. |
| **LLM Provider** | Pluggable via `LLMProvider` protocol. Default: Ollama (Qwen2.5-7B). Options: Claude (Anthropic SDK), OpenAI. |
| **Template Fallback** | When LLM is unavailable, fall back to template-based `_fallback_report` with static phrasing and model data. |
| **Guardrails** | Always cite actual model numbers. Never fabricate metrics. Include confidence intervals where available. |

### F6: Multi-Client Dashboard

**Purpose:** Give agencies a single workspace to manage all clients.

| Aspect | Detail |
|--------|--------|
| **Client List** | Table view: client name, industry, last model run, status, quick actions. |
| **Client Switching** | Dropdown or sidebar to switch between client contexts. All views scoped to selected client. |
| **Dashboard View** | Per-client: KPI cards (total spend, total revenue, blended ROAS, best channel), recent model runs, channel performance summary. |
| **Model History** | Timeline of all model runs for the client: date, status (running/complete/failed), diagnostics summary, link to full results. |
| **Cross-Client Overview** | Agency-level summary: total spend across all clients, average ROAS, top-performing channels across portfolio. |
| **Quick Actions** | One-click: upload data, train model, run optimizer, generate report — from dashboard. |

### F7: Reports and Export

**Purpose:** Deliver professional, client-ready output.

| Aspect | Detail |
|--------|--------|
| **Auto-Generated Report** | Sections: Executive Summary, Channel Analysis, Budget Recommendations, Model Diagnostics, Risks & Caveats. |
| **PDF Export** | One-click PDF download. Branded with agency logo (configurable). |
| **Shareable Link** | Generate a public link for client stakeholders. Read-only view. No login required. Link expiration configurable. |
| **Client View** | Simplified dashboard: key metrics, channel breakdown, budget recommendations. No technical diagnostics. |

---

## 6. User Roles and Permissions

| Role | Description | Can Do | Cannot Do |
|------|-------------|--------|-----------|
| **Agency Owner** | Full access to the agency workspace | Manage team members (invite, remove, change roles). Manage clients (add, edit, delete). Manage billing and subscription. Train models, run optimizer, generate reports. Access all client data. Configure data connectors. |
| **Analyst** | Primary model builder and data manager | Train models, run optimizer, generate reports. Manage data connectors (add, edit, delete). View and analyze all client data within the agency. Cannot manage team members or billing. |
| **Viewer** | Read-only stakeholder (e.g., account manager) | View dashboards, reports, and model results. Cannot train models, modify data, or change settings. |
| **Client (External)** | Agency's client stakeholder | View shared report via link. Read-only. Cannot access the agency workspace, other clients, or any internal data. |

**Implementation:** Supabase Row-Level Security (RLS) policies enforce role boundaries. Each API request includes a JWT with `org_id`, `user_id`, and `role`. RLS policies on every table check `org_id` membership and role.

---

## 7. User Stories

### Agency Owner Stories

**US-01: Onboard the agency**
As Maya (Agency Owner), I want to create an agency workspace, invite my team members with roles, and add my first client so that we can start measuring channel performance.
- Acceptance criteria: Create org, invite users via email, assign roles (Analyst, Viewer), add client with name/industry. Team members receive invite email and can log in.

**US-02: Manage billing and subscription**
As Maya, I want to view my current plan, usage (model trains, clients), and upgrade or downgrade so that I can control costs as my agency grows.
- Acceptance criteria: Billing page shows current tier, client count, model trains used/remaining. Upgrade/downgrade flow with confirmation.

**US-03: Review cross-client performance**
As Maya, I want an agency-level overview showing total spend, average ROAS, and top channels across all clients so that I can identify portfolio-level trends and opportunities.
- Acceptance criteria: Dashboard aggregates metrics across all clients. Sortable by client, channel, time period.

### Analyst Stories

**US-04: Connect a data source**
As Alex (Analyst), I want to connect a client's Meta Ads account with one click (OAuth) so that I can pull their spend and performance data without manual CSV exports.
- Acceptance criteria: OAuth flow completes, data source appears as "Connected" in the client's data sources list, historical data is pulled and visible in the data preview table.

**US-05: Upload CSV data**
As Alex, I want to drag-and-drop a CSV file containing my client's marketing data so that I can quickly onboard a client without API setup.
- Acceptance criteria: CSV is validated against the canonical schema, missing columns are flagged with helpful error messages, valid data appears in the client's data preview.

**US-06: Train an MMM model**
As Alex, I want to configure model settings (date range, channels, priors) and click "Train" so that I get a Bayesian MMM trained on my client's data.
- Acceptance criteria: Configuration form shows recommended defaults. Training starts as background job. Progress bar updates in real time. Model completes with diagnostics (R-hat, R-squared, MAPE). Model appears in model history.

**US-07: Review model diagnostics**
As Alex, I want to see convergence metrics (R-hat), fit quality (R-squared, MAPE), and posterior predictive checks so that I can verify the model is trustworthy before sharing results.
- Acceptance criteria: Diagnostics page shows all metrics with traffic-light indicators. R-hat < 1.05 = green. R-squared > 0.7 = green. Posterior predictive check chart visible.

**US-08: View channel attribution**
As Alex, I want to see each channel's contribution percentage, ROAS, and response curve so that I can understand which channels drive the most value.
- Acceptance criteria: Attribution table shows channel, contribution %, ROAS, spend, attributed revenue. Response curves are interactive (hover to see marginal ROI at any spend level).

**US-09: Run budget optimizer**
As Alex, I want to set a total budget and per-channel constraints, then run the optimizer so that I get a recommended spend allocation that maximizes expected revenue.
- Acceptance criteria: Optimizer form accepts total budget, min/max per channel, floor amounts. Output shows recommended allocation, expected revenue per channel, and comparison to current allocation.

**US-10: Generate AI insights**
As Alex, I want the system to automatically generate natural-language insights about channel performance, budget recommendations, and anomalies so that I can quickly prepare a client-ready analysis.
- Acceptance criteria: Insight panel shows per-channel narrative, budget recommendation with expected impact, anomaly alerts. All insights cite actual model numbers.

**US-11: Ask scenario questions**
As Alex, I want to ask "What if I shift 20% from TV to Meta?" and get a modeled response in plain English so that I can quickly explore alternatives with my client.
- Acceptance criteria: Chat interface accepts natural-language question. Response includes modeled revenue impact, confidence interval, and caveat about assumptions.

**US-12: Generate and share a report**
As Alex, I want to generate an auto-formatted MMM report, export it as PDF, and share a link with my client so that they can review findings without needing platform access.
- Acceptance criteria: Report generates with sections (executive summary, channel analysis, budget recs, risks). PDF downloads with agency logo. Shareable link renders a read-only client view. Link can be set to expire.

**US-13: Switch between clients**
As Alex, I want to quickly switch between client workspaces so that I can manage multiple accounts without logging in and out.
- Acceptance criteria: Client dropdown/switcher in sidebar. All views update to show data for selected client. No data leakage between clients.

### Viewer Stories

**US-14: View a client dashboard**
As Jordan (Viewer), I want to see the KPI dashboard for a specific client so that I can understand their performance without asking the analyst to pull data.
- Acceptance criteria: Dashboard loads with KPI cards, channel performance, recent model runs. Read-only — no buttons to train models or modify data.

**US-15: Review model history**
As Jordan, I want to see the history of model runs for a client so that I can track how attribution has changed over time.
- Acceptance criteria: Model history list shows date, status, diagnostics summary. Clicking a run opens read-only results.

### Client (External) Stories

**US-16: View a shared report**
As a Client Executive, I want to click a link from my agency and see a professional MMM report so that I can understand my marketing performance without learning a new tool.
- Acceptance criteria: Link opens a simplified view. Shows key metrics, channel breakdown, budget recommendations. No login required. Agency branding visible.

**US-17: Explore budget scenarios**
As a Client Executive, I want to adjust a budget slider and see the expected revenue impact so that I can make informed decisions about spend changes.
- Acceptance criteria: Interactive slider adjusts total budget. Revenue forecast updates in real time. Disclaimer that results are model-based estimates.

### Cross-Cutting Stories

**US-18: Receive anomaly alerts**
As any user, I want to be notified when the system detects unusual spend patterns or ROAS deviations so that I can investigate before wasting budget.
- Acceptance criteria: Alert appears in dashboard and (optionally) via email. Alert includes channel, metric, deviation magnitude, and suggested investigation.

**US-19: Use control variables**
As Alex, I want to include holiday effects and Google Trends data in my model so that the attribution is more accurate and accounts for external factors.
- Acceptance criteria: Control variable configuration section in model setup. Holiday calendar auto-populated for US. Google Trends integration optional.

**US-20: Manage model artifacts**
As Alex, I want to save, version, and reload model artifacts so that I can compare models over time and avoid re-training from scratch.
- Acceptance criteria: Models are saved automatically after training. Version list shows all artifacts. "Load" button restores a previous model's results. Storage uses S3/R2 keyed by tenant+client.

---

## 8. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Time to first model** | <15 minutes from CSV upload | Track time from upload initiation to model completion |
| **Model R-squared** | >0.7 for ecommerce datasets | Computed by PyMC-Marketing diagnostics |
| **Model training time (CPU)** | <5 minutes per model | Celery job duration logging |
| **Model training time (GPU)** | <2 minutes per model | Celery job duration logging |
| **Agency activation** | 5 agencies onboarded in first month post-launch | Sign-up tracking |
| **Weekly active agencies** | 3+ agencies running models weekly by month 3 | Activity logging |
| **Data connector success rate** | >95% of API pulls succeed on first attempt | Connector error logging |
| **Report generation time** | <30 seconds for full PDF report | API response time tracking |
| **NPS (agencies)** | >40 at 3 months | In-app survey |
| **Client share-link open rate** | >60% of shared links viewed | Link click tracking |
| **Model accuracy (user-reported)** | >80% of users rate model as "trustworthy" | Post-model survey |

---

## 9. MVP Scope (What IS in V1)

### Data Layer
- CSV upload with schema validation
- Meta Marketing API connector (OAuth2)
- Google Ads API connector (OAuth2 + developer token)
- GA4 Data API connector (service account)
- TikTok Marketing API connector (access token)
- Shopify Admin API connector (access token)
- Scheduled weekly sync for all API connectors
- Canonical schema normalization
- Encrypted credential storage per tenant

### Modeling
- PyMC-Marketing Bayesian MMM engine
- Configuration UI (priors, adstock, saturation, sampler settings)
- Sensible defaults for DTC/ecommerce
- Background training via Celery + Redis
- Real-time training progress
- Diagnostics dashboard (R-hat, R-squared, MAPE, posterior predictive check)
- Model artifact storage (S3/R2, ArviZ NetCDF)
- Model versioning and history

### Attribution and Optimization
- Channel contribution %, ROAS, spend vs. revenue
- Response curves (diminishing returns)
- Time decomposition (trend, seasonality, media)
- Budget optimizer with per-channel constraints
- Scenario comparison (current vs. optimized vs. custom)
- Control variables (holidays, Google Trends)

### AI Insights
- LLM provider abstraction (Ollama default, Claude, OpenAI)
- Auto-generated channel insights
- Budget recommendations
- Anomaly alerts
- Executive summary generation
- Scenario Q&A chat interface
- Template fallback when LLM is unavailable

### Multi-Client Management
- Agency workspace with client list
- Client switching (sidebar/dropdown)
- Per-client data isolation (RLS)
- Role-based access (Owner, Analyst, Viewer, Client)
- Agency-level cross-client overview

### Reports and Export
- Auto-generated MMM report (sections: overview, channel analysis, budget recs, risks)
- PDF export with agency branding
- Shareable link (client view, read-only, no login)
- Link expiration settings

### Infrastructure
- Supabase (PostgreSQL, RLS, Auth)
- FastAPI backend
- Next.js 15 + React 19 + Tailwind + shadcn/ui frontend
- Vercel (frontend) + Railway/Fly.io (backend) deployment
- JWT-based auth (Supabase Auth + NextAuth.js)

---

## 10. Out of Scope (What Is NOT in V1)

### Explicitly Not Building
- **MTA/pixel tracking** — MMM Platform is MMM-first, not an MTA tool
- **Social media scheduling or creative tools** — not an ad builder
- **SEO tools** — outside measurement scope
- **White-label branding** — V2 feature
- **SSO (SAML)** — V2 feature
- **Stripe billing integration** — V2 (manual billing for early adopters)
- **Audit log** — V2 feature
- **Multi-geo MMM** — V2 feature
- **Mobile app** — V2 feature
- **Programmatic connectors (DV360, TTD)** — V2, P3 priority
- **LinkedIn, Snap, Pinterest connectors** — V2, P2 priority
- **Incrementality test calibration** — V2, requires lift-test integration
- **A/B test integration** — V2
- **Industry benchmark priors** — V2 (requires curated dataset)
- **API access for agency internal tooling** — V2

### What V1 Will Not Do Well (Known Limitations)
- No GPU-accelerated training in cloud deployment (CPU only for V1 managed hosting; GPU available for self-hosted)
- No automated model selection (user must configure priors manually; "recommended settings" button is a starting point, not optimization)
- No real-time data streaming (batch sync only, weekly by default)
- Limited to US holiday calendar (international calendars in V2)

---

## 11. Key Assumptions

| # | Assumption | Risk if Wrong | Validation Method |
|---|-----------|---------------|-------------------|
| 1 | Agencies will pay $199–499/mo for a self-serve MMM tool rather than hiring consultants at $10–50k per engagement | Low adoption; agencies stick with consultants | Landing page sign-up rate, early conversations with 10 agency owners |
| 2 | PyMC-Marketing can produce R-squared >0.7 on typical ecommerce datasets with default priors | Model quality insufficient; users lose trust | Benchmark against 5 real ecommerce datasets before launch |
| 3 | Ollama (Qwen2.5-7B) produces sufficiently reliable structured JSON for insight generation on commodity hardware | Insights are garbled or hallucinated; users disable AI | A/B test Ollama vs. OpenAI insights with 10 analysts; measure "useful" rating |
| 4 | Agencies prefer CSV upload over API connectors for initial onboarding | API setup friction blocks activation | Track first-model funnel: % who use CSV vs. API for first data source |
| 5 | A 15-minute time-to-first-model is achievable on CPU with typical ecommerce datasets (2–3 years of weekly data, 5–10 channels) | Training is too slow; users abandon | Benchmark training time on reference hardware (8-core CPU, 32GB RAM) |
| 6 | Multi-client workspace is the primary adoption driver (vs. single-client features) | Agencies use it for one client only; no expansion | Track clients-per-agency over first 90 days |
| 7 | Shareable client report links will be used by >50% of agencies | Agencies prefer sending PDFs; links ignored | Track link generation vs. view counts |
| 8 | Bayesian uncertainty intervals are a selling point (vs. deterministic point estimates) | Users find credible intervals confusing | Survey: "Did the uncertainty intervals help you make a decision?" |

---

## 12. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Model quality does not meet user expectations** — R-squared <0.7 on some datasets, leading to distrust | Medium | High | Pre-launch: benchmark on 5+ real datasets. Ship "recommended settings" that produce good defaults. Include model diagnostics prominently so users can assess quality before sharing results. Offer "model quality tips" in docs. |
| 2 | **API connector reliability** — platform APIs change, rate limits hit, OAuth tokens expire mid-sync | High | Medium | Exponential backoff retry. Connector health dashboard with status indicators. Email alerts on sync failure. Manual CSV fallback always available. |
| 3 | **LLM insight quality** — Ollama generates unreliable or hallucinated insights, eroding trust | Medium | High | Guardrail: always cite actual model numbers. Pydantic validation on LLM output. Template fallback when LLM unavailable. Option to disable AI insights and show raw data only. |
| 4 | **Slow training on CPU** — large datasets (100+ weeks, 20+ channels) exceed 5-minute target | Medium | Medium | Preprocessing: channel aggregation, date-range pruning. GPU option for self-hosted. Progress bar with ETA. Auto-recommend smaller channel set if training is slow. |
| 5 | **Low agency adoption** — agencies prefer existing tools or spreadsheets | Medium | High | Position as complement to (not replacement for) existing workflow. Focus on time savings (15 min vs. 4–8 weeks). Offer free trial. Target 5 design-partner agencies for feedback before general launch. |
| 6 | **Data security concerns** — agencies hesitant to connect ad platform APIs to a new SaaS | Medium | High | SOC 2 readiness roadmap. Credentials encrypted at rest (Supabase vault). No raw ad data stored beyond what's needed for modeling. Transparent data flow documentation. |
| 7 | **Competitive response** — Triple Whale, Northbeam, or Measured add agency-first MMM features | Low (12 mo) | High | Ship fast. Differentiate on: open-source engine (PyMC-Marketing), zero-cost LLM (Ollama), agency-first UX. Build switching costs via client data and model history. |
| 8 | **Scope creep** — stakeholders request V2 features (SSO, white-label, incrementality) before V1 is stable | High | Medium | Strict V1 scope document (this PRD). Feature request backlog in product management tool. V2 roadmap published to set expectations. |
| 9 | **Supabase vendor lock-in** — dependency on Supabase for auth, RLS, database | Low | Medium | Standard PostgreSQL under the hood. Supabase provides migration tooling. Document all RLS policies for portability. |
| 10 | **Open-source engine risk** — PyMC-Marketing is maintained by PyMC Labs; if maintenance lapses, we inherit the burden | Low | Medium | Monitor GitHub activity quarterly. Fork if necessary (Apache 2.0). Google Meridian as documented fallback engine. |

---

## Appendix: Pricing Hypothesis

| Tier | Price | Clients | Model Trains/mo | Target Segment |
|------|-------|---------|-----------------|----------------|
| Starter | $199/mo | 3 | 20 | Small agencies (3–5 people) |
| Pro | $499/mo | 15 | 100 | Growth agencies (10–30 people) |
| Enterprise | Custom | Unlimited | Unlimited | Large agencies (30+ people) |

**Notes:**
- Pricing validated with 5+ agency owners before launch.
- Usage overages: $25 per additional model train, $15 per additional client.
- Annual discount: 20% (i.e., Starter = $1,908/yr vs. $2,388/yr monthly).

---

## Appendix: Tech Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3.11 + FastAPI | PyMC-Marketing is Python-native; async support for connectors |
| Frontend | Next.js 15 + React 19 + Tailwind + shadcn/ui | Modern React; fast iteration; component library |
| Database | Supabase (PostgreSQL + RLS + Auth) | Multi-tenant isolation, built-in auth, managed hosting |
| Job Queue | Celery + Redis | Background model training, data sync scheduling |
| MMM Engine | PyMC-Marketing (Bayesian MMM on PyMC) | Best-in-class open-source Bayesian MMM; Apache 2.0 |
| LLM | Ollama default (Qwen2.5-7B), pluggable Claude/OpenAI | Zero-cost default; data stays in-house; enterprise option |
| Model Storage | S3 / R2 (ArviZ NetCDF traces) | Keyed by tenant + client; versioned |
| Auth | Supabase Auth (JWT) + NextAuth.js | Seamless full-stack auth; social login for agency users |
| Deployment | Vercel (frontend) + Railway/Fly.io (backend) + Supabase (DB) | Managed hosting; low ops burden for V1 |

---

*End of PRD.*
