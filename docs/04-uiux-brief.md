# MMM Platform — UI/UX Design Brief

| | |
|---|---|
| **Document** | 04-uiux-brief.md |
| **Product** | MMM Platform — AI-powered Marketing Mix Modeling for agencies |
| **Author role** | Senior UI/UX Designer (data-heavy SaaS dashboards) |
| **Canonical source** | `docs/_spec.md` (MMM Platform canonical spec) |
| **Supporting research** | `research/agency-workflow.md`, `research/competitor-landscape.md`, `research/data-connector-spec.md`, `research/ai-insights-layer.md`, `research/mmm-engine-comparison.md` |
| **Frontend stack** | Next.js 15, React 19, Tailwind CSS 3.4, shadcn/ui, Recharts 2.13 (already in `app/package.json`) |
| **Status** | Pre-build reference for implementation agents |

This brief defines the complete visual and interaction language for the MMM Platform web app. It is prescriptive enough for an AI coding agent to build without guessing. Where the spec is silent, this document is authoritative.

---

## 1. Design Style and Principles

### 1.1 Direction

**"Quiet instrumentation"** — the app should read like a financial-grade measurement console, not a marketing site. The data is the hero; chrome is minimized. Think *Linear meets Bloomberg Terminal*, light-first.

Four adjectives from the brief requirements: **clean, data-first, professional, minimal**.

- Light mode is the **default** and only mode in MVP. Dark mode tokens are specified (Section 2.5) but ship after launch.
- Every screen is **utility-first**: no decorative gradients, no illustrations, no brand flourishes. One accent color is reserved for semantic/action use only (Section 2.2).
- **Density is a feature.** Agencies manage 3–50+ clients and hundreds of model runs. Information must be scannable at a glance: ~14px base text, 4px spacing grid, compact tables.

### 1.2 Design Principles

| # | Principle | Meaning in practice |
|---|-----------|---------------------|
| P1 | **Data-first hierarchy** | The single most important number on a screen gets the largest type. Secondary context (delta, tooltip, footnote) is always smaller and muted. |
| P2 | **Trust through transparency** | Bayesian MMM is a black box to clients. Every metric (R², R-hat, MAPE, contribution %) is rendered with its number **and** a plain-language interpretation. Never show a number without framing. |
| P3 | **One client context at a time** | The current client is always visible (Section 7). Every panel, chart, and table is scoped to it and labeled as such. No orphan data. |
| P4 | **Progress is never ambiguous** | Long-running work (model training, data sync) always shows state: `queued → running → succeeded/failed`, with % where known. No infinite spinners on multi-minute jobs. |
| P5 | **Conservative color semantics** | Color means something (success/warning/error/channel identity) or it does not get applied. Never color purely decoratively. |
| P6 | **Consistent chart grammar** | Same channel = same color in **every** chart across the app (Section 6.5). Same axis orientation (time = x) everywhere. |
| P7 | **Fast time-to-insight** | Target: <15 min from CSV upload to first trained model (spec success metric). The UI must make that path 3 clicks: **Connect data → Configure → Train**. |
| P8 | **Editability before export** | AI-generated reports are drafts, not facts. Every generated artifact is editable before it can be exported or shared (Section 10). |

### 1.3 Tone of Voice (microcopy)

- Concise, imperative, no fluff. "Train model", "Connect data", "Run scenario".
- Numbers always accompanied by units and period: `$24.1k`, `3.2x ROAS`, `Q2 2026`.
- Uncertainty is stated honestly: `R² 0.74 — good fit`, `R-hat 1.02 — converged`. Confidence intervals displayed where the engine provides them (spec: "Include confidence intervals where available").
- Errors are instructive, never blame: `"Training failed: data has 0 revenue rows after 2026-03-15."`

---

## 2. Color Palette

All values are hex. Tailwind classes are given for implementation. Light mode is the only shipped theme in MVP.

### 2.1 Core Neutrals

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| `bg-page` | `#F8FAFC` | `slate-50` | App background (outside cards) |
| `bg-surface` | `#FFFFFF` | `white` | Cards, sidebar, topbar, modals |
| `bg-surface-muted` | `#F1F5F9` | `slate-100` | Inset wells, table header, code blocks, hover rows |
| `border-subtle` | `#E2E8F0` | `slate-200` | Default borders, dividers |
| `border-strong` | `#CBD5E1` | `slate-300` | Focused/active borders, selected table rows |
| `text-primary` | `#0F172A` | `slate-900` | Headings, primary values |
| `text-secondary` | `#475569` | `slate-600` | Body copy, labels |
| `text-muted` | `#94A3B8` | `slate-400` | Captions, footnotes, placeholders, disabled |
| `text-inverse` | `#FFFFFF` | `white` | Text on primary/success/warning/error fills |

### 2.2 Brand / Action Colors

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| `primary` | `#4F46E5` | `indigo-600` | Primary buttons, active nav item, links, focus ring |
| `primary-hover` | `#4338CA` | `indigo-700` | Primary button hover |
| `primary-soft` | `#EEF2FF` | `indigo-50` | Active nav background, selected state fills, chip backgrounds |
| `primary-soft-border` | `#C7D2FE` | `indigo-200` | Active nav / selected-state borders |
| `secondary` | `#334155` | `slate-700` | Secondary button text/icons; dark fill variant |
| `accent` | `#0EA5E9` | `sky-500` | AI insight highlight, "recommended" badges, sparkline accent |
| `accent-soft` | `#E0F2FE` | `sky-50` | AI insight panel background |

The **accent** is reserved for AI-derived content (insights, recommendations, anomaly alerts) so users learn "blue = machine-generated, double-check numbers". Primary indigo is reserved for user-initiated action.

### 2.3 Semantic Colors

