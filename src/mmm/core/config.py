"""Model configuration helpers and presets."""
from __future__ import annotations

from mmm.models.schemas import Granularity, ModelConfig

CHANNEL_PRIOR_HINTS: dict[str, list[float]] = {
    "tv": [1.0, 0.6, 0.8],
    "radio": [1.2, 0.5, 0.9],
    "print": [1.4, 0.4, 1.0],
    "search": [2.0, 0.3, 1.0],
    "social": [1.8, 0.5, 0.9],
    "meta": [1.8, 0.5, 0.9],
    "tiktok": [1.8, 0.6, 0.9],
    "youtube": [1.5, 0.4, 1.0],
}

def suggest_saturation_beta(channels: list[str]) -> list[float]:
    betas: list[float] = []
    for ch in channels:
        key = next((k for k in CHANNEL_PRIOR_HINTS if k in ch.lower()), None)
        betas.append(CHANNEL_PRIOR_HINTS[key][0] if key else 1.5)
    return betas

def build_model_config(
    *, channels: list[str], granularity: str = "week", draws: int | None = None,
    tune: int | None = None, chains: int | None = None, adstock_max_lag: int | None = None,
    saturation_beta: list[float] | None = None, **extra,
) -> ModelConfig:
    if adstock_max_lag is None:
        adstock_max_lag = 8 if granularity == "week" else 14
    if saturation_beta is None:
        saturation_beta = suggest_saturation_beta(channels)
    # Production defaults: 4 chains / 1000 draws / 1000 tune
    if draws is None:
        draws = 1000
    if tune is None:
        tune = 1000
    if chains is None:
        chains = 4
    return ModelConfig(
        granularity=Granularity(granularity), draws=draws, tune=tune, chains=chains,
        adstock_max_lag=adstock_max_lag, saturation_beta=saturation_beta, **extra,
    )
