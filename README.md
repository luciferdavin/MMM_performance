# MMM Platform - AI Marketing Mix Modeling for Agencies

Multi-tenant SaaS tool that helps marketing agencies measure channel performance, attribute revenue, and **optimize ad spend allocation** using Bayesian Marketing Mix Modeling (MMM).

## Why MMM?

As third-party cookies and platform attribution decay, agencies can no longer trust click-based attribution alone. MMM uses historical time-series data (media spend by channel + revenue) to statistically measure each channel's contribution, model diminishing returns, and recommend optimal budget splits.

## Core Engine

Wraps **PyMC-Marketing** (Bayesian MMM on PyMC):

- Adstock (lag/carryover) + saturation (Hill curve) transforms
- Channel contribution / ROAS attribution
- **Budget optimizer**: maximize revenue under constraints (total budget, per-channel min/max, floors)
- Model diagnostics: R-hat convergence, R^2, MAPE
- Forecast + scenario planning
- Save/load model artifacts

## Architecture

```
Connectors (Meta/Google/TikTok/Shopify/CSV) -> Preprocessor -> MMMModel (PyMC)
   -> Budget Optimizer -> AI Insights (Ollama/Claude/OpenAI)
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
mmm generate-sample
mmm train --csv data/sample/sample_data.csv
mmm allocate --model model_artifacts/model --budget 10000
mmm contributions --model model_artifacts/model
```

## Project Layout

```
src/mmm/
|-- core/          # engine, preprocessor, optimizer, diagnostics, config
|-- connectors/    # Meta, Google Ads, GA4, TikTok, Shopify, CSV
|-- ai/            # LLM providers (Ollama/Claude/OpenAI), insights, reports
|-- models/        # Pydantic schemas
|-- cli.py         # mmm CLI
tests/             # pytest suite
data/sample/       # synthetic dataset
```

## LLM Providers

Default is **self-hosted Ollama** (zero API cost). Swappable to Claude or OpenAI:

```bash
export LLM_PROVIDER=ollama       # default
export LLM_PROVIDER=anthropic    # needs ANTHROPIC_API_KEY
export LLM_PROVIDER=openai       # needs OPENAI_API_KEY
```

## Connectors

All connectors output a normalized schema: `date, channel, spend, impressions, clicks, conversions, revenue`. CSV is the universal fallback.

## License

Apache-2.0