| Token | Hex | Tailwind | Soft bg | Usage |
|-------|-----|----------|---------|-------|
| `success` | `#16A34A` | `green-600` | `#DCFCE7` / `green-100` | Healthy status, converged, model passed, positive delta |
| `warning` | `#D97706` | `amber-600` | `#FEF3C7` / `amber-100` | Needs attention, R-hat borderline, sync stale, retrain due |
| `error` | `#DC2626` | `red-600` | `#FEE2E2` / `red-100` | Failure, failed job, validation error, negative delta |
| `info` | `#0284C7` | `sky-600` | `#E0F2FE` / `sky-100` | Neutral informative status (e.g., "queued") |

Rules:
- Status **always pairs color with an icon or text label** — never color alone (Accessibility, Section 14).
- Deltas: positive `#16A34A`, negative `#DC2626`, flat `#94A3B8`. Always with an arrow glyph: `↑`, `↓`, `→`.
- Successful diagnostics thresholds: R-hat ≤ 1.01 → green; 1.01–1.10 → amber; > 1.10 → red. R² ≥ 0.70 → green (spec target); 0.50–0.69 → amber; < 0.50 → red.

### 2.4 Chart Categorical Palette (channel identity)

Fixed channel → color mapping, applied consistently app-wide (P6). Supports the canonical schema channels (`research/data-connector-spec.md`) plus a fallback cycle.

| Channel key | Color | Hex | Tailwind |
|-------------|-------|-----|----------|
| `meta` | Meta blue | `#1877F2` | `blue-600` |
| `google_ads` | Google red | `#EA4335` | `red-500` |
| `tiktok` | Ink | `#111111` | `black` |
| `shopify_revenue` | Shopify green | `#96BF48` | `lime-500` |
| `organic` | Organic teal | `#14B8A6` | `teal-500` |
| `tv` | Broadcast violet | `#8B5CF6` | `violet-500` |
| `radio` | Radio amber | `#F59E0B` | `amber-500` |
| fallback (8–N) | Cycle | `#4F46E5 → #0EA5E9 → #10B981 → #F97316 → #EC4899 → #64748B` | — |

These are brand-adjacent but deliberately toned to read on white. The mapping lives in one module (`lib/channel-colors.ts`) — every chart imports from it. Charts **must not** hardcode series colors.

### 2.5 Dark Mode Tokens (post-MVP reference)

| Light token | Dark equivalent |
|-------------|-----------------|
| `bg-page` | `#0F172A` (slate-900) |
| `bg-surface` | `#1E293B` (slate-800) |
| `bg-surface-muted` | `#334155` (slate-700) |
| `border-subtle` | `#334155` |
| `border-strong` | `#475569` |
| `text-primary` | `#F1F5F9` |
| `text-secondary` | `#CBD5E1` |
| `text-muted` | `#94A3B8` |
| `primary` | `#818CF8` (indigo-400) |

Ship with `class` strategy: `<html class="dark">` toggle. Not built in MVP.

---

## 3. Typography

### 3.1 Families

| Role | Font | Load strategy | Notes |
|------|------|---------------|-------|
| UI + body | **Inter** (400/500/600/700) | `next/font/google`, `display: swap` | One family, deliberately default-chosen for SaaS legibility |
| Numeric/data | **Inter with `font-feature-settings: "tnum"`** (tabular numbers) | Same font | Use for all KPI values, table figures, axis labels |
| Diagnostics / config values | **IBM Plex Mono** (400/500) | `next/font/google` | R-hat, R², sampler names, model config JSON, job IDs |

Two families max (per web performance rules). No serif.

### 3.2 Type Scale

Base size is **14px** (denser than a typical marketing site — this is a data tool). All sizes are `rem`, mobile never scales above the desktop size except headings.

| Element | Size | Weight | Line-height | Letter-spacing | Class name |
|---------|------|--------|-------------|----------------|------------|
| Page title (h1) | 24px / 1.5rem | 600 | 1.25 | -0.02em | `text-2xl font-semibold tracking-tight` |
| Section title (h2) | 20px / 1.25rem | 600 | 1.3 | -0.01em | `text-xl font-semibold` |
| Card title (h3) | 16px / 1rem | 600 | 1.4 | — | `text-base font-semibold` |
| Sub-section (h4) | 14px / 0.875rem | 600 | 1.4 | — | `text-sm font-semibold` |
| KPI value | 28–32px | 700 | 1.1 | -0.02em, tabular | `text-3xl font-bold tabular-nums` |
| Body | 14px / 0.875rem | 400 | 1.5 | — | `text-sm` |
| Secondary body | 14px / 0.875rem | 400 | 1.5 | — | `text-sm text-muted-foreground` |
| Caption | 12px / 0.75rem | 400 | 1.4 | — | `text-xs text-muted-foreground` |
| Overline / label | 11px / 0.6875rem | 600 | 1.3 | 0.08em uppercase | `text-[11px] font-semibold uppercase tracking-wider` |
| Mono (diagnostics) | 12–13px | 400 | 1.5 | — | `font-mono text-xs` |

### 3.3 Numeric Formatting Rules

- Money: `$24.1k`, `$1.24M`; exact only in tooltips (`$24,123.00`).
- ROAS: `3.2x`, one decimal.
- Percentages: `12.4%`, one decimal, always with `%` sign.
- Confidence intervals: `[2.1x, 4.0x]` in tooltips and footnote captions.
- Dates: `Mar 15, 2026` in tables; relative only in captions ("2h ago").
- All figures render with `tabular-nums` so columns and KPI rows align.

---

## 4. Component Library — shadcn/ui

### 4.1 Install baseline

