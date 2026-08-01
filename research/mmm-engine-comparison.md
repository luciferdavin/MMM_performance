# MMM Engine Comparison

*Research date: 2026-08-01. Recommendation: **PyMC-Marketing** as core engine.*

## 1. PyMC-Marketing (RECOMMENDED)

- **Stack**: Python 3.11+, PyMC (Bayesian), Apache 2.0
- **Maintainer**: PyMC Labs (consulting firm; strong community)
- **Status**: Actively maintained; v4+ line; ~10k+ users
- **MMM features**
  - Adstock transforms: geometric, delayed, Weibull (left/right)
  - Saturation: Hill function, Michaelis-Menten
  - Budget optimizer: `MMM.allocate_budget()` (scipy-optimize; maximizes revenue subject to spend constraint)
  - Custom priors, experiment/lift-test calibration
  - Time-varying intercepts via Gaussian Processes
  - Multi-sampler backends: PyMC NUTS, NumPyro, BlackJax, Nutpie
  - Scikit-learn-style `fit()` / `predict()` API
  - DAG-based causal identification; GPU acceleration
- **Extras**: CLV (BG/NBD, Gamma-Gamma), Bass Diffusion, Discrete Choice, CSA
- **Fit**: Best for a product we wrap — full API, documented, active

## 2. Google Meridian (secondary / alternative)

- **Stack**: Python 3.11-3.13, TensorFlow Probability, NUTS MCMC
- **Status**: Actively maintained (v1.7.1+, ~1k commits). **Successor to LightweightMMM** (archived Jan 2026).
- **Features**: Bayesian MMM, geo-level hierarchical modeling, budget optimizer, scenario planning, reach/frequency optimization, experiment calibration
- **Fit**: Strong when clients need Google-style geo models; heavier TFP dependency

## 3. Meta Robyn (not recommended for SaaS)

- **Stack**: R (primary), Python beta (LLM-translated), Nevergrad for HP search
- **Features**: Semi-automated model selection via evolutionary algorithm, Ridge regression, adstock/saturation, budget allocation, model clustering
- **Strengths**: Automated hyperparameter search reduces manual decisions
- **Weaknesses**: R-first integration friction; Ridge less flexible than Bayesian; beta Python port unstable; Meta license restrictive for SaaS distribution

## 4. Google LightweightMMM (deprecated)

- **Status**: ARCHIVED 2026-01-19, read-only. Replaced by Meridian. **Do not use.**

## Recommendation

| Criterion | PyMC-Marketing | Meridian | Robyn |
|-----------|---------------|----------|-------|
| Python-native | Yes | Yes | Partial (R primary) |
| Budget optimizer | Yes | Yes | Yes |
| Custom priors | Yes | Yes | Limited |
| License (SaaS-safe) | Apache 2.0 | Apache 2.0 | Meta (restrictive) |
| Active maintenance | Yes | Yes | Yes (R) |
| Ease of wrapping | High | Medium | Low |

**Decision**: Wrap **PyMC-Marketing**. Add Meridian as an optional second engine for clients requiring geo-level modeling. Skip Robyn.

*Sources: pymc-marketing GitHub (pymc-labs), github.com/google/meridian, github.com/google/lightweight_mmm (archived), github.com/facebookexperimental/Robyn.*
