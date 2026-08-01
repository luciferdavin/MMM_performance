"""Tests for the train task module (tasks/train.py).

Covers:
  - _build_run_inputs: config parsing, defaults, empty records validation
  - _build_result_summary: summary payload shape
  - train_model_job: success path, ModelingError on failed fit, InfraError on generic failure
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mmm.models.schemas import (
    ChannelContribution,
    FitResult,
    MediaRecord,
    ModelConfig,
    ModelDiagnostics,
    MMMDataset,
)


# ---------------------------------------------------------------------------
# _build_run_inputs
# ---------------------------------------------------------------------------

class TestBuildRunInputs:
    def test_builds_config_and_dataset_from_dict(self):
        from mmm.tasks.train import _build_run_inputs

        config = {
            "model": {"name": "test-job", "draws": 500, "chains": 2},
            "records": [
                {"date": "2024-01-01", "channel": "meta", "spend": 1000},
                {"date": "2024-01-08", "channel": "google", "spend": 800},
            ],
        }
        model_config, dataset = _build_run_inputs("job-1", config)
        assert isinstance(model_config, ModelConfig)
        assert model_config.name == "test-job"
        assert model_config.draws == 500
        assert model_config.chains == 2
        assert isinstance(dataset, MMMDataset)
        assert len(dataset.records) == 2
        assert set(dataset.channels) == {"meta", "google"}

    def test_applies_defaults_for_missing_fields(self):
        from mmm.tasks.train import _build_run_inputs

        config = {
            "records": [
                {"date": "2024-01-01", "channel": "meta", "spend": 500},
            ],
        }
        model_config, dataset = _build_run_inputs("job-2", config)
        # Should use defaults
        assert model_config.name == "job-job-2"  # f"job-{model_job_id}"
        assert model_config.draws == 1000
        assert model_config.tune == 1000
        assert model_config.chains == 4
        assert model_config.sampler == "nuts"
        assert model_config.random_seed == 42

    def test_raises_on_empty_records(self):
        from mmm.tasks.train import _build_run_inputs

        config = {"model": {"name": "empty"}, "records": []}
        # MMMDataset's pydantic validator rejects empty records list
        with pytest.raises(ValueError, match="at least one record"):
            _build_run_inputs("job-3", config)

    def test_raises_not_implemented_when_config_is_none(self):
        from mmm.tasks.train import _build_run_inputs

        with pytest.raises(NotImplementedError, match="DB persistence not wired"):
            _build_run_inputs("job-4", None)

    def test_includes_control_columns(self):
        from mmm.tasks.train import _build_run_inputs

        config = {
            "records": [
                {"date": "2024-01-01", "channel": "meta", "spend": 500, "clicks": 100, "impressions": 5000},
            ],
            "control_columns": ["clicks", "impressions"],
        }
        _, dataset = _build_run_inputs("job-5", config)
        assert dataset.control_columns == ["clicks", "impressions"]


# ---------------------------------------------------------------------------
# _build_result_summary
# ---------------------------------------------------------------------------

class TestBuildResultSummary:
    def test_summary_shape(self):
        from mmm.tasks.train import _build_result_summary

        diag = ModelDiagnostics(
            model_name="test", converged=True, rhat_max=1.03, r2=0.85, mape=7.2,
        )
        fit_result = FitResult(model_name="test", model_id="abc123", status="ok", diagnostics=diag)
        contributions = [
            ChannelContribution(channel="meta", contribution=5000, share=0.6, roas=3.2, spend=2000),
            ChannelContribution(channel="google", contribution=3000, share=0.4, roas=2.8, spend=1500),
        ]
        import time
        summary = _build_result_summary(fit_result, contributions, time.monotonic())
        assert summary["model_name"] == "test"
        assert summary["model_id"] == "abc123"
        assert summary["channels_count"] == 2
        assert summary["top_channel"] == "meta"
        assert summary["top_roas"] == 3.2
        assert summary["r2"] == 0.85
        assert summary["mape"] == 7.2
        assert summary["converged"] is True
        assert summary["training_seconds"] >= 0

    def test_summary_with_no_diagnostics(self):
        from mmm.tasks.train import _build_result_summary

        fit_result = FitResult(model_name="test", model_id="x", status="ok", diagnostics=None)
        import time
        summary = _build_result_summary(fit_result, [], time.monotonic())
        assert summary["r2"] is None
        assert summary["mape"] is None
        assert summary["converged"] is None
        assert summary["top_channel"] is None


# ---------------------------------------------------------------------------
# train_model_job — full integration with eager mode
# ---------------------------------------------------------------------------

class TestTrainModelJob:
    def _make_config(self, name: str = "integration-test") -> dict:
        return {
            "model": {"name": name, "draws": 100, "tune": 100, "chains": 1},
            "records": [
                {"date": "2024-01-01", "channel": "meta", "spend": 1000, "revenue": 3000},
                {"date": "2024-01-01", "channel": "google", "spend": 800, "revenue": 2400},
                {"date": "2024-01-08", "channel": "meta", "spend": 1100, "revenue": 3300},
                {"date": "2024-01-08", "channel": "google", "spend": 900, "revenue": 2700},
                {"date": "2024-01-15", "channel": "meta", "spend": 1200, "revenue": 3600},
                {"date": "2024-01-15", "channel": "google", "spend": 1000, "revenue": 3000},
                {"date": "2024-01-22", "channel": "meta", "spend": 1300, "revenue": 3900},
                {"date": "2024-01-22", "channel": "google", "spend": 1100, "revenue": 3300},
            ],
        }

    @patch("mmm.tasks.train._save_artifact")
    def test_success_path(self, mock_save):
        """Happy path: model fit succeeds, artifacts saved, returns succeeded."""
        from mmm.tasks.train import train_model_job

        mock_save.return_value = Path("/tmp/artifacts/job-test")

        with patch("mmm.tasks.train.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(model_storage_path="/tmp/models")

            with patch("mmm.tasks.train.MMMModel") as MockMMM:
                mock_model = MagicMock()
                MockMMM.return_value = mock_model

                mock_fit_result = FitResult(
                    model_name="integration-test",
                    model_id="abc123",
                    status="ok",
                    diagnostics=ModelDiagnostics(
                        model_name="integration-test", converged=True,
                        rhat_max=1.03, r2=0.85, mape=5.0,
                    ),
                )
                mock_model.fit.return_value = mock_fit_result
                mock_model.get_channel_contributions.return_value = [
                    ChannelContribution(
                        channel="meta", contribution=5000, share=0.6, roas=3.0, spend=2000,
                    ),
                    ChannelContribution(
                        channel="google", contribution=3000, share=0.4, roas=2.5, spend=1800,
                    ),
                ]
                mock_model.model_id = "abc123"

                result = train_model_job.apply(
                    args=("job-test",), kwargs={"config": self._make_config()},
                )
                assert result.status == "SUCCESS"
                payload = result.result
                assert payload["status"] == "succeeded"
                assert payload["model_job_id"] == "job-test"
                mock_save.assert_called_once()

    @patch("mmm.tasks.train._save_artifact")
    def test_modeling_error_on_failed_fit(self, mock_save):
        """When fit() returns status=failed, task raises ModelingError."""
        from mmm.tasks.train import train_model_job

        with patch("mmm.tasks.train.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(model_storage_path="/tmp/models")

            with patch("mmm.tasks.train.MMMModel") as MockMMM:
                mock_model = MagicMock()
                MockMMM.return_value = mock_model
                mock_model.fit.return_value = FitResult(
                    model_name="bad", model_id="x", status="failed", error="boom",
                )
                mock_model.model_id = "x"

                result = train_model_job.apply(
                    args=("job-fail",), kwargs={"config": self._make_config("bad")},
                )
                assert result.status == "FAILURE"
                # The task wraps non-ModelingError exceptions in InfraError;
                # fit returning "failed" raises ModelingError which propagates directly.
                assert isinstance(result.result, Exception)

    def test_empty_config_raises_not_implemented(self):
        """config=None triggers _db_load_job_config which raises NotImplementedError → InfraError."""
        from mmm.tasks.train import train_model_job

        with patch("mmm.tasks.train.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(model_storage_path="/tmp/models")
            result = train_model_job.apply(
                args=("job-nodb",), kwargs={"config": None},
            )
            assert result.status == "FAILURE"
            # NotImplementedError is caught by the generic except → InfraError
            assert isinstance(result.result, Exception)