`components.json` with default `new-york` style, CSS variables, light base. All components in `app/components/ui/*`. The shadcn/ui **Chart** block wraps Recharts (already a dependency) — use it for every chart; it provides consistent tooltips, axes, and the `chart-config` color contract.

### 4.2 Component map (which component, used where)

| Component | Primary use in MMM | Notes |
|-----------|--------------------|-------|
| `Button` | Every action. Variants: `default` (primary), `secondary`, `outline`, `ghost`, `destructive`, `link`. Sizes: `default` (h-9), `sm` (h-8), `icon` | Loading state uses `Loader2` spinner inside button |
| `Card` | KPI cards, channel cards, chart panels, form panels | Header slot: title (h3) + `DropdownMenu` actions |
| `Input` / `NumberInput` | Config forms, budget amounts, CSV path fields | Numbers: `inputMode="numeric"`, right-aligned value |
| `Label` + `Form` (react-hook-form) | All configuration forms | Errors inline under field, `aria-describedby` |
| `Select` | Model config (sampler, prior family, adstock type), connector type | Native-select fallback on mobile |
| `Command` | **Client switcher** (Section 7) and global search | `cmdk`; keyboard-first |
| `DropdownMenu` | Row actions ("…"), card overflow menus, user menu | |
| `Dialog` | Model config editor, add client, add data source, confirm dialogs | Focus-trapped, `aria-labelledby` |
| `AlertDialog` | Destructive confirmations: "Delete model?", "Disconnect connector?" | |
| `Sheet` | Mobile nav drawer; report "Edit" side panel on small screens | |
| `Tabs` | Dashboard: Overview / Attribution / Models; report sections | |
| `Table` + `DataTable` (TanStack Table) | Clients list, model history, connector status, scenario compare | Column sorting, row selection, sticky header, horizontal scroll |
| `Badge` | Job status, model version, connector status, role chips | Status badges always icon + text |
| `Alert` | Error banners, retrain-due banner, LLM-fallback notice | |
| `Progress` | Training progress, data upload progress | Paired with % label |
| `Skeleton` | All loading states (Section 12.4) | Shimmer = `animate-pulse`, slate-100 |
| `Tooltip` / `HoverCard` | Chart point detail, R-hat explainer, truncation | |
| `Switch` | "Enable scheduled sync", "Use industry priors" | |
| `Slider` + `RadioGroup` | Budget constraint percentages, prior confidence | |
| `Avatar` | Client avatars (initials), user menu | Initials, deterministic bg from name hash |
| `Separator`, `ScrollArea`, `Checkbox`, `Textarea`, `Toast` (sonner) | Standard usage | |

### 4.3 Chart composition (Recharts via shadcn Chart)

| Chart | Component | Use case |
|-------|-----------|----------|
| Line/Area chart | `LineChart` / `AreaChart` | Revenue & spend over time; media decomposition (stacked area) |
| Bar chart (vertical) | `BarChart` | Spend by channel; contribution $ by channel |
| Bar chart (horizontal, 100% stacked) | `BarChart layout="vertical"` + stacked bars | **Budget allocation** current vs proposed (Section 9) |
| Scatter + line | `ScatterChart` + `Line` | **Response curves** (spend vs incremental revenue, diminishing returns) |
| Donut / Pie | `PieChart` | Contribution share % by channel |
| Density / histogram | `BarChart` (custom bin) | Posterior predictive distributions (optional MVP+ polishing) |

Chart rules:
- X axis = time unless the chart is about allocation.
- Every chart has a title (h3), a unit caption (e.g., "revenue, $"), and a `<ChartTooltip>` with formatted currency.
- Grid lines: slate-200, 1px, dashed only for the zero line.
- Empty-data and error states are handled per Section 12.

---

## 5. Layout Rules

### 5.1 App shell

```
┌─────────────┬──────────────────────────────────────────────────┐
│   Sidebar   │  Top bar: [Client switcher] … [Search] [User]    │
│  260px      ├──────────────────────────────────────────────────┤
│  (org nav)  │                                                  │
│             │   Content area (max-width 1400px, centered)      │
│             │   12-col grid, 24px gutter                       │
│             │                                                  │
└─────────────┴──────────────────────────────────────────────────┘
```

- **Sidebar**: fixed 260px wide, full height, `bg-surface` with right `border-subtle`. Contains: org logo + name (top), primary nav (middle), plan/usage card + user menu (bottom). Collapses to a 64px icon rail below `lg` and to a `Sheet` drawer below `md` (Section 13).
- **Top bar**: 64px tall, `bg-surface`, `border-b border-subtle`. Left: **client switcher** (Section 7). Right: global search (⌘K), help, notifications, user avatar menu.
- **Content**: centered column, `max-width: 1400px`, horizontal padding `24px` (`px-6`), vertical `24px`.

### 5.2 Spacing grid

Spacing is a strict **4px base** (Tailwind default scale, no custom overrides):

| Token | Value | Use |
|-------|-------|-----|
| `space-1` | 4px | Tight icon/text gaps |
| `space-2` | 8px | Button internals, list row gaps |
| `space-3` | 12px | Compact card internals |
| `space-4` | 16px | Default card padding, form field gaps |
| `space-6` | 24px | Section gaps, card grid gutters |
| `space-8` | 32px | Page section spacing |
| `space-12` | 48px | Between top-level page blocks |

- Card padding: `p-4` (16px) default; KPI cards `p-5`.
- Card grid: `grid gap-4`, responsive column counts (Section 6.2).
- Border radius: cards & inputs `rounded-lg` (8px), buttons `rounded-md` (6px), badges `rounded-full`.
- Shadows: default card `shadow-sm` (subtle); hover elevate to `shadow-md` only on interactive cards.

### 5.3 Responsive breakpoints

