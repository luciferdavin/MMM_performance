"""Core MMM model — thin wrapper around PyMC-Marketing."""
from __future__ import annotations
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
import pandas as pd
import numpy as np
from mmm.models.schemas import (
    Allocation, AllocationResult, BudgetConstraints, ChannelContribution,
    FitResult, ForecastPoint, ModelConfig, ModelDiagnostics, MMMDataset,
)
from mmm.core.preprocessor import to_training_frame, validate_dataset
from mmm.core.diagnostics import compute_diagnostics
from mmm.core.optimizer import allocate_budget_scipy

if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)

# Lazily imported to avoid import error when pymc_marketing isn't installed.
_PyMC_MMM = None
_GeometricAdstock = None
_HillSaturation = None

def _lazy_pmc_mmm():
    global _PyMC_MMM
    if _PyMC_MMM is None:
        from pymc_marketing.mmm import MMM as _MMM
        _PyMC_MMM = _MMM
    return _PyMC_MMM

def _lazy_transformations():
    global _GeometricAdstock, _HillSaturation
    if _GeometricAdstock is None or _HillSaturation is None:
        from pymc_marketing.mmm.components.adstock import GeometricAdstock
        from pymc_marketing.mmm.components.saturation import HillSaturation
        _GeometricAdstock = GeometricAdstock
        _HillSaturation = HillSaturation
    return _GeometricAdstock, _HillSaturation


