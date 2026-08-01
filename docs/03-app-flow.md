# MMM Platform — App Flow Document

**Document**: `docs/03-app-flow.md`
**Role**: UX Strategist
**Source of truth**: `docs/_spec.md` (canonical spec) + `research/*` (competitor landscape, data-connector-spec, mmm-engine-comparison, ai-insights-layer, agency-workflow)
**Status**: MVP definition — build-ready
**App**: MMM Platform — "AI-powered Marketing Mix Modeling for agencies — measure channels, optimize spend, grow clients faster"

---

## 1. Product Overview & Goals

### 1.1 What the product is

MMM Platform is a self-serve, multi-tenant Bayesian Marketing Mix Modeling (MMM) SaaS built **for marketing agencies**. An agency connects each client's marketing data (platform APIs or CSV), trains a Bayesian MMM in minutes, and gets:

- Channel attribution (contribution %, ROAS, response curves)
- Budget optimization scenarios (what-if reallocations)
- AI-generated natural-language insights and executive reports
- Shareable read-only client reports

### 1.2 UX success metrics (from spec)

| Metric | Target |
|--------|--------|
| Time to first trained model (CSV upload → completed) | < 15 minutes |
| Model train wall-clock time | < 5 min CPU / < 2 min GPU |
| Agency activation | 5 agencies onboarded in first month |
| Model quality bar | R² > 0.7 on ecommerce datasets |

These targets directly shape the UI: onboarding must be a short wizard, training must run asynchronously with progress feedback, and the "aha" moment (first trained model) must be reachable in a single sitting.

### 1.3 Positioning statement (drives copy tone)

> "Self-serve Bayesian MMM with AI insights — built for agencies managing many clients. Connect data, train in minutes, get NL budget recommendations. No consultants, no 8-week waits, no per-client enterprise pricing."

Tone: professional, data-confident, non-technical-user friendly. Avoid jargon without inline explanation (e.g., "R-hat (convergence check)").

---

## 2. Users, Roles & Permissions

From spec, four roles. The first three are authenticated app users; the fourth is an unauthenticated link-based viewer.

| Role | Auth | Permissions | Cannot do |
|------|------|-------------|-----------|
| **Agency Owner** | Supabase Auth | Everything: manage team, billing, all clients, all models, connectors, reports, delete clients | — |
| **Analyst** | Supabase Auth | Train models, run optimizer, generate reports, manage data connectors, manage clients (add/edit) | Manage team, manage billing, delete clients, change org settings |
| **Viewer** | Supabase Auth | Read-only dashboard, model history, attribution, reports (view/export PDF) | Train models, run optimizer, edit connectors, add clients, manage team |
| **Client (external)** | None (share token) | View a single shared report (read-only, no auth) | Anything else; no access to workspace |

**Permission enforcement**: enforced server-side via Supabase RLS + FastAPI dependency injection. UI hides/ disables actions the current role cannot perform (never relies on client-side hiding alone). Role-gating tables appear in Sections 5 and 15.

---

## 3. Information Architecture — Full Page Inventory

### 3.1 Site map

```
/                                            Landing page (marketing)
/login                                       Sign in
/signup                                      Create account
/forgot-password                             Reset password
/onboarding                                  Onboarding wizard (post-signup)
/share/[token]                               Client shared report (no auth)

/app/dashboard                               Workspace dashboard (home)
/app/clients                                 Client list
/app/clients/new                             Add client (form page)
/app/clients/[clientId]/overview             Client detail / KPI dashboard
/app/clients/[clientId]/data-sources         Data sources list
/app/clients/[clientId]/data-sources/connect Connect data source wizard
/app/clients/[clientId]/models               Model history
/app/clients/[clientId]/models/new           New model / configure + train
/app/clients/[clientId]/models/[jobId]       Model detail + diagnostics
/app/clients/[clientId]/attribution          Channel attribution
/app/clients/[clientId]/optimizer            Budget optimizer
/app/clients/[clientId]/optimizer/[scenarioId]  Saved optimization scenario
/app/clients/[clientId]/insights             AI insights & reports list
/app/clients/[clientId]/insights/[reportId]  Report detail (review/export/share)
/app/settings/team                           Team management
/app/settings/connectors                     Org-level connector credentials (OAuth token storage, default accounts)
/app/settings/billing                        Subscription / plan / usage
/app/settings/profile                        Current user profile
```

### 3.2 Complete page inventory

| # | Route | Page | Primary audience | Requires auth | Purpose |
|---|-------|------|------------------|---------------|---------|
| 1 | `/` | Landing | Prospects | No | Explain product, pricing, CTA to signup |
| 2 | `/login` | Sign in | All users | No | Email/password + magic link + OAuth |
| 3 | `/signup` | Create account | Prospects | No | Create org + owner account |
| 4 | `/forgot-password` | Password reset | All users | No | Request reset email |
| 5 | `/onboarding` | Onboarding wizard | New owner | Yes | Org setup → first client → connect data → first model |
| 6 | `/app/dashboard` | Workspace dashboard | Owner, Analyst, Viewer | Yes | Cross-client KPIs, recent jobs, quota |
| 7 | `/app/clients` | Client list | Owner, Analyst | Yes | Add / select / search clients |
| 8 | `/app/clients/new` | Add client | Owner, Analyst | Yes | Create client record |
| 9 | `/app/clients/[clientId]/overview` | Client detail | All | Yes | Client KPIs, latest model, quick actions |
| 10 | `/app/clients/[clientId]/data-sources` | Data sources | Owner, Analyst | Yes | List/manage connectors for client |
| 11 | `/app/clients/[clientId]/data-sources/connect` | Connect wizard | Owner, Analyst | Yes | Choose platform → auth → configure → verify |
| 12 | `/app/clients/[clientId]/models` | Model history | All | Yes | Job list, statuses, retrain |
| 13 | `/app/clients/[clientId]/models/new` | New model config | Owner, Analyst | Yes | Configure + submit training job |
| 14 | `/app/clients/[clientId]/models/[jobId]` | Model detail | All | Yes | Live progress, diagnostics, results |
| 15 | `/app/clients/[clientId]/attribution` | Channel attribution | All | Yes | Contribution %, ROAS, response curves |
| 16 | `/app/clients/[clientId]/optimizer` | Budget optimizer | Owner, Analyst | Yes | Constraints → run → allocation |
| 17 | `/app/clients/[clientId]/optimizer/[scenarioId]` | Scenario detail | Owner, Analyst | Yes | Saved scenario view/compare |
| 18 | `/app/clients/[clientId]/insights` | AI insights | All | Yes | Insight cards + report list |
| 19 | `/app/clients/[clientId]/insights/[reportId]` | Report detail | All | Yes | Review narrative, export PDF, share |
| 20 | `/share/[token]` | Client report view | Client (external) | No (token) | Read-only report rendering |
| 21 | `/app/settings/team` | Team management | Owner | Yes | Invite / role / remove members |
| 22 | `/app/settings/connectors` | Connector settings | Owner | Yes | Store org-level API tokens, default accounts |
| 23 | `/app/settings/billing` | Billing & usage | Owner | Yes | Plan, quota meter, invoices (V2 Stripe — show placeholder) |
| 24 | `/app/settings/profile` | Profile | All | Yes | Name, email, password, LLM provider preference |