| Breakpoint | Tailwind | Behavior |
|-----------|----------|----------|
| `< 640px` | base | Single column, sidebar → `Sheet` drawer, tables → horizontal scroll |
| `sm 640` | `sm:` | 2-col KPI grid |
| `md 768` | `md:` | Sidebar → icon rail; 3-col KPI grid |
| `lg 1024` | `lg:` | Full sidebar; 4-col KPI grid; 2-col chart layout |
| `xl 1280` | `xl:` | 3-col chart layout; content max-width 1400px caps here |
| `2xl 1536` | `2xl:` | No layout change (content already capped) |

### 5.4 Information architecture (routes)

| Route | Page |
|-------|------|
| `/` | Agency dashboard (KPI + client overview) — redirects to `/dashboard` |
| `/dashboard` | Agency dashboard |
| `/clients` | Clients list |
| `/clients/[id]` | Client detail: dashboard scoped to client |
| `/clients/[id]/models` | Model history + train |
| `/clients/[id]/data` | Data connectors & sync status |
| `/clients/[id]/attribution` | Channel attribution (contribution, curves, decomposition) |
| `/optimize` | Budget optimizer (client-scoped) |
| `/reports` | Reports list; `client/[id]/report/[reportId]` viewer/editor |
| `/settings` | Org settings (team, roles, billing) |

Nav (sidebar): **Dashboard · Clients · Optimizer · Reports · Settings**. Model training, data, and attribution are nested under the client context.

---

## 6. Dashboard Design

Two dashboard levels share the same component grammar:

- **Agency dashboard** (`/dashboard`): cross-client KPIs + client list + recent model runs.
- **Client dashboard** (`/clients/[id]`): all panels scoped to the current client (Section 7).

### 6.1 KPI cards

Row of 4 (xl) / 3 (md) / 2 (sm) / 1 (mobile) cards, `grid gap-4`. KPI card anatomy:

```
┌──────────────────────────────┐
│  OVERLINE LABEL        [info]│
│   $1.24M                    │ ← KPI value, 28-32px tabular
│   ↑ 8.2% vs last period     │ ← delta, colored + arrow
│   caption: "Revenue, Q2 2026"│
└──────────────────────────────┘
```

Agency dashboard KPIs:

| KPI | Format | Source |
|-----|--------|--------|
| Active clients | `12` | org |
| Models trained (30d) | `47` | org usage |
| Avg. model R² | `0.74` | latest jobs |
| Model trains / quota | `47 / 100` (Pro) | plan usage (Starter 20, Pro 100 — spec pricing) |
| Insights generated (30d) | `124` | org usage |

Client dashboard KPIs (spec F3/F6):

| KPI | Format | Delta basis |
|-----|--------|-------------|
| Revenue (period) | `$1.24M` | vs prior period |
| Total spend | `$389k` | vs prior period |
| Blended ROAS | `3.2x` | vs prior period |
| Channel contribution (top) | `Meta 34%` | share of revenue |
| Model status | `Healthy · R² 0.74` | latest model job |

### 6.2 Channel performance cards

Grid of cards, one per channel (`grid gap-4`, `sm:grid-cols-2 xl:grid-cols-3`). Card anatomy:

```
┌──────────────────────────────────┐
│  [●] Meta           ROAS 3.4x    │  ← channel dot (canonical color) + name; ROAS value
│  Spend $182k  ·  34% of revenue  │  ← secondary stats
│  ▁▂▃▅▆▇▆▅▅▆▇▇▂▃▄▅▆▇▅▃         │  ← spend/ROAS sparkline (accent or channel color)
│  Contribution: 34%   ↓ 2pts      │  ← delta with arrow
└──────────────────────────────────┘
```

Hover → `shadow-md` + `cursor-pointer`, click → `Attribution` tab scoped to that channel. Card header includes a `DropdownMenu` (View curve, View trend, Pin to report).

### 6.3 Chart types on dashboards

| Panel | Chart | Placement |
|-------|-------|-----------|
| Revenue & spend over time | `AreaChart` (revenue) + `LineChart` (spend) overlay | Full-width hero chart (xl: col-span-2) |
| Channel contribution share | `PieChart` (donut) | Right of hero |
| Media decomposition | stacked `AreaChart` (trend/seasonality/media per engine) | Full-width |
| Response curves | `ScatterChart` + fitted line | Full-width or 2-col |
| Spend by channel | vertical `BarChart` | 2-col |

### 6.4 Data density

- Tables use `py-2` rows, 14px text — dense but ≥ 32px row height.
- Charts occupy no more than 55% vertical viewport on first paint; below-fold panels are skeletons until scrolled into view (`IntersectionObserver` lazy render).
- Every panel has a footer caption with data period + source (e.g., "Data: Meta API · Mar 1–Jun 30, 2026 · last synced 2h ago").
- Number precision: 2 significant figures on cards, full precision in tooltips.

### 6.5 AI Insights panel

Right rail (or 2-col card) with `accent-soft` background. Each insight is a small card: **icon (accent) + overline `AI INSIGHT` + one-sentence claim + cited metrics + source footer**.

```
AI INSIGHT
Meta ROAS fell from 4.1x to 3.4x (-17%) vs last period.
Cited: ROAS 3.4x [2.9x, 4.0x] · spend +22% · conversions -9%
Verification: model v12 · R² 0.74
```

If LLM is down, this panel renders the template fallback (spec: `report.py _fallback_report`) with a `Badge` reading `Template insights (LLM offline)` — never blank.

---

## 7. Client Switching UX

Agencies manage 3–50+ clients; switching is the highest-frequency navigation act. It must be one action, from anywhere, with zero ambiguity about scope.

### 7.1 The switcher control

