# MMM SaaS Competitive Landscape

*Research date: 2026-08-01.*

## Players

| Tool | Focus | Agency support | Method | Differentiator |
|------|-------|---------------|--------|----------------|
| **Measured** | Enterprise brands | No (brand-direct) | Causal MMM + incrementality tests | 300+ integrations, SOC2/ISO, benchmarking; "triangulated measurement" |
| **Northbeam** | DTC ecommerce | Yes | MTA (pixel) + MMM Plus | First-party pixel attribution + MMM hybrid; tracks $130B attributed revenue |
| **Triple Whale** | DTC ecommerce | Yes (2,000+ agencies) | MMM + MTA + incrementality | AI OS ("Moby" agent), 60k brands, Shopify-first, 60+ connectors |
| **Recast** | DTC/ecommerce | Limited | Bayesian MMM | Channel forecasting, scenario planning |
| **Mutinex** | Growth teams | Yes (agency focus) | MMM | Multi-brand, growth modeling |

## Observations

1. **Agency support is a gap.** Measured targets brands direct. Only Triple Whale / Mutinex emphasize agencies. Agencies currently stitch together spreadsheets, platform reports, and ad-hoc consultant MMM.
2. **Hybrid measurement is the norm.** MTA (pixel) + MMM + incrementality. MMM alone is not enough — agencies want MMM as the strategic layer, MTA for tactical.
3. **Ecommerce/DTC is the wedge.** Shopify-first onboarding is how Triple Whale/Northbeam scaled. A Shopify connector is table-stakes for the ecommerce segment.
4. **AI is the current battleground.** Triple Whale ships an AI agent (Moby). NL insights + automated scenario planning is where differentiation lands.
5. **Pricing is opaque.** All vendors demo-only; typical model is annual SaaS + implementation/consulting services.

## Our Differentiation

- Agency-first multi-tenant UX (clients, white-label reports, roles, audit)
- AI-native NL insights + budget scenario planner
- Fast parallel model training + pre-built industry priors
- Open-source Bayesian engine (PyMC-Marketing) => cost advantage vs. vendor-locked proprietary models
- Self-hosted Ollama LLM => zero per-insight API cost; data stays in-house

## Pricing hypothesis (to validate)

| Tier | Who | Price | Includes |
|------|-----|-------|----------|
| Starter | Small agencies | $199/mo | 3 clients, CSV, 20 model trains/mo |
| Pro | Growth agencies | $499/mo | 15 clients, platform connectors, scenario planner |
| Enterprise | Large agencies | Custom | Unlimited clients, white-label, SSO, incrementality |

*Sources: measured.com, northbeam.io, triplewhale.com, recaststudios.com, mutinex.com (fetched 2026-08-01).*
