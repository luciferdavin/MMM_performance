"""Tests for the core MMMModel engine (engine.py).

Covers:
  - MMMModel constructor + config validation
  - fit() with mocked PyMC-Marketing API
  - get_channel_contributions() return shape
  - allocate_budget fallback path (scipy)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from mmm.models.schemas import (
    BudgetConstraints,
    ChannelContribution,
    FitResult,
    ModelConfig,
    ModelDiagnostics,
    MMMDataset,
    MediaRecord,
)
from mmm.core.engine import MMMModel


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_dataset(n_weeks: int = 8) -> MMMDataset:
    """Build a small synthetic dataset with two channels."""
    records = []
    base = pd.Timestamp("2024-01-01")
    for w in range(n_weeks):
        for ch, spend, rev in [("meta", 1000 + w * 10, 3000 + w * 30),
                                ("google", 800 + w * 8, 2400 + w * 24)]:
            records.append(
                MediaRecord(
                    date=base + pd.Timedelta(days=w * 7),
                    channel=ch,
                    spend=spend,
                    impressions=spend * 50,
                    clicks=spend // 2,
                    conversions=spend // 20,
                    revenue=rev,
                )
            )
    return MMMDataset(records=records)


@pytest.fixture
def default_config() -> ModelConfig:
    return ModelConfig(name="unit-test-model", draws=200, tune=200, chains=1)


@pytest.fixture
def sample_dataset() -> MMMDataset:
    return _make_dataset()


# ---------------------------------------------------------------------------
# 1. Constructor + config validation
# ---------------------------------------------------------------------------

class TestMMMModelConstructor:
    def test_stores_config(self, default_config):
        model = MMMModel(default_config)
        assert model.config is default_config
        assert model.config.name == "unit-test-model"

    def test_model_id_is_hex_12(self, default_config):
        model = MMMModel(default_config)
        assert len(model.model_id) == 12
        assert all(c in "0123456789abcdef" for c in model.model_id)

    def test_starts_unfitted(self, default_config):
        model = MMMModel(default_config)
        assert not model.is_fitted
        assert model._fitted_model is None
        assert model._fit_data is None
        assert model._channel_columns == []

    def test_config_defaults(self):
        cfg = ModelConfig()
        assert cfg.name == "default"
        assert cfg.target_column == "revenue"
        assert cfg.granularity.value == "week"
        assert cfg.adstock_max_lag == 8
        assert cfg.sampler == "nuts"
        assert cfg.draws == 1000
        assert cfg.tune == 1000
        assert cfg.chains == 4
        assert cfg.random_seed == 42

    def test_config_validation_draws_min(self):
        with pytest.raises(Exception):
            ModelConfig(draws=10)

    def test_config_validation_chains_min(self):
        with pytest.raises(Exception):
            ModelConfig(chains=0)


# ---------------------------------------------------------------------------
# 2. fit() — mocked pymc_marketing API
# ---------------------------------------------------------------------------

class TestMMMModelFit:
    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_fit_calls_pymc_with_correct_kwargs(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        """Verify fit() constructs MMM with the right keyword arguments."""
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls

        mock_Adstock = MagicMock()
        mock_Saturation = MagicMock()
        mock_trans.return_value = (mock_Adstock, mock_Saturation)

        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.02, r2=0.9, mape=5.0,
        )

        model = MMMModel(default_config)
        result = model.fit(sample_dataset)

        # MMM was instantiated
        mock_MMM_cls.assert_called_once()
        call_kwargs = mock_MMM_cls.call_args
        assert "date_column" in call_kwargs.kwargs
        assert call_kwargs.kwargs["date_column"] == "bucket"
        assert "channel_columns" in call_kwargs.kwargs
        assert "meta" in call_kwargs.kwargs["channel_columns"]
        assert "google" in call_kwargs.kwargs["channel_columns"]
        assert call_kwargs.kwargs["adstock_first"] is True
        assert call_kwargs.kwargs["sampler_config"]["draws"] == 200
        assert call_kwargs.kwargs["sampler_config"]["tune"] == 200
        assert call_kwargs.kwargs["sampler_config"]["chains"] == 1

        # fit was called on the instance
        mock_MMM_cls.return_value.fit.assert_called_once()

        # Result is FitResult with status ok
        assert isinstance(result, FitResult)
        assert result.status == "ok"
        assert result.model_name == "unit-test-model"

    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_fit_sets_is_fitted(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(default_config)
        assert not model.is_fitted
        model.fit(sample_dataset)
        assert model.is_fitted

    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    def test_fit_returns_failed_on_exception(
        self, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_MMM_cls.side_effect = RuntimeError("pymc exploded")
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())

        model = MMMModel(default_config)
        result = model.fit(sample_dataset)
        assert result.status == "failed"
        assert "pymc exploded" in result.error

    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_fit_stores_fit_data_and_channels(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(default_config)
        model.fit(sample_dataset)
        assert model._fit_data is not None
        assert "meta" in model._channel_columns
        assert "google" in model._channel_columns

    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_fit_calls_compute_diagnostics(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(default_config)
        model.fit(sample_dataset)
        mock_diag.assert_called_once()


# ---------------------------------------------------------------------------
# 3. get_channel_contributions() — mocked
# ---------------------------------------------------------------------------

class TestGetChannelContributions:
    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_contributions_shape(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(default_config)
        model.fit(sample_dataset)

        # Mock the channel contribution computation
        # Shape: (chain=1, draw=200, date=8, channel=2)
        contrib_data = np.random.default_rng(42).random((1, 200, 8, 2))
        mock_contrib_result = MagicMock()
        mock_contrib_result.channel_contribution_original_scale_samples = contrib_data
        model._fitted_model.compute_channel_contribution_original_scale.return_value = mock_contrib_result

        results = model.get_channel_contributions()
        assert isinstance(results, list)
        assert len(results) == 2
        channels_returned = {r.channel for r in results}
        assert channels_returned == {"meta", "google"}
        for r in results:
            assert isinstance(r, ChannelContribution)
            assert r.contribution >= 0
            assert r.spend > 0
            assert r.share >= 0

    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_contributions_sorted_by_roas_desc(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(default_config)
        model.fit(sample_dataset)

        # Create contributions where google has higher ROAS
        contrib_data = np.zeros((1, 10, 8, 2))
        contrib_data[:, :, :, 0] = 100  # meta lower
        contrib_data[:, :, :, 1] = 200  # google higher
        mock_contrib_result = MagicMock()
        mock_contrib_result.channel_contribution_original_scale_samples = contrib_data
        model._fitted_model.compute_channel_contribution_original_scale.return_value = mock_contrib_result

        results = model.get_channel_contributions()
        # Should be sorted by ROAS descending
        assert results[0].roas >= results[1].roas

    def test_contributions_raises_when_unfitted(self, default_config):
        model = MMMModel(default_config)
        with pytest.raises(AssertionError, match="call fit"):
            model.get_channel_contributions()


# ---------------------------------------------------------------------------
# 4. allocate_budget fallback path
# ---------------------------------------------------------------------------

class TestAllocateBudget:
    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_allocate_falls_back_to_scipy_when_not_nuts_sampler(
        self, mock_diag, mock_trans, mock_pmc, sample_dataset,
    ):
        """When sampler is not nuts/numpyro, pymc allocate_budget is skipped."""
        config = ModelConfig(name="test", sampler="random_walk", draws=200, tune=200, chains=1)
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="test", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(config)
        model.fit(sample_dataset)

        # Mock get_channel_contributions for scipy fallback
        mock_contribs = [
            ChannelContribution(channel="meta", contribution=5000, share=0.5, roas=3.5, spend=2000),
            ChannelContribution(channel="google", contribution=4000, share=0.5, roas=3.0, spend=1800),
        ]
        model.get_channel_contributions = MagicMock(return_value=mock_contribs)

        result = model.allocate_budget(10000)
        assert len(result.allocations) == 2
        total = sum(a.allocated_budget for a in result.allocations)
        assert abs(total - 10000) < 1.0

    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_allocate_falls_back_when_pymc_alloc_raises(
        self, mock_diag, mock_trans, mock_pmc, sample_dataset,
    ):
        """When pymc allocate_budget raises, should fall back to scipy."""
        config = ModelConfig(name="test", sampler="nuts", draws=200, tune=200, chains=1)
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="test", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(config)
        model.fit(sample_dataset)

        # pymc allocate_budget will raise
        model._fitted_model.allocate_budget.side_effect = RuntimeError("pymc alloc failed")

        # Mock get_channel_contributions for scipy fallback
        mock_contribs = [
            ChannelContribution(channel="meta", contribution=5000, share=0.5, roas=3.5, spend=2000),
            ChannelContribution(channel="google", contribution=4000, share=0.5, roas=3.0, spend=1800),
        ]
        model.get_channel_contributions = MagicMock(return_value=mock_contribs)

        result = model.allocate_budget(10000)
        assert len(result.allocations) == 2

    def test_allocate_raises_when_unfitted(self, default_config):
        model = MMMModel(default_config)
        with pytest.raises(AssertionError, match="call fit"):
            model.allocate_budget(10000)


# ---------------------------------------------------------------------------
# 5. predict() basics
# ---------------------------------------------------------------------------

class TestPredict:
    @patch("mmm.core.engine._lazy_pmc_mmm")
    @patch("mmm.core.engine._lazy_transformations")
    @patch("mmm.core.engine.compute_diagnostics")
    def test_predict_returns_forecast_points(
        self, mock_diag, mock_trans, mock_pmc, default_config, sample_dataset,
    ):
        mock_MMM_cls = MagicMock()
        mock_pmc.return_value = mock_MMM_cls
        mock_trans.return_value = (MagicMock(), MagicMock())
        mock_diag.return_value = ModelDiagnostics(
            model_name="unit-test-model", converged=True, rhat_max=1.0, r2=0.8, mape=5.0,
        )

        model = MMMModel(default_config)
        model.fit(sample_dataset)

        # Mock predict to return numpy array
        n_rows = len(model._fit_data)
        model._fitted_model.predict.return_value = np.ones(n_rows) * 5000

        from mmm.models.schemas import ForecastPoint
        forecasts = model.predict()
        assert len(forecasts) == n_rows
        for fp in forecasts:
            assert fp.predicted_revenue > 0
            assert fp.lower < fp.predicted_revenue
            assert fp.upper > fp.predicted_revenue

    def test_predict_raises_when_unfitted(self, default_config):
        model = MMMModel(default_config)
        with pytest.raises(AssertionError, match="call fit"):
            model.predict()