- **Trigger**: top-bar left, styled as a compact `Button variant="outline"` that always shows the **current client avatar (initials) + name + chevron**.
- **Menu**: `Command` (cmdk) popover, 320px wide:
  - Search field auto-focused ("Search clients…").
  - List of clients: `Avatar`, name, industry, tiny status dot (`Healthy model` / `No model` / `Needs data`), active client has a checkmark.
  - Footer: `+ Add client` action (opens Add-client dialog).
- **Keyboard**: `⌘K` opens a global command palette that includes clients first, then actions (Train model, Run scenario, Generate report). The switcher itself is reachable via `Alt+C`.

### 7.2 Context indicator

A persistent scope badge at the top of the content area, under the page title:

```
Budget Optimizer                     [Meta] ▸ ▸ [Google]       Context: Acme Apparel ▾
```

- Format: `Context: Acme Apparel` with a small building icon, `primary-soft` background chip, appearing on **every** client-scoped page and chart panel caption.
- When a panel is NOT scoped (org-level), it reads `Org-wide` and is visually distinct (no colored chip).

### 7.3 Global state

- A `ClientProvider` React context + a tiny Zustand store (`useClientStore`) hold `clientId` + `clients[]`.
- Persist `clientId` in `localStorage` and as a URL query param (`?client=<id>`) so deep links and refresh preserve scope. `useSearchParams` is the source of truth; the store mirrors it.
- All server data is keyed by client via TanStack Query: `useQuery({ queryKey: ['client-models', clientId] })`. **Switching a client invalidates nothing globally** — each scope has its own key, so history returns instantly.
- On switch: charts/table show `Skeleton` while the new scope's queries load (no flash of old data — render `null` until `isPending` for the new key).

---

## 8. Model Training UI

### 8.1 Flow (3 steps, spec F2)

A wizard-style `Dialog` (or dedicated route `/clients/[id]/models/train`) with a 3-step `Stepper`:

1. **Data** — choose DataSource(s), date range, target KPI (revenue default), preview table of the canonical frame (`date, channel, spend, impressions, clicks, conversions, revenue`).
2. **Configure** — model parameters (below).
3. **Review & Train** — summary card of every choice, estimated wall-clock time, **Train model** primary button.

Pre-flight validation (fails fast, inline):
- ≥ 2 channels with spend, ≥ 12 weeks of weekly or 60 days of daily data.
- No zero-variance columns ("Google Ads has 0 impressions — remove it or include spend only").
- Target KPI present with nonzero sum.

### 8.2 Configuration form (step 2)

Two-column form (`Form` + `Select`/`Input`), every field with a `Tooltip` explainer. Advanced group under `Accordion` labeled "Advanced (expert)".

| Field | Control | Default | Options / note |
|-------|---------|---------|----------------|
| Prior preset | `RadioGroup` | `industry` | `industry` (recommended), `conservative`, `aggressive`, `custom` — preset chip shows what each means |
| Adstock type | `Select` | `geometric` | `geometric`, `delayed`, `weibull` (engine support per research) |
| Saturation | `Select` | `hill` | `hill`, `michaelis-menten` |
| Sampler | `Select` | `nuts` | `nuts`, `numpyro`, `blackjax`, `nutpie` (engine research) |
| Chains | `NumberInput` | `4` | range 2–8 |
| Draws (per chain) | `NumberInput` | `1000` | range 500–5000; label "draws" with warmup note |
| (Advanced) Custom priors | `Textarea` | — | JSON keyed by channel; validated with error highlighting |

Defaults are the "fast path" — a user who accepts everything and hits **Train** on step 1 should get a valid model (meets <15 min time-to-first-model).

### 8.3 Progress indicator (background job)

Training runs via Celery (spec). The UI polls `GET /clients/[id]/model-jobs/{id}` every 3s.

Job lifecycle states and rendering:

| State | Visual |
|-------|--------|
| `queued` | Info badge `Queued` + spinner; ETA caption "~3 min ahead of you" |
| `running` | `Progress` bar with stage label + %: `Sampling chains (40%)`; stages: Preparing data → Compiling model → Sampling → Computing diagnostics. Elapsed timer. **Cancel** button (destructive, AlertDialog confirm) |
| `succeeded` | Success badge + auto-navigate to **Diagnostics** view |
| `failed` | Error badge + collapsible error detail + "Edit config and retrain" button (pre-fills last config) |

Progress bar rule: never fake precision — if % is unknown, render indeterminate (`animate-pulse`) with stage text instead.

### 8.4 Diagnostics visualization (spec F2)

Post-training `Tabs`: **Overview · Diagnostics · Curves · Decomposition**.

- **Overview**: KPI cards — `R² 0.74` (good/amber/red per Section 2.3), `MAPE 12.4%`, `Chains 4 × 1000`, runtime.
- **Diagnostics table** (mono values):

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| R-hat (max) | 1.01 | ≤ 1.01 | green ✓ |
| R-hat (per param) | 0.99–1.02 | ≤ 1.10 | rows list worst params in red |
| R² | 0.74 | ≥ 0.70 | green ✓ |
| MAPE | 12.4% | < 20% | green ✓ |
| Posterior predictive | pass | visual | green ✓ |

Each row's `?` tooltip gives the plain-language meaning ("R-hat near 1 means the chains converged to the same answer"). **Posterior predictive check** renders observed revenue line overlaid with a shaded band of posterior samples (LineChart, observed = solid `#0F172A`, band = `primary` at 20% opacity).

- **Curves**: response curve `ScatterChart` per channel (spend → incremental revenue), diminishing-returns inflection point marked with a `ReferenceDot`.
- **Decomposition**: stacked area `trend + seasonality + media`.

Model history row links back to this view (`/clients/[id]/models/[jobId]`).

---

## 9. Budget Optimizer UI

