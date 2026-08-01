"""Tests for model diagnostics module (diagnostics.py).

Covers:
  - compute_diagnostics with converged model (r_hat < 1.1)
  - compute_diagnostics with non-converged model (r_hat >= 1.1)
  - R² and MAPE computation
  - Warnings accumulation and edge cases
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from mmm.core.diagnostics import compute_diagnostics
from mmm.models.schemas import ModelDiagnostics


def _make_y_pred(n: int = 20):
    """Build y (actual) and pred (predicted) series with known R²."""
    rng = np.random.default_rng(42)
    y = pd.Series(rng.normal(1000, 100, n))
    # prediction = actual + small noise → high R²
    pred = y + rng.normal(0, 10, n)
    return y, pred


def _make_model(y: pd.Series, pred_values: np.ndarray, *, idata=None) -> MagicMock:
    """Create a mock model with predict. idata=None skips rhat computation."""
    model = MagicMock()
    model.idata = idata
    model.predict.return_value = pd.Series(pred_values)
    return model


def _patch_summary(monkeypatch: pytest.MonkeyPatch, rhat_values) -> MagicMock:
    """Patch arviz.summary so compute_diagnostics sees the given r_hat values."""
    import arviz as az

    r_hat_series = pd.Series(rhat_values)
    summary = MagicMock()
    summary.r_hat = r_hat_series
    summary.__getitem__ = lambda self, key: r_hat_series
    summary.__bool__ = lambda self: True
    monkeypatch.setattr(az, "summary", lambda *a, **kw: summary)
    return summary


# ---------------------------------------------------------------------------
# Test: converged model (r_hat < 1.1)
# ---------------------------------------------------------------------------

class TestComputeDiagnosticsConverged:
    def test_returns_model_diagnostics(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.0])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert isinstance(result, ModelDiagnostics)
        assert result.model_name == "test-model"

    def test_converged_when_rhat_below_threshold(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.02, 0.99])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.converged is True
        assert result.rhat_max == 1.02
        assert result.rhat_max < 1.1

    def test_r2_positive_and_high(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.0])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.r2 > 0.9

    def test_mape_is_percentage(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.0])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.mape >= 0
        assert result.mape < 100


# ---------------------------------------------------------------------------
# Test: non-converged model (r_hat >= 1.1)
# ---------------------------------------------------------------------------

class TestComputeDiagnosticsNonConverged:
    def test_non_converged_when_rhat_high(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.25])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.converged is False
        assert result.rhat_max == 1.25

    def test_warning_added_for_non_convergence(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.3])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert any("R-hat" in w for w in result.warnings)

    def test_exact_threshold_1_1_marks_non_converged(self, monkeypatch):
        y, pred = _make_y_pred()
        _patch_summary(monkeypatch, [1.1])
        model = _make_model(y, pred.values, idata=MagicMock())
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        # 1.1 is NOT < 1.1 → non-converged
        assert result.converged is False


# ---------------------------------------------------------------------------
# Test: edge cases
# ---------------------------------------------------------------------------

class TestComputeDiagnosticsEdgeCases:
    def test_no_idata_uses_default_rhat(self):
        """When model has no idata, rhat_max defaults to 1.1 and converged=True."""
        y, pred = _make_y_pred()
        model = _make_model(y, pred.values)
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.rhat_max == 1.1
        assert result.converged is True

    def test_predictions_all_zero_gives_low_r2(self):
        """When predictions are zero, R² should be poor (<= 0)."""
        y = pd.Series([100.0] * 20)
        pred = np.zeros(20)
        model = _make_model(y, pred)
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.r2 <= 0.0
        assert any("low R" in w for w in result.warnings)

    def test_existing_warnings_are_appended(self):
        """Pre-existing warnings list is extended, not replaced."""
        y, pred = _make_y_pred()
        model = _make_model(y, pred.values)
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model", warnings=["existing_warning"])
        assert "existing_warning" in result.warnings

    def test_predict_exception_falls_back_to_zero_r2(self):
        """If model.predict() raises, R² and MAPE default to 0."""
        y = pd.Series([100.0] * 20)
        model = _make_model(y, np.zeros(20))
        model.predict.side_effect = RuntimeError("predict broke")
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.r2 == 0.0
        assert result.mape == 0.0

    def test_idata_exception_falls_back_to_default_rhat(self, monkeypatch):
        """If az.summary raises, rhat_max defaults to 1.1."""
        y, pred = _make_y_pred()
        import arviz as az

        model = _make_model(y, pred.values, idata=MagicMock())
        monkeypatch.setattr(az, "summary", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("summary broke")))
        result = compute_diagnostics(model, y, pd.DataFrame(), "test-model")
        assert result.rhat_max == 1.1
        assert result.converged is True