class MMMModel:
    """Unified model interface over PyMC-Marketing."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.model_id = uuid.uuid4().hex[:12]
        self._fitted_model = None
        self._fit_data: pd.DataFrame | None = None
        self._channel_columns: list[str] = []
        self._target_column: str = "revenue"
        self._posterior = None
        self._diagnostics: ModelDiagnostics | None = None

    @property
    def is_fitted(self) -> bool:
        return self._fitted_model is not None

    def fit(self, dataset: MMMDataset) -> FitResult:
        try:
            MMMClass = _lazy_pmc_mmm()
            wide, channels = to_training_frame(
                dataset,
                granularity=self.config.granularity,
                target_column=self.config.target_column,
            )
            warnings = validate_dataset(wide, channels)
            # Reset index so "bucket" becomes a column.  Extract X and y from
            # the *same* reset frame so their integer indices match (required
            # by pymc_marketing.model_builder.fit).
            wide_r = wide.reset_index()
            date_col = "bucket" if "bucket" in wide_r.columns else wide_r.columns[0]
            X = wide_r[[date_col] + list(channels)]
            y = wide_r[self.config.target_column]
            self._channel_columns = channels
            self._target_column = self.config.target_column
            self._fit_data = wide
            GeometricAdstock, HillSaturation = _lazy_transformations()
            mmm_kwargs: dict = dict(
                date_column=date_col,
                channel_columns=channels,
                adstock=GeometricAdstock(l_max=self.config.adstock_max_lag),
                saturation=HillSaturation(),
                adstock_first=self.config.adstock_first,
                sampler_config={
                    "draws": self.config.draws,
                    "tune": self.config.tune,
                    "chains": self.config.chains, "target_accept": self.config.target_accept,
                },
            )
            pmc_model = MMMClass(**mmm_kwargs)
            pmc_model.fit(
                X=X,
                y=y,
                random_seed=self.config.random_seed,
            )
            self._fitted_model = pmc_model
            diag = compute_diagnostics(pmc_model, y, X, self.config.name, warnings)
            self._diagnostics = diag
            self._posterior = pmc_model.posterior if hasattr(pmc_model, "posterior") else None
            return FitResult(
                model_name=self.config.name,
                model_id=self.model_id,
                status="ok",
                diagnostics=diag,
            )
        except Exception as exc:
            logger.exception("model fit failed")
            return FitResult(
                model_name=self.config.name,
                model_id=self.model_id,
                status="failed",
                error=str(exc),
            )

    def predict(self, data: pd.DataFrame | None = None, *, n_periods: int = 12) -> list[ForecastPoint]:
        assert self.is_fitted, "call fit() first"
        df = data if data is not None else self._fit_data
        assert df is not None
        pred = self._fitted_model.predict(df)
        return [
            ForecastPoint(date=str(df.index[i]), predicted_revenue=float(v), lower=float(v * 0.85), upper=float(v * 1.15))
            for i, v in enumerate(pred.values.flatten() if hasattr(pred, "values") else pred)
        ]

    def get_channel_contributions(self) -> list[ChannelContribution]:
        assert self.is_fitted, "call fit() first"
        contrib_result = self._fitted_model.compute_channel_contribution_original_scale(
            original_scale_input=self._fit_data,
        )
        contrib_samples = contrib_result.channel_contribution_original_scale_samples
        if hasattr(contrib_samples, "values"):
            contrib_samples = contrib_samples.values
        # Shape: (chain, draw, date, channel) → reduce to (channel,)
        contrib_median = np.median(contrib_samples, axis=(0, 1, 2))
        total_spend = self._fit_data[self._channel_columns].sum(axis=0) if self._fit_data is not None else pd.Series(1.0, index=self._channel_columns)
        total_contrib = contrib_median.sum()
        results: list[ChannelContribution] = []
        for i, ch in enumerate(self._channel_columns):
            c = float(contrib_median[i])
            s = float(total_spend.get(ch, 0))
            share = c / total_contrib if total_contrib > 0 else 0
            roas = c / s if s > 0 else 0
            results.append(ChannelContribution(channel=ch, contribution=c, share=share, roas=roas, spend=s))
        results.sort(key=lambda x: x.roas, reverse=True)
        return results

    def allocate_budget(
        self, total_budget: float, *, date_start: str | None = None, date_end: str | None = None,
        constraints: BudgetConstraints | None = None,
    ) -> AllocationResult:
        assert self.is_fitted, "call fit() first"
        if self.config.sampler in ("nuts", "numpyro"):
            try:
                # Derive num_periods from the date range (or full training window).
                if date_start or date_end:
                    start = pd.to_datetime(date_start) if date_start else self._fit_data.index.min()
                    end = pd.to_datetime(date_end) if date_end else self._fit_data.index.max()
                    mask = (self._fit_data.index >= start) & (self._fit_data.index <= end)
                    num_periods = int(mask.sum())
                else:
                    num_periods = len(self._fit_data)

                # Build per-channel budget_bounds from constraints if provided.
                budget_bounds: dict[str, tuple[float, float]] | None = None
                if constraints and constraints.channel_bounds:
                    budget_bounds = constraints.channel_bounds

                # v0.19.2 API: optimize_budget returns (DataArray, OptimizeResult)
                optimal_budgets, _ = self._fitted_model.optimize_budget(
                    budget=total_budget,
                    num_periods=num_periods,
                    budget_bounds=budget_bounds,
                )
                allocs = [
                    Allocation(
                        channel=str(ch),
                        allocated_budget=float(optimal_budgets.sel(channel=ch).item()),
                        share=(
                            float(optimal_budgets.sel(channel=ch).item()) / total_budget
                            if total_budget
                            else 0
                        ),
                        expected_revenue=0.0,
                    )
                    for ch in optimal_budgets.channel.values
                ]
                total_rev = sum(a.expected_revenue for a in allocs)
                return AllocationResult(
                    total_budget=total_budget,
                    allocations=allocs,
                    expected_total_revenue=total_rev,
                )
            except Exception:
                logger.warning("pymc optimize_budget failed, falling back to scipy optimizer")
        return allocate_budget_scipy(self, total_budget, constraints=constraints)

    def save(self, path: Path | str) -> None:
        assert self.is_fitted, "call fit() first"
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self._fitted_model.save(str(path / "model.json"))
        pd.to_pickle(self._fit_data, path / "fit_data.pkl")
        pd.to_pickle(self._channel_columns, path / "channels.pkl")
        logger.info("model saved to %s", path)

    @classmethod
    def load(cls, path: Path | str, config: ModelConfig | None = None) -> "MMMModel":
        path = Path(path)
        MMMClass = _lazy_pmc_mmm()
        loaded = MMMClass.load(str(path / "model.json"))
        config = config or ModelConfig()
        instance = cls(config)
        instance._fitted_model = loaded
        instance._fit_data = pd.read_pickle(path / "fit_data.pkl")
        instance._channel_columns = pd.read_pickle(path / "channels.pkl")
        instance._target_column = config.target_column
        return instance