Route `/optimize` (client-scoped, spec F4). Left form column + right results column (`lg:grid-cols-5` form=2 / results=3).

### 9.1 Constraint inputs

**Step A — Total budget**: `NumberInput` with currency prefix `$`, required. Caption: "Current plan spends $389k. Recommended total: $421k (±5%)."

**Step B — Per-channel constraints.** One row per channel, left-aligned, using a small inline grid:

```
Meta         Budget cap: [50]% max   ·  Floor: $[20]k absolute
             (current 34% share → proposed up to 50%)
```

Row controls:
- **Min / max %** — `Slider` (dual-handle, 0–100) plus compact `NumberInput` mirror.
- **Absolute floor** — `NumberInput` `$` (e.g., "never below $20k for TV").
- Toggle `Lock` on a channel pins it at current spend (not editable).

Inline validation as the user types: cap sum must be ≥ 100% (`"Channel caps only allow 82% of budget — raise caps or lower floors"`), floors must sum ≤ total budget. Errors are `text-destructive` under the offending field, form submit disabled until clean.

### 9.2 Allocation bar chart

Primary result: a **horizontal 100% stacked bar** comparing **Current** vs **Proposed** allocation (Recharts `BarChart layout="vertical"`, one stack per row):

```
Current   ▓▓▓▓▓ Meta 34% ▓▓ Google 22% ▓▓ TV 18% ▓▓ TikTok 16% ▓▓ Radio 10%
Proposed  ▓▓▓▓▓▓ Meta 40% ▓▓▓ Google 26% ▓▓ TV 12% ▓▓ TikTok 14% ▓▓ Radio 8%
```

- Each segment labeled with `channel %` (always ≥ 8% to label; smaller segments get tooltip only).
- Segments use the canonical channel colors (Section 2.4) so the bar reads against every other chart.
- Under the bar: expected result line — `"Projected revenue $1.42M (+9.4% vs current plan)"` with confidence interval caption `[+4.1%, +13.8%]`.

### 9.3 Expected revenue per channel

`DataTable` with columns: `Channel | Current $ | Proposed $ | Δ Spend | Expected revenue | Δ Revenue | ROAS`. Sorting on all numeric columns. Rows with negative Δ revenue highlighted amber (not red — a reallocation is a trade-off, not an error).

### 9.4 Scenario comparison

- **Save scenario** (primary `secondary` button): name field + save. Saved scenarios list under `Tabs` on the results column: `Scenario | Total budget | Projected revenue | Δ vs current | [Load] [Delete]`.
- **Compare view**: a table/bars with one column per saved scenario vs current plan. Best projected revenue gets a `success` badge "Best".
- **Apply**: primary CTA `Apply to plan` writes the proposed budget back to the client plan and surfaces a toast; secondary `Export as CSV`.
- A "What-if" quick question (spec F5: "What if I shift 20% from TV to Meta?") appears as a small `Input` with a sparkle icon → calls the AI layer; the answer renders in the AI Insights panel, then offers `Set as scenario` to push results into the compare table.

---

## 10. Reports UI

### 10.1 Report flow

1. **Generate**: on `/reports`, choose client + template (`Standard MMM report`) → AI layer generates sections.
2. **Edit**: review/edit draft (below).
3. **Export / Share**: `Export PDF` (primary) + `Copy share link` (secondary).

`/reports` list: `DataTable` — `Client | Report | Period | Status (draft/ready) | Updated | [Edit] [Export] [Share]`.

### 10.2 Auto-generated sections (spec F7)

Rendered as a left-anchored `Tabs`/anchor nav with editable content blocks:

| Section | Content | Editable? |
|---------|---------|-----------|
| 1. Overview | Executive summary, headline KPIs (revenue, ROAS, contribution) | Yes — prose |
| 2. Channel analysis | Contribution % table, response curves, trend narrative | Yes — prose + pinned charts |
| 3. Budget recommendations | Reallocation table + "why" narrative | Yes — prose + table |
| 4. Risks & notes | Anomalies, convergence caveats, model fit warnings | Yes — prose |

- Every generated claim keeps a **citation footnote** (collapsible `HoverCard` on a superscript number): `① ROAS 3.4x [2.9x, 4.0x] · model v12`.
- Generated prose renders through a markdown editor (e.g., `Plate`/`Tiptap` or a simple controlled `Textarea` + preview split). **Edit mode is the default view** — no separate "edit" toggle to discover.
- AI-generation failure → template fallback fills each section with placeholder bullets and an `Alert`: `"LLM unavailable — template report shown. Numbers are from the model; narrative is generic."`

### 10.3 Edit before export

- Block actions per section: `Rewrite with AI`, `Reset to generated`, `Delete`, `Reorder (↑↓)`.
- Unsaved changes indicator on the section header (`● Unsaved`) and a sticky footer bar: `Discard changes` / `Save report` (ghost/secondary) + `Export PDF` (primary). Save persists to the report record; export never happens with unsaved edits silently — the footer intercepts: `"You have unsaved edits — save before exporting?"` AlertDialog.

### 10.4 PDF preview & export

- **Right-side preview pane** (`lg:` split, report editor left / preview right): a static, print-styled rendering of the report as the PDF will look (no extra spacing, A4 portrait, branded header with client name + "Prepared for Acme Apparel by [Agency]").
- On `Export PDF`: client-side print → `window.print()` with a print stylesheet that hides nav/chrome and renders only the report container (simplest reliable route on Next.js; server-side PDF lib is a V2 option).
- Export success toast includes the `Copy share link` secondary action.

### 10.5 Shareable link (client view, spec F7 / role: Client)