**Page count**: 24 pages/screens (MVP). Modals/drawers (add-member, delete-confirm, share-report, scenario-save) are shared components, not pages.

---

## 4. Global Navigation Structure

### 4.1 App shell layout (desktop ≥ 1024px)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Top bar: [☰ collapse]  Client context switcher [▾]   ...  🔔   👤        │
├──────────────┬──────────────────────────────────────────────────────────┤
│ Sidebar      │                                                          │
│              │                     PAGE CONTENT                        │
│ ┌──────────┐ │                                                          │
│ │ Dashboard │ │  (Scrollable; max-width 1280px; centered)              │
│ │ Clients   │ │                                                          │
│ │  ├ Acme    │ │                                                          │
│ │  ├ Nimbus  │ │                                                          │
│ │  └ + Add   │ │                                                          │
│ │            │ │                                                          │
│ │ Settings   │ │                                                          │
│ │  ├ Team    │ │                                                          │
│ │  ├ Billing │ │                                                          │
│ │  └ Profile │ │                                                          │
│ │            │ │                                                          │
│ │ Usage card │ │                                                          │
│ │ [─── 62%]  │ │                                                          │
└──────────────┴──────────────────────────────────────────────────────────┘
```

**Sidebar (primary navigation)** — persistent, collapsible to 64px icon rail:

- **Dashboard** → `/app/dashboard`
- **Clients** (expandable group):
  - Each client (icon + name) → that client's `/overview`
  - "+ Add client" → `/app/clients/new`
- **Settings** (group, owner-only for Team/Billing; Profile for all):
  - Team → `/app/settings/team` *(Owner only)*
  - Billing & Usage → `/app/settings/billing` *(Owner only)*
  - Profile → `/app/settings/profile`
- **Usage meter** card (fixed at bottom): plan name, "X / Y model trains this month", progress bar. Links to Billing. Visible to Owner only; Analysts/Viewers see a read-only count.

**Client-scoped sub-navigation** — when a client is selected (or when on a client route), a horizontal tab bar appears directly under the top bar (or as a second sidebar level on desktop):

```
Client: Acme Growth  ▾ (change client)
[ Overview ] [ Data Sources ] [ Models ] [ Attribution ] [ Budget Optimizer ] [ Insights & Reports ]
```

**Top bar (context bar)**:
- Left: workspace name ("Acme Agency"), mobile hamburger.
- Center-left: **Client context switcher** — a select/dropdown listing all clients the user can access, with an "Add client" item. Selecting a client navigates to `/app/clients/[id]/overview`. On non-client pages (Dashboard, Settings) the switcher is hidden or disabled.
- Right: **LLM status pill** (Ollama connected / degraded / fallback templates active — important because AI insights degrade gracefully), notification bell (model jobs, sync failures, invitations), user menu (Profile, Billing if owner, Sign out).

### 4.2 Mobile navigation (< 1024px)

- Top bar shows: hamburger (opens a slide-in drawer with full sidebar), client context switcher, notification bell, avatar.
- Slide-in drawer: same items as sidebar; tap to navigate; auto-closes on navigation; backdrop to dismiss.
- Client-scoped tabs render as a horizontally scrollable pill bar under the top bar (no wrap).
- Primary CTAs ("Train model", "Run optimizer") render as a sticky bottom action bar on the relevant pages so the key action is thumb-reachable.
- Tables collapse to cards: each row becomes a card with the primary identifier, 2–3 key metrics, and a chevron to the detail page.
- Share links, PDF exports, and toasts are standard on mobile; avoid hover-only interactions (use tap targets ≥ 44px).

### 4.3 Navigation rules

1. Every authenticated page beyond `/onboarding` requires an active session; unauthenticated users redirect to `/login?next=<returnUrl>`.
2. Client pages require the user to have access to that client (membership via org + RLS). No access → 404 (not 403, to avoid leaking client existence).
3. `/onboarding` is shown to the org owner until onboarding is complete (`org.onboarding_complete = true`); dismissible via "Skip for now" which routes to `/app/dashboard` and shows a persistent "Finish setup" banner.
4. Breadcrumbs on client pages: `Clients / <Client name> / <Section>`.
5. Deep links are always valid (refresh-safe) because all state is server-backed, not in client memory.

---

## 5. URL Routing Map & Role Access

| Route | Owner | Analyst | Viewer | Notes |
|-------|:-----:|:-------:|:------:|-------|
| `/onboarding` | ✅ | — | — | Redirect others to dashboard |
| `/app/dashboard` | ✅ | ✅ | ✅ | Viewer: read-only widgets |
| `/app/clients` | ✅ | ✅ | read-only | Viewer sees list, cannot add |
| `/app/clients/new` | ✅ | ✅ | — | Viewer → 404 |
| `/app/clients/[id]/overview` | ✅ | ✅ | ✅ | |
| `/app/clients/[id]/data-sources*` | ✅ | ✅ | — | Viewer → 404 |
| `/app/clients/[id]/models` | ✅ | ✅ | ✅ | Viewer read-only |
| `/app/clients/[id]/models/new` | ✅ | ✅ | — | Viewer → 404 |
| `/app/clients/[id]/models/[jobId]` | ✅ | ✅ | ✅ | |
| `/app/clients/[id]/attribution` | ✅ | ✅ | ✅ | |
| `/app/clients/[id]/optimizer*` | ✅ | ✅ | — | Viewer → 404 |
| `/app/clients/[id]/insights*` | ✅ | ✅ | ✅ | Viewer read-only |
| `/share/[token]` | ✅ (no auth) | ✅ (no auth) | ✅ (no auth) | Token-gated; independent of role |
| `/app/settings/team` | ✅ | — | — | 404 for others |
| `/app/settings/billing` | ✅ | — | — | 404 for others |
| `/app/settings/connectors` | ✅ | ✅ | — | 404 for Viewer |
| `/app/settings/profile` | ✅ | ✅ | ✅ | |

---

## 6. Global UX Patterns

Shared state/feedback conventions used on every page (build these as reusable shadcn/ui primitives):

### 6.1 Loading states

| Component | Pattern |
|-----------|---------|
| Full-page fetch | Skeleton blocks matching final layout (shimmer); never a blank page or full-screen spinner for data grids |
| Inline action (button) | Button becomes disabled + inline spinner; primary label text retained ("Training…") |
| Async job page | Dedicated status panel (see 9.3 / Section 11); no skeleton for a long-running job — show real status |
| Initial app load | App-level splash with logo + "Loading workspace…" (max ~2s) |

### 6.2 Empty states

Every empty state must include: an illustration/icon, a plain-language explanation ("No data connected yet"), **one** primary CTA, and (where relevant) a link to a help article or template download. Inventory:

| Page/Region | Empty state message | Primary CTA |
|-------------|--------------------|-------------|
| Dashboard, no clients | "Welcome! Add your first client to get started." | "+ Add client" |
| Client overview, no model | "Train your first model to see channel performance." | "Train model" |
| Data sources, none | "No data sources connected. MMM needs spend & revenue data." | "Connect data source" |
| Model history, none | "No models yet. Your training history will appear here." | "Train your first model" |
| Attribution, no completed model | "Attribution appears after a model finishes training." | "View models" |
| Optimizer, no completed model | "Run or complete a model before optimizing budgets." | "View models" |
| Insights, no completed model | "Insights are generated from a trained model." | "Train model" |
| Reports, none | "Generate your first executive report." | "Generate report" |
| Team, no members besides owner | "Invite teammates to collaborate." | "Invite member" |

### 6.3 Error states

- **Page-level fetch failure**: centered error card with icon, message, "Retry" button, and "Reload page" fallback.
- **Form field errors**: inline, below the field, with red border; validated on blur and on submit; first error scrolls into view.
- **Mutation failure**: destructive/error toast (top-right, auto-dismiss 5s) with the human-readable message from the API (never raw stack).
- **API 4xx (RLS/403)**: page renders 404 as specified; if the backend returns a distinct "no permission", show "You don't have access to this page" with a link to Dashboard.
- **Offline / network**: a dismissible global banner "Connection lost — reconnecting…" with automatic retry; cached route shells still render.

### 6.4 Confirmation dialogs (destructive only)

- **Delete client / delete data source / delete model artifact / remove member**: modal with item name, warning of consequence ("This permanently deletes Acme Growth and all its models, data sources, and reports"), type-to-confirm the client name for delete-client (hard-delete is irreversible), Cancel / red Delete button. Never use "are you sure?" for non-destructive actions (re-trains, scenario re-runs get a lightweight confirm only).
- All destructive actions are Owner-only except data-source deletion (Owner + Analyst).

### 6.5 Toasts & notifications

- Success: green toast (e.g., "Training job queued", "Report generated", "Connection verified").
- Warning: amber toast (e.g., "LLM unavailable — using template report", "Some rows skipped in CSV (12 invalid dates)").
- Error: red toast.
- In-app notification bell entries: job queued/completed/failed, data sync failure, invite received, quota at 80% and 100%.

### 6.6 Number & format conventions

- Currency in the client's configured currency; default USD; format `$12,400` and `$1.24M`.
- Percentages: contribution share with 1 decimal; ROAS with 2 decimals (`ROAS 3.42`).
- Dates: `Aug 12, 2026`; relative where useful ("trained 2h ago").
- Confidence intervals: shown as `3.4 – 4.1` or error bars on charts; always labeled "90% credible interval".
- Colors: use the shadcn/ui theme tokens; semantic green/amber/red for healthy/warning/failed states; channel colors are a stable palette assigned per channel name (Meta=#2563EB, Google=#EA580C, TikTok=#0F172A, etc.) — persist the mapping per client so charts are consistent.

---

## 7. Authentication Flows (Supabase Auth)

### 7.1 Sign in (`/login`)

**What the user sees**: centered card, left-aligned brand block ("MMM Platform — AI-powered Marketing Mix Modeling for agencies"). Card fields:

- Email (with browser autofill)
- Password (show/hide toggle)
- "Sign in" (primary, full-width)
- Divider: "or"
- "Continue with Google" (optional, secondary)
- Links: "Forgot password?" → `/forgot-password`; "New to MMM? Create an account" → `/signup`

**Flow**:
1. Submit → POST `/auth/login` (Supabase `signInWithPassword`).
2. Success → check `org.onboarding_complete`:
   - Not complete → `/onboarding`
   - Complete → `/app/dashboard` (or `next` param if provided)
3. Failure → inline error above the submit button:
   - Invalid credentials: "Incorrect email or password."
   - Not confirmed: "Please verify your email first. Resend verification" (link).
   - Account suspended: "This account has been suspended. Contact support."
4. Rate limit (Supabase default): "Too many attempts. Try again in X seconds."

**Empty state**: none (form always present). **Error/loading**: as above.

### 7.2 Create account (`/signup`)

**Fields**:
1. Step 1 — Account: full name, work email, password (min 8 chars, show strength meter), "Continue".
2. Step 2 — Organization: agency name, team size select (1–5 / 6–20 / 21–50 / 50+), "Create workspace".

**Flow**:
1. Submit → Supabase `signUp`; user record created with `role=agency_owner`, a new `Organization` row (`name = agency name`), and a membership row.
2. Email confirmation: if `confirm email` is enabled, show a "Check your inbox" screen with a resend link; the onboarding wizard is deferred until confirmed.
3. Confirmed → `/onboarding` (wizard, Section 8).
4. Existing-email error: "An account with this email already exists. Sign in instead."
5. Password too weak: inline validation.

**Roles of the creator**: the signup user is always **Agency Owner** of the new org.

### 7.3 Forgot / reset password

1. `/forgot-password`: email field → submit → "If an account exists for this email, a reset link has been sent." (Never reveal whether an account exists.)
2. Reset link → Supabase-hosted reset page → new password → signs in → `/app/dashboard`.
3. Expired link → error screen with "Request a new link".

### 7.4 Session handling

- Session lives in Supabase Auth JWT; refreshed automatically (NextAuth.js integration).
- All `/app/*` routes and API calls enforce the session; 401 → redirect `/login?next=`.
- Sign out (user menu): confirm-free, clears session, redirects to `/` landing.

### 7.5 First-run redirect logic (post-auth)

```
/login or /signup success
  └─ org.onboarding_complete == false  → /onboarding
  └─ org.onboarding_complete == true   → /app/dashboard
```

---

## 8. Agency Onboarding Flow (signup → first client → first model)

**Goal**: first trained model in **under 15 minutes**, with zero support calls. The wizard is a single full-screen flow with a progress stepper (4 steps) and "Save & exit anytime" persistence — every step writes to the server, so leaving and returning resumes exactly where the user stopped.

```
/signup → /onboarding
  Step 1  Organization & defaults
  Step 2  Add your first client
  Step 3  Connect data source (CSV recommended for first run)
  Step 4  Train first model (recommended defaults)
       ↓
  Success screen → /app/clients/[clientId]/models/[jobId]
```

### Step 1 — Organization setup (pre-filled from signup)
- Agency name (pre-filled, editable), industry segment select (ecommerce/DTC, B2B SaaS, finance, travel, other), default currency select.
- LLM provider choice (advanced, collapsed): "AI insights provider" = "Ollama (self-hosted, default)" with a note that Claude/OpenAI can be configured in Settings; admin may set `LLM_PROVIDER` env and the UI reflects availability.
- Buttons: **"Continue"** → Step 2. **"Skip"** not offered here (no data yet).

### Step 2 — Add first client
- Card: client name, domain (optional), currency (defaults to org), industry.
- **"Save & continue"** → creates `Client` row → Step 3.
- Secondary link: "Add another client later" (writes nothing, proceeds to Step 3).

### Step 3 — Connect data source
Two-column layout: left = recommended path (CSV), right = "Connect a platform API" list (Meta, Google Ads, GA4, TikTok, Shopify) with availability badges.

- **CSV path**: download a **template CSV** (downloads `mmm_template.csv` with the canonical schema header + 3 example rows), drag-and-drop dropzone (accepts `.csv`, max 50 MB), or paste-from-clipboard textarea. On upload, a **preview table** (first 10 rows + inferred column mapping) is shown with fixable mapping dropdowns (date/channel/spend/impressions/clicks/conversions/revenue). "Save & continue" validates and stores the DataSource.
  - Upload warnings (non-blocking, shown as amber toast): invalid dates skipped, spend < 0 clamped to 0 with warning, unmapped optional columns left null.
  - Upload errors (blocking): no date or spend column, empty file, all rows invalid.
- **Platform path**: opens the connect wizard (Section 9.1) inline; after verification returns to onboarding Step 3 marked complete.
- Buttons: **"Save & continue"**, "Back".

### Step 4 — Train first model (recommended defaults)
- Model name (pre-filled "First model — <client>"), date range auto-set to the data coverage (editable).
- Advanced settings collapsed behind "Advanced model settings (optional)": priors (default: industry priors for ecommerce), adstock (geometric), saturation (Hill), sampler (NUTS), chains=4, draws=500. Defaults are the spec's recommended values — the user should never need to touch them for the first run.
- Submit button: **"Train my first model"**.
- On submit → job `queued` → redirect to the **Model detail** page with live progress (Section 9.3) and a success panel when done.

### Step 5 — Success screen
- Confetti-free, calm success state: check icon, "You trained your first MMM in ~X min", bullet highlights (channels measured, top channel, R²), buttons:
  - **"View channel attribution"** → `/attribution`
  - **"Run budget optimizer"** → `/optimizer`
  - **"Generate executive report"** → `/insights/new`
  - "Back to dashboard" (ghost) → `/app/dashboard`
- Marks `org.onboarding_complete = true`.

**Onboarding errors**: any step API failure → error toast + stays on step. **Loading**: step transitions show a top progress bar (linear, 25/50/75/100%) plus per-step inline spinners on Save.

**Edge cases**:
- User abandons after Step 2 → banner on Dashboard: "Finish setup — connect data and train a first model." → `/onboarding` resumes at Step 3.
- No data at all when user wants to proceed → block Step 4 with tooltip "Connect data first".
- Onboarding steps persisted server-side so a second device resumes correctly.

---

## 9. Core Flows

### 9.1 Connect Data Source (choose platform → auth → configure → verify)

**Entry points**: Data Sources page "Connect data source", onboarding Step 3, empty-state CTA on client overview. Route: `/app/clients/[clientId]/data-sources/connect`.

**Stepper**: 4 steps — (1) Choose platform, (2) Authenticate, (3) Configure, (4) Verify.

#### Step 1 — Choose platform
Grid of connector cards with logo, name, priority badge:

| Card | Type | Priority |
|------|------|----------|
| CSV upload | File/paste | P0 (universal fallback) |
| Shopify | API (Admin, X-Shopify-Access-Token) | P0 (revenue source) |
| Meta Ads | Marketing API v19+ (OAuth2) | P1 |
| Google Ads | OAuth2 + developer token | P1 |
| GA4 | Data API v1beta (service account) | P1 |
| TikTok | Marketing API v1.3 (access token) | P2 |
| LinkedIn / Snap / Pinterest | OAuth2 | P2 (disabled w/ "Coming soon" in MVP unless implemented) |

- Cards show "Configured" badge if an org-level credential already exists.
- Disabled cards: greyscale + tooltip "Not yet available in this plan" (Pro tier gates API connectors; CSV available on all plans).

#### Step 2 — Authenticate
- **OAuth platforms (Meta/Google/TikTok/LinkedIn)**: button "Connect <Platform>" → opens provider OAuth popup → on success, the platform account list appears; user selects which account to connect to this client. Cancel/deny → inline error "Connection cancelled. Try again."
- **Shopify**: enter store subdomain (e.g., `my-store.myshopify.com`) + Admin API access token (pasted into a masked field with a "Where do I find this?" help link).
- **GA4**: select a Firebase/GA property from an org-level service-account list (configured in Settings → Connectors) — if none, prompt to configure a service account first with a link to `/app/settings/connectors`.
- **CSV**: not shown here; CSV is its own path (Section 8, Step 3).

Credentials are stored encrypted in `data_sources` (per tenant) — the UI never displays a stored token; only shows "Connected · <account email> · last sync <date>".

#### Step 3 — Configure
Per-connector mapping form (pre-filled with sensible defaults):

- Date range: "Sync from" date picker + "Daily" cadence; **scheduled sync** toggle (default ON, weekly) → maps to Celery scheduled sync job.
- Channel mapping: which platform fields map to the canonical `channel` label (e.g., Meta campaign objective → channel bucket). Show an auto-generated mapping with edit ability.
- Currency + timezone for the client.
- Advanced: row limits, API field options (collapsed).

#### Step 4 — Verify
- Runs a live API test (`fetch_spend(start, end)` against last 30 days). Shows:
  - ✅ Connection OK — "Fetched 42,180 rows · 9 channels · Aug 1 – Aug 30, 2026" + mini sparkline of spend/revenue.
  - ⚠️ Partial — "Connected but some fields missing (no revenue). Revenue is required for a useful model." — allow "Save anyway" or "Fix mapping".
  - ❌ Failed — reason ("Invalid token", "API rate-limited — retrying", "Account has no campaigns in range") with **"Retry"** and **"Go back to config"**.
- **"Save connection"** → creates/updates the `DataSource` row, marks it active, redirects to `/data-sources` with a green toast "Shopify connected. First sync scheduled for Sunday."

**Empty state** (Step 1 with zero connectors): a single prominent CSV card + "recommended for fastest start".

**Edge cases**: rate limits (429) auto-retry with exponential backoff — show "Retrying (attempt 2/3)…"; duplicate connector for same platform+account → inline warning "This account is already connected to this client — connect anyway?"; deleting an account in the provider → next verify shows "Connection expired — re-authenticate" with a one-click re-auth button.

### 9.2 Train Model (configure → submit → wait → diagnostics → done)

**Entry points**: Models page "Train model", client overview "Train model", onboarding Step 4. Route: `/app/clients/[clientId]/models/new`.

#### Phase A — Configure (form page)
Left column = form; right column = live "Data readiness" panel (from connected DataSources):

1. **Model name** (text, default "Model <date>").
2. **Date range** (start/end pickers; default = full data coverage; warn if < 8 weeks of data: "8+ weeks of data improves model reliability").
3. **Data source selection** — checkboxes of connected sources; auto-includes revenue source (Shopify/GA4 revenue or CSV revenue column). At least one source with revenue required → otherwise block submit with CTA "Connect data source".
4. **Controls** — optional panel per spec (advanced, collapsed by default):
   - Priors: select preset (ecommerce default, B2B default, custom). 
   - Adstock: geometric / delayed / Weibull.
   - Saturation: Hill / Michaelis-Menten.
   - Sampler: NUTS (default) / NumPyro / BlackJax / Nutpie.
   - Chains (2/4/8, default 4), Draws (250/500/1000, default 500).
5. **Engine badge**: "PyMC-Marketing (Bayesian)".
6. **Cost & quota callout**: "This run uses 1 of your 20 monthly model trains." (Owner sees quota; Analyst sees a read-only line).
7. Primary CTA: **"Start training"**; secondary: "Save as draft".

**Validation**: date range valid, data source with revenue present, model name non-empty. Inline errors; submit disabled until valid.

#### Phase B — Submit & wait (Model detail page, live)
On submit → POST `/models/train` → job row created (`status=queued`) → redirect to `/app/clients/[clientId]/models/[jobId]`.

Page renders a **job status panel** with:

| State | Panel content |
|-------|---------------|
| queued | "In queue — position #3 of 4" + estimated wait ("~2 min"), progress bar 5% |
| running | Live progress bar with sub-phase label: *loading data* (15%) → *sampling (MCMC)* (20–80%, draws/chains counter "1,437 / 2,000 draws") → *computing diagnostics* (85%) → *saving artifact* (95%) → *complete* (100%) |
| completed | Success banner, summary cards, "Continue" actions |
| failed | Error card with reason + guidance + "Retrain with same settings" |

Auto-refresh: SSE stream (or 2s polling fallback) from FastAPI; the page never requires manual refresh. The page is safe to navigate away from; a notification fires on completion.

**Progress fetch**: job `progress` field (0–100) + `stage` enum (`loading`, `sampling`, `diagnostics`, `saving`, `done`).

#### Phase C — Diagnostics (post-completion section on same page)
Once completed, the page expands a **Diagnostics panel**:

- **Convergence**: R-hat table per parameter. All ≤ 1.01 → green "Converged". Any > 1.1 → amber "Some chains did not converge — consider more draws or longer burn-in." plus a "Retrain with more draws" quick action.
- **Fit quality**: R² (target > 0.7), MAPE, posterior predictive check plot (actual vs predicted revenue over time, shaded credible band).
- **Export of the trace**: "Download trace (NetCDF)" → S3/R2 artifact keyed `tenant/client/model_job/`. 

#### Phase D — Done
Bottom actions: **"View channel attribution"**, **"Run budget optimizer"**, **"Generate report"**, "Back to model history". Model appears in history with `completed` badge.

**Empty state** (Phase A with no data): whole right panel is the empty state from Section 6.2. **Error**: any config fetch failure → retry card. **Loading**: skeletons for both columns.

### 9.3 Run Budget Optimizer (select client → set constraints → run → view allocation)

**Entry points**: Budget Optimizer tab, client overview "Optimize budget", model detail "Run budget optimizer". Route: `/app/clients/[clientId]/optimizer`.

Requires a **completed model** (nearest completed job is used; a dropdown lets the user pick which model version to optimize against). No completed model → empty state with "Train model" CTA.

#### Layout
- Left: **constraints panel** (sticky form).
- Right: **results panel** — empty until first run ("Set constraints and run to see the recommended allocation").

#### Constraint inputs
1. **Total budget** (currency input; defaults to last period's total spend).
2. **Per-channel constraints** table, one row per modeled channel:
   - Current allocation (read-only, from model)
   - Min % / Max % sliders or numeric inputs (0–100)
   - Absolute floor / cap (currency, optional)
   - Lock toggle (🔒 fixes a channel at its current spend)
3. **Objective**: "Maximize revenue" (default) / "Maximize ROAS".
4. **Optimizer**: "Auto (recommended)" → scipy optimizer with PyMC `allocate_budget` fallback; advanced toggle exposes method.
5. CTA: **"Run optimization"** (primary). Secondary: "Reset to current allocation".

**Example** (shows on the page as a hint box):
> Total budget $100,000. Constraints: Meta 20–60% (floor $15,000), Google 10–40%, TikTok 0–25%, locked: Shopify organic $5,000. Optimizer returns: Meta $44,000 (44%), Google $31,000 (31%), TikTok $15,000 (15%), Organic $5,000 (5%), unallocated $5,000.

#### Run & results
- On run: button → spinner "Optimizing…"; typical < 5s; then results panel populates:
  - **Allocation bar**: horizontal stacked bar, current vs optimized side-by-side, per-channel share %.
  - **Expected revenue**: big number + delta vs current ("$1.24M expected, +8.4% vs current") with credible interval.
  - **Table**: channel / current spend / optimized spend / Δ / expected revenue / Δ ROAS.
  - **Warning list** (amber): e.g., "TikTok exceeds your max constraint — clamped to 25%", "Constraints leave $5,000 unallocated".
- Actions: **"Save scenario"** (name → `/optimizer/[scenarioId]`, stored for comparison), **"Download CSV"**, **"Add to report"** (pins allocation table to the next generated report).

**Scenario detail page** (`/optimizer/[scenarioId]`): read-only snapshot + compare against current allocation; "Re-run with these constraints" loads them back into the editor.

**Errors**: no completed model → empty state; optimizer fails (e.g., infeasible constraints) → error card "Constraints can't be satisfied — lower minimums or raise total budget" with specifics; loading = skeleton on results panel.

### 9.4 Generate Insights Report (auto-generate → review → export PDF → share)

**Entry points**: Insights tab "Generate report", model detail "Generate report", optimizer "Add to report". Route: `/app/clients/[clientId]/insights` (list) and `/app/clients/[clientId]/insights/[reportId]` (detail).

#### Generation trigger
- Primary flow: user clicks **"Generate report"** → modal: report title (default "Executive Report — <Client> — <Month>"), model version select, optional "Include budget scenario" select (pins a saved scenario), toggle "Include technical diagnostics" (default off for client-facing), CTA **"Generate"**.
- Generation is async (LLM narrative + chart assembly). Job states: `generating` (progress spinner, ~10–30s) → `ready` → redirect to report detail.
- **LLM fallback**: if the LLM provider is unreachable (Ollama down), the UI shows amber banner "AI narrative unavailable — generating template report" and uses the template fallback (`report.py _fallback_report`). The report still completes.

#### Report detail page (review)
Report sections (per spec F7):

| # | Section | Content | Source |
|---|---------|---------|--------|
| 1 | Overview / executive summary | 3–5 sentence NL narrative: total spend, revenue, top channel, headline recommendation | LLM summary or template |
| 2 | Channel analysis | Per-channel table + contribution % / ROAS / spend / revenue; contribution pie/bar; response curves | Model output |
| 3 | Budget recommendations | Reallocation table with expected revenue impact (or pinned scenario) | Optimizer / LLM |
| 4 | Risks & caveats | Confidence intervals, model R²/MAPE, "MMM measures correlation, not causation", data caveats | Model diagnostics + template |

- All AI narrative must cite numbers from model output; a **citation strip** shows "All figures from model #123, trained Aug 1, 2026."
- Review affordances: inline editing is **not** in MVP (edit in V2); the reviewer can regenerate ("Regenerate narrative") and can toggle sections in/out before export.
- **Export PDF**: server-side PDF render (headless) → downloads `<client>-mmm-report.pdf`. Loading: button spinner "Rendering PDF…". Error: toast "PDF generation failed — retry or contact support."
- **Share**: "Share with client" button → creates a `/share/[token]` link → modal with copyable URL, expiry select (30 days / 90 days / never, default 90), "Revoke" management. Copied → green toast "Link copied". The modal lists active links with revoke buttons.

#### Client shared report view (`/share/[token]`)
- No auth required; branded with agency name (white-label in V2 — show agency logo/name now).
- Renders the report read-only: sections, charts, PDF download button.
- Banners: "Shared report · Prepared by <Agency>" and an expiry warning if within 7 days.
- Invalid/expired token → friendly 404 "This report link is invalid or has expired — contact <Agency> to request a new one."
- No sidebar, no app navigation, no "edit" affordances — a strict read-only surface.

#### Report list (`/insights`)
Cards/table: title, model version, generated date, status (generating/ready), PDF badge, share status ("Shared · link expires Sep 12"), actions (Open, Download PDF, Share, Delete). Empty state per Section 6.2.

**Errors**: generation fails (LLM error + template also fails) → red toast "Report generation failed. Please retry." with the job marked `failed` in the list and a Retry button.

---

## 10. Client Management Flow

### 10.1 Add client
Paths: Clients page "+ Add client", sidebar "+ Add client", onboarding Step 2, dashboard empty state.
- Form page (`/app/clients/new`): name (required), domain (optional), currency (select, defaults org), industry (optional), "Create client" button.
- Submit → `POST /clients` → green toast "Client created" → redirect `/app/clients/[id]/overview` → empty state guides "Connect data source".
- Validation: duplicate name within org → "A client with this name already exists."
- Role gate: Owner + Analyst (Analyst allowed to add per spec).

### 10.2 Switch context
- Primary control: **client context switcher** in the top bar (Section 4.1) — dropdown with all accessible clients, searchable if > 8, current client check-marked.
- Secondary: sidebar client list click → switches context and lands on that client's overview.
- Context is derived from the URL (`/app/clients/[clientId]/...`), so there is no hidden "active client" state — deep links and multi-tab are always correct. The switcher is a convenience that navigates.
- On non-client pages (Dashboard, Settings), no client context is required.

### 10.3 Client detail (`/app/clients/[clientId]/overview`)

What the user sees:
- Header: client name, currency, domain, "Managed by <agency>" breadcrumb, actions (**Edit** → opens edit modal, **Delete** — Owner only).
- KPI row (from the **latest completed model**): Total Spend, Total Revenue, ROAS, Top Channel (+ share %). If no model: these cards show "—" with tooltip "Train a model to see KPIs".
- "Latest model" card: status badge, R², MAPE, trained date, actions (View diagnostics, Retrain).
- Channel performance cards (mini bars for contribution share).
- Quick actions row: Connect data source / Train model / Run optimizer / Generate report (role-gated).
- Recent jobs feed (last 5 model jobs + sync jobs) with status chips.

Empty / loading / error states: per Section 6; the whole page skeletons on fetch, empty states per widget when no model exists.

### 10.4 Edit client
Modal (name, domain, currency, industry) → save → toast "Client updated". Not a separate page.

### 10.5 Delete client
1. Only Owner. Gear/overflow → "Delete client".
2. Confirm modal: item name, red warning, **type the client name** to confirm, red "Delete permanently".
3. On confirm → `DELETE /clients/[id]` (cascades: data sources, model jobs + artifacts in S3, reports, share tokens) → toast "Client deleted" → redirect `/app/clients`.
4. If the client is in the middle of a training/sync job: block with message "A training job is running for this client. Cancel it or wait for completion." Cancel-job action offered inline.
5. Failure (RLS/backend) → red toast, no partial deletion.

---

## 11. Model Training Lifecycle (state machine)

Job status enum (single source of truth for all UI):

```
queued → running → completed
   │        │
   │        └→ failed
   └→ cancelled (owner/analyst cancel while queued or running)
```

| Status | UI badge | Transition triggers | User actions |
|--------|----------|--------------------|--------------|
| `draft` | Grey "Draft" | Config saved but not submitted (optional) | Edit, Submit |
| `queued` | Blue "Queued" | User hits Start training; Celery worker picks up | Cancel (→ `cancelled`); view queue position |
| `running` | Indigo "Running" (pulsing dot) | Worker begins; sub-stages `loading`→`sampling`→`diagnostics`→`saving` | View live progress; Cancel (graceful — safe only between MCMC chains); "Notify me" implicitly on |
| `completed` | Green "Completed" | `saving` finishes; artifact written to S3/R2 | View diagnostics, attribution, optimizer, report; **Retrain** |
| `failed` | Red "Failed" | Engine error, data error, OOM, RLS/auth on artifact write | Retry with same settings; edit config; view error detail; contact support |
| `cancelled` | Grey "Cancelled" | User cancels | Retrain |

### 11.1 Failure reasons surfaced in UI (mapped to guidance)

| Failure | UI message | Suggested action button |
|---------|-----------|------------------------|
| Insufficient data (< 8 weeks) | "Not enough data — need at least 8 weeks." | "Edit date range" |
| Missing revenue column | "No revenue source found." | "Connect revenue source" |
| Sampler divergences / non-convergence | "Sampler reported divergences — results may be unreliable." | "Retrain with more draws" |
| OOM / worker crash | "Training ran out of memory." | "Reduce draws/chains" + "Retrain" |
| Unknown / generic | Error id + "Contact support" | "Download error log" |

### 11.2 Retrain
- Anywhere a completed/failed model appears: **"Retrain"** action → opens the config page **pre-filled with that job's config** → "Start training" creates a **new** job (never mutates the historical job). Old jobs remain in history as immutable records.
- Quota counting: every submitted job consumes 1 of the org's monthly model trains (except drafts/cancelled jobs are not counted; cancelled-after-start counts). Show this in the submit confirmation when applicable.

### 11.3 Model history page (`/app/clients/[clientId]/models`)

- Table: name, status badge, version (#v2), date range, R², MAPE, trained at, actions (Open, Retrain, ⋮ → Copy config / Delete artifact). Sortable by date; filter chips by status (All / Running / Completed / Failed).
- Running jobs show inline progress in the row (mini progress bar) — click navigates to the live detail page.
- Loading: skeleton table. Empty: Section 6.2. Error: retry card.
- Concurrent jobs: multiple runs per client allowed (Celery); quota enforced; "2 jobs running" chip shown.

---

## 12. Page-by-Page Detail (beyond what flows cover)

### 12.1 Landing page (`/`)
- Hero: tagline + sub-headline + primary CTA "Start free trial" → `/signup`; secondary "See how it works" (scroll to 3-feature section).
- Sections: How it works (Connect → Train → Optimize → Report, 4-step), Features grid (per spec F1–F7), Channel/industry logos, Pricing table (Starter/Pro/Enterprise from spec), CTA band, footer.
- States: static content; no auth; loading = skeleton hero image; error = none (static).

### 12.2 Workspace dashboard (`/app/dashboard`)
What the user sees:
- Greeting + date; "Finish setup" banner if onboarding incomplete (owner only).
- KPI row (org-wide): Total clients, Models trained this month (X/Y), Completed models, Total revenue measured across latest models.
- **Clients overview** list/table: client, status (Data connected / Needs data / Model ready), latest model R² + trained date, top channel, quick actions (Train, Optimize, Report).
- **Recent activity** feed: model jobs + data sync jobs + invites (icon, message, relative time).
- **Alerts** (amber cards): "3 data syncs failed — re-authenticate", "Meta API token expires in 5 days".
- Role gating: Viewer sees the same read-only (no quick actions); owner-only elements hidden.
Empty state: Section 6.2 (no clients). Loading: skeleton grid. Error: retry card.

### 12.3 Clients list (`/app/clients`)
- Search field (client name), count "12 clients", table or card grid: name, industry, currency, data-source count, latest model status, actions (Open, ⋮ menu → Edit/Delete).
- "+ Add client" primary CTA (owner/analyst).
- Empty/loading/error per Section 6.

### 12.4 Data sources page (`/app/clients/[clientId]/data-sources`)
- Cards per connector: logo, status badge (Active / Needs re-auth / Error / Syncing), account label, last sync time, rows fetched, schedule ("Weekly · Sundays 2 AM"), actions (Re-auth, Test connection, Edit mapping, Delete).
- "Connect data source" primary CTA → wizard.
- Sync failures show the amber "Fix now" → re-auth. Active sync shows pulsing "Syncing…" until the Celery job finishes (SSE update).
- Delete connector → confirm modal (affects future models only; historical model artifacts retained).

### 12.5 AI insights page (`/app/clients/[clientId]/insights`)
- **Insight cards** (auto-generated from latest model): each is one of the 5 insight types (channel_performance, budget_recommendation, anomaly, benchmark, summary). Card: icon, type label, NL text citing numbers, "Add to report" toggle, regenerate icon.
- **Scenario Q&A** composer (F5): input "Ask about your model" with suggested prompts ("What if I shift 20% from TV to Meta?", "Which channel is underfunded?"). Streaming answer (SSE); every answer cites numbers; "Add to report" button.
- **Reports list** (below): recent reports with status.
- Empty (no model): Section 6.2. LLM-down: amber banner + template insights still shown (static template content); Q&A disabled with "AI assistant offline" message.

### 12.6 Team management (`/app/settings/team` — Owner only)
- Member table: avatar, name, email, role select (Owner/Analyst/Viewer), status (Active/Pending/Invite expired), remove button (except self).
- "Invite member" → modal: email(s), role select → sends invite (Supabase Auth invite) → pending row with "Resend" / "Revoke".
- Changing own role: blocked (Owner must always exist). Removing last owner: blocked.
- Empty: "Invite your first teammate" CTA. Errors: invalid email, invite limit.

### 12.7 Billing & usage (`/app/settings/billing` — Owner only)
- Plan card (Starter/Pro/Enterprise per spec pricing), "Manage plan" (Stripe in V2 — MVP shows plan + limits, upgrade as placeholder "Contact sales").
- Usage meters: model trains used this month (X/Y), storage used, API calls, with reset date.
- Current invoice / payment method (V2 placeholder). Quota-at-80% banner here and on dashboard.

### 12.8 Connector settings (`/app/settings/connectors` — Owner + Analyst)
- Org-level credential vault: per-platform list of stored OAuth tokens / service accounts / API tokens (masked), account emails, "Add account" / "Revoke" (revoke = remove stored credential, affects all clients using it).
- Note text: "Credentials are encrypted and never stored in plaintext."

### 12.9 Profile (`/app/settings/profile`)
- Name, email (verified badge), change password (Supabase), LLM provider preference (if org allows override), "Delete my account" (Owner blocked — must transfer or delete org first).

---

## 13. Button Actions & Navigation Paths (master table)

| Control (where) | Action | Navigation / effect |
|-----------------|--------|--------------------|
| "Sign in" (`/login`) | Auth | → `/app/dashboard` or `/onboarding` |
| "Create account" (`/signup`) | Create org+owner | → email confirm → `/onboarding` |
| "Forgot password?" | — | → `/forgot-password` |
| Onboarding "Continue/Save & continue" (steps 1–3) | Persist step | → next step |
| "Train my first model" (onboarding step 4) | Queue job | → `/models/[jobId]` |
| "Skip for now" (onboarding) | Mark dismissed | → `/app/dashboard` |
| Sidebar "Dashboard" | — | → `/app/dashboard` |
| Sidebar client item | Switch context | → `/clients/[id]/overview` |
| Sidebar "+ Add client" | — | → `/clients/new` |
| Client tabs (Overview/Data Sources/Models/Attribution/Optimizer/Insights) | — | → corresponding route |
| "Connect data source" (any) | — | → `/data-sources/connect` |
| "Connect <Platform>" (wizard step 2) | OAuth | provider popup → account select |
| "Save connection" (wizard step 4) | Persist DataSource | → `/data-sources` + toast |
| "Start training" (models/new) | Queue job | → `/models/[jobId]` |
| "Save as draft" (models/new) | Persist draft | stays, toast "Draft saved" |
| "Cancel" (running/queued job) | Cancel job | → `/models` + toast |
| "Retrain" (any model card) | Clone config | → `/models/new` pre-filled |
| "Download trace (NetCDF)" | Export artifact | download from S3/R2 |
| "View channel attribution" | — | → `/attribution` |
| "Run budget optimizer" | — | → `/optimizer` |
| "Run optimization" (optimizer) | Compute allocation | results panel populates |
| "Save scenario" (optimizer) | Persist | → `/optimizer/[scenarioId]` |
| "Download CSV" (optimizer results) | Export | CSV download |
| "Add to report" (optimizer/insight) | Pin content | marks next report includes it, toast |
| "Generate report" (insights) | Queue report | → `/insights/[reportId]` when ready |
| "Regenerate narrative" (report) | Re-roll LLM | narrative swaps, toast |
| "Export PDF" (report/share view) | Render PDF | PDF download |
| "Share with client" (report) | Create share token | modal with link copy |
| "Copy" (share modal) | Clipboard | toast "Link copied" |
| "Revoke" (share modal) | Revoke token | link invalidated, toast |
| "Invite member" (team) | Send invite | pending row in table |
| "Resend"/"Revoke" (invite) | — | invite refresh/revoke |
| "Add account"/"Revoke" (connector settings) | — | credential vault update |
| "Edit"/"Delete" (client header) | — | edit modal / delete confirm |
| Avatar → "Sign out" | Logout | → `/` landing |

---

## 14. Notifications

| Event | Channel | Content example |
|-------|---------|-----------------|
| Model training completed | In-app bell + browser push (opt-in) | "Model #v3 for Acme Growth completed (R² 0.84)" |
| Model training failed | In-app bell + toast on the page | "Training failed: insufficient data. Retrain" |
| Data sync failed | In-app bell + amber banner on Data Sources | "Meta Ads sync failed — re-authenticate" |
| Sync completed with warnings | Toast (quiet) | "Google Ads sync: 3 channels skipped" |
| Team invite received | Email + in-app bell | "You've been invited to Acme Agency as Analyst" |
| Quota at 80% / 100% | In-app bell + banner on dashboard | "You've used 16 of 20 monthly model trains" |
| Share link revoked/expiring | In-app bell | "Client report link expires in 7 days" |
| LLM provider down | Global amber banner on Insights | "AI narrative unavailable — using template reports" |

---

## 15. Appendix — Data Shapes the UI Depends On

### 15.1 Canonical data frame (every connector outputs this)

| column | type | required | example |
|--------|------|----------|---------|
| date | datetime | yes | 2026-07-12 |
| channel | str | yes | meta, google_ads, tiktok, shopify_revenue, organic, tv |
| spend | float | yes (can be 0) | 4520.50 |
| impressions | int | no | 812000 |
| clicks | int | no | 12450 |
| conversions | int | no | 310 |
| revenue | float | yes (at least one source) | 15840.00 |

### 15.2 Job status enum (Section 11)

`draft | queued | running | completed | failed | cancelled`

### 15.3 Model result summary (shown on model card)

`job_id, model_version, status, r2, mape, top_channel, trained_at, artifact_key, config_snapshot`

### 15.4 Report sections (Section 9.4) — must render in both LLM and template mode

`overview | channel_analysis | budget_recommendations | risks`

### 15.5 Share token model

`token (opaque), report_id, agency_name, client_name, expires_at, revoked_at`

---

## 16. Cross-cutting UX guardrails for the build

1. **Every long-running action is async-first**: train, sync, report generation, PDF render all create a job + status chip + notification; no blocking UI.
2. **Everything server-backed**: no active-client state in memory; derive from URL (deep-link safe, multi-tab safe).
3. **Explainability is a feature**: every number on a model page links to the diagnostic that produced it; every AI insight cites the underlying figure.
4. **Graceful degradation**: LLM down → template reports; API rate-limited → retry w/ backoff + visible status; connector revoked → one-click re-auth.
5. **Role-gating everywhere, enforced server-side**; the UI hides/disables what a role cannot do, but 404/403 comes from the API.
6. **Quota transparency**: model-train cost is always visible before a run; usage meter always visible in the sidebar (owner) / dashboard (all).
7. **First-run experience is opinionated**: onboarding and "Start training" use recommended defaults; advanced controls are always collapsed, never the first thing shown.
8. **Destructive = confirm + irreversible language**: type-to-confirm only for client deletion; every delete modal states exactly what is removed.