- `Copy share link` produces `https://app.mmm.io/r/<token>` — no auth wall (link-based read-only).
- Client view renders the same report **without** any edit affordances, with the client's brand header (client name + agency attribution), and a top banner: `"Shared by [Agency] — read-only view"`.
- Client view never exposes: spend floors, min/max caps, other clients, model diagnostics internals (R-hat etc. are hidden; R² shown as plain "Model fit: good").

---

## 11. Table / List Design

Common `DataTable` recipe (TanStack Table): sticky header (`bg-surface-muted`, `text-xs uppercase tracking-wide text-muted`), `py-2` rows, row hover `bg-surface-muted`, zebra off, footer pagination `rows/page · 1–20 of 347` with Prev/Next.

### 11.1 Clients list (`/clients`)

| Column | Render |
|--------|--------|
| Client | `Avatar` initials + name (link → `/clients/[id]`) |
| Industry | caption text |
| Data sources | stacked `Badge`s: `Shopify · Meta` (max 2 + `+3`) |
| Latest model | `R² 0.74 · Mar 15` or `No model` (muted) |
| Status | status `Badge`: `Healthy` / `Needs data` / `Retrain due` |
| Updated | relative `2h ago` |
| Actions | `DropdownMenu`: Open, Data connectors, Train model, Generate report, Archive |

Card version (for KPI strip) on dashboard: `Avatar + name + industry + status dot` as a list, max 8 visible.

### 11.2 Model history (`/clients/[id]/models`)

| Column | Render |
|--------|--------|
| Run | `#42 · v12` (mono) |
| Date | `Mar 15, 2026 14:32` |
| Config summary | `4ch × 1000 · NUTS · geometric` (mono, truncated + tooltip) |
| R² | mono value + status color |
| R-hat | mono value + status color |
| Duration | `3m 12s` |
| Status | `Badge` (`succeeded`/`running`/`failed`) |
| Actions | `DropdownMenu`: View diagnostics, Retrain, Export report, Delete (AlertDialog) |

### 11.3 Connector status (`/clients/[id]/data`)

| Column | Render |
|--------|--------|
| Connector | icon + name (`Meta Marketing API`) |
| Type | `Badge`: `API` / `CSV` |
| Status | `Badge` + icon: `Connected` (green), `Error` (red), `Not configured` (muted) |
| Last sync | `2h ago` or `—` |
| Next sync | `Tue 09:00` (weekly auto-pull per spec) |
| Actions | `Sync now` (secondary, shows spinner while running), `Configure`, `Disconnect` (AlertDialog) |

---

## 12. Empty State Designs

Every list/chart has a designed empty state: **icon (muted), h2 title, one-line description, primary action + optional secondary action.** Centered, ~`py-16`. No dead space, no "No data" dead-ends.

| Screen | Empty state | Primary CTA | Secondary |
|--------|-------------|-------------|-----------|
| Clients list (no clients yet) | "Welcome to MMM" — "Add your first client to start measuring channels." | `+ Add first client` (opens dialog) | `View demo data` (fills sample client) |
| Client dashboard (no model yet) | "No model yet" — "Connect data, then train your first model in minutes." | `Connect data` | `Train with sample data` |
| Data connectors (no sources) | "No data connected" — "CSV upload is fastest; platform connectors sync automatically." | `Upload CSV` | `Connect Shopify` |
| Models (no models yet) | "No models trained" — "Train a model to see channel attribution." | `Train first model` | `View docs` |
| Charts (no data for period) | "No data for this period" — chart-specific, with period caption | `Change period` | `Sync now` |
| Optimizer (no model) | "Train a model first" — "The optimizer needs a trained model to allocate budget." | `Train model` | — |
| AI insights (LLM down, no fallback) | "Insights unavailable" — explanatory, retry | `Retry` | — |
| Reports (none) | "No reports yet" — "Generate an executive report from your latest model." | `Generate report` | — |

### 12.4 Loading state (Skeleton)

- First load: page `Skeleton` blocks matching final geometry (KPI cards 96px, chart 320px, table 8 rows).
- Query refetch on client switch: panels show `Skeleton`, page never flashes previous client data (Section 7.3).
- Never show a full-page spinner for server queries.

---

## 13. Mobile Responsiveness

MVP is a **desktop-first tool** (agencies do planning on laptops). Mobile gets a deliberate, honest subset:

### 13.1 Works on mobile

- **Dashboard (read-only)**: KPI cards (1-col), channel cards (1-col), charts scale to viewport width. Charts stay interactive via tap tooltips.
- **Clients list**: full-width list; row actions via bottom `Sheet` instead of hover menus.
- **Client switching**: top-bar switcher opens as full `Sheet`; `⌘K` maps to a visible search `Button`.
- **Connector status & model history**: horizontal-scroll tables (`overflow-x-auto`, sticky first column) — no reflow.
- **Notifications, profile, viewing shared reports**: all readable.

### 13.2 Desktop-only (blocked on mobile with a clear affordance)

| Feature | Mobile treatment |
|---------|------------------|
| Model training config wizard | Content **read-only**: show latest job + status; editing shows a `Sheet` notice "Training configuration is desktop-optimized — open on a larger screen" with a link to copy config JSON |
| Budget optimizer constraint sliders | Show last scenario results read-only; sliders replaced by message + `Open on desktop` |
| Report editing | Report **view** only; edit CTA shows the same desktop notice |
| Data connector OAuth setup | Connectors list viewable; "Configure" links out to desktop notice |

Rule: never let a mobile user land on a half-broken editor. Detect pointer: `md:` breakpoints gate editing UI; a `useIsDesktop` hook (matches `min-width: 1024px` and `pointer: fine`) drives the notices.

### 13.3 Touch & ergonomics

- Tap targets ≥ 44px (`h-11` for row buttons on mobile).
- Charts: tooltip on tap, `onPointerDown` faster than hover.
- Sticky top bar so client context stays visible while scrolling tables.

---

## 14. Accessibility Basics

WCAG 2.1 **AA** is the bar (contrast 4.5:1 text, 3:1 large/graphical).

### 14.1 Contrast (verified against palette)

| Pair | Ratio | Pass |
|------|-------|------|
| `text-primary #0F172A` on `bg-surface #FFF` | ~18:1 | AA ✓ |
| `text-secondary #475569` on `#FFF` | ~7.5:1 | AA ✓ |
| `text-muted #94A3B8` on `#FFF` | ~3.0:1 | **AA body ✗** — muted text is allowed for captions/placeholders ONLY, never for content; hover shows full `text-secondary` |
| `primary #4F46E5` on `#FFF` | ~6.3:1 | AA ✓ |
| White on `primary #4F46E5` | ~4.6:1 | AA ✓ |
| `success #16A34A` on `#FFF` | ~3.4:1 | large/graphical ✓ — statuses always pair icon + label, so text contrast is not the sole signal |

Rules: muted text is non-content only; charts encode with shape/label in addition to color; the channel dot color is always paired with the channel name text.

### 14.2 Focus states

- Global focus ring: `outline: 2px solid #4F46E5; outline-offset: 2px` via `focus-visible`. Applied to all interactive elements (buttons, links, inputs, chart points, table rows with actions).
- No custom `:focus` suppression — never `outline-none` without a visible replacement.
- Modal/dialog focus trap; return focus to the trigger on close; `Escape` closes.
- Keyboard: full app operable without a mouse. Client switcher (`Alt+C`), command palette (`⌘K`), menu navigation via arrow keys.

### 14.3 ARIA labels

- Icon-only buttons: `aria-label` (`Sync now`, `Delete model`, `More actions`).
- Client switcher: `role="combobox"`, `aria-expanded`, `aria-controls`.
- Charts: each `<ChartContainer>` gets `role="img"` + `aria-label` summarizing the story ("Bar chart of proposed budget allocation by channel, Meta 40%, Google 26%…") and `aria-describedby` pointing at the caption. Tooltip values also present in the caption text.
- Status badges: `role="status"` where async; progress bars get `role="progressbar"` + `aria-valuenow` + stage text.
- Live regions: training stage updates and toast messages announced via `aria-live="polite"`.
- Tables: `th scope="col"`, sort buttons `aria-sort`.

### 14.4 Other

- `prefers-reduced-motion`: disable shimmer/skeletons, sparkline draw animations, and loading spinners → static equivalents.
- Form errors: `role="alert"`, `aria-describedby` linking field to its error text, `aria-invalid="true"`.
- Color is never the only indicator (Section 2.3 rule). Touch target min 44px on mobile.
- Run automated checks (axe) in CI and a keyboard-only smoke pass before release.

---

## 15. Visual Inspiration References

Draw from these (light-mode, data-first) as compositional references — not to clone, but to match the "quiet instrumentation" bar:

| Reference | What to take |
|-----------|--------------|
| **Linear** | Command palette UX (⌘K), focus-ring discipline, restrained single-accent palette, dense-but-calm list rows |
| **Stripe Dashboard** | KPI card anatomy, generous-but-consistent whitespace, subtle card elevation, plain-language error states |
| **Vercel Dashboard** | Sidebar + topbar shell, project switching pattern (analog to our client switcher), status badges |
| **Amplitude / Mixpanel** | Chart grammar for event/cohort data, tooltip-first drill-down, tabbed analytics views |
| **Mode Analytics** | Data-dense tables, column sorting/formatting standards, tabular numerals |
| **Metabase** | Self-serve charting approachability — what "no dead ends" looks like for non-technical users |
| **Retool / Datadog** | Table density ceiling and row-action patterns; Datadog for diagnostics-style status tables (R-hat table analog) |
| **Observed competitor tools** (Northbeam, Triple Whale — per `research/competitor-landscape.md`) | Their multi-channel performance cards and scenario screens are the category benchmark; our differentiator is **cleaner, lighter, agency-scoped** — fewer colors, more whitespace, editable reports |

Anti-references (explicitly avoid): financial-terminal clutter, marketing-site hero aesthetics, neon/dark-first fintech styling, and "generic Tailwind dashboard-by-numbers" (uniform card grids, single decorative gradient).

---

## Appendix A — Frontend implementation checklist

For the building agent; derived from the above and consistent with the spec.

1. Scaffold shadcn/ui (`components.json`, `new-york`, CSS vars) with the Section 2 tokens in `globals.css`.
2. Install: `@radix-ui/*` primitives via shadcn, `recharts` (present), `@tanstack/react-table`, `cmdk`, `sonner`, `next/font` (Inter + IBM Plex Mono), Zustand for client context.
3. Build `lib/channel-colors.ts`, `lib/format.ts` (Section 3.3), `lib/cn.ts`, `lib/client-store.ts`, `hooks/use-is-desktop.ts`.
4. Shell components: `AppSidebar` (collapsible/drawer), `TopBar` + `ClientSwitcher` (Section 7), `ScopeBadge`.
5. Layouts per Section 5.4; lock `max-w-[1400px]` content wrapper.
6. Dashboard + charts per Section 6 with Section 4.3 Recharts wrappers.
7. Wizard (Section 8), diagnostics views (8.4), optimizer (Section 9), report editor/preview (Section 10).
8. Tables (Section 11), empty states (Section 12), a11y pass (Section 14).
9. Verify: light theme only, `next build` clean, Playwright smoke on `/`, `/clients`, `/clients/[id]`, `/optimize`, `/reports` at 1440 and 390 widths.

---

*End of UI/UX brief. All values, routes, and feature references trace to `docs/_spec.md`; chart/engine capability references trace to `research/*.md`.*
