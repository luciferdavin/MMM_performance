"""Celery task: background MMM model training.

Orchestrates the full lifecycle of a single training run:

    1. Load job config (from DB or passed JSON)
    2. Build ``ModelConfig`` + ``MMMDataset``
    3. Run ``MMMModel.fit(dataset)``
    4. Persist artifact + channel contributions
    5. Update ``model_jobs`` row status

DB writes are currently no-op stubs.  Wire them to SQLAlchemy or Supabase
once the persistence layer is ready (see ``_db_*`` helpers at the bottom).

See ``docs/02-trd.md`` §8.3 for the training lifecycle and §11.3 for task
timeouts and retry semantics.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded

from mmm.config import get_settings
from mmm.core.engine import MMMModel
from mmm.models.schemas import (
    ChannelContribution,
    MediaRecord,
    ModelConfig,
    MMMDataset,
)
from mmm.worker import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------

class ModelingError(RuntimeError):
    """Raised when the MMM fit routine signals a failure.

    NOT retried — the input data or configuration is bad and retrying
    the identical request would fail the same way.
    """


class InfraError(RuntimeError):
    """Transient infrastructure failure (DB timeout, storage unreachable).

    Retried once per ``docs/02-trd.md`` §11.3.
    """


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="mmm.tasks.train.train_model_job",
    acks_late=True,
    autoretry_for=(InfraError, SoftTimeLimitExceeded),
    retry_backoff=True,
    retry_kwargs={"max_retries": 1},
)
def train_model_job(
    self: Any,
    model_job_id: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train a Bayesian MMM model for *model_job_id*.

    Parameters
    ----------
    model_job_id:
        Primary key of the ``model_jobs`` row.
    config:
        Optional JSON-serialisable config dict.  Must contain at minimum:

        .. code-block:: json

            {
                "model": { "name": "q3-mix", "draws": 1000, ... },
                "records": [ { "date": "...", "channel": "meta", "spend": 1200, ... }, ... ]
            }

        When the DB persistence layer is wired the task will fall back to
        reading ``model_jobs.config``; this argument is a convenience for
        testing and development.

    Returns
    -------
    dict
        Minimal result payload — the full diagnostics and channel
        contributions live in the database.
    """
    _timer_start = time.monotonic()
    _run_id = uuid.uuid4().hex[:8]
    logger.info("[train:%s] job=%s — starting", _run_id, model_job_id)

    # -- progress: mark running (started_at) --------------------------------
    _db_mark_running(model_job_id)

    try:
        # 1. Build run inputs ------------------------------------------------
        model_config, dataset = _build_run_inputs(model_job_id, config)

        logger.info(
            "[train:%s] config=%s channels=%d records=%d",
            _run_id,
            model_config.name,
            len(dataset.channels),
            len(dataset.records),
        )

        # 2. Fit model -------------------------------------------------------
        model = MMMModel(config=model_config)
        fit_result = model.fit(dataset)

        if fit_result.status != "ok":
            raise ModelingError(fit_result.error or "model fit returned status=failed")

        # 3. Save artifact ---------------------------------------------------
        artifact_dir = _save_artifact(model, model_job_id, model_config)
        artifact_key = artifact_dir.as_posix()

        contributions = model.get_channel_contributions()
        summary = _build_result_summary(fit_result, contributions, _timer_start)

        # 4. Persist results -------------------------------------------------
        _db_mark_succeeded(model_job_id, artifact_key=artifact_key, result_summary=summary)
        _db_write_channel_results(model_job_id, model_config.name, contributions)

        elapsed = time.monotonic() - _timer_start
        logger.info(
            "[train:%s] job=%s — succeeded in %.1fs, artifact=%s",
            _run_id, model_job_id, elapsed, artifact_key,
        )
        return {"model_job_id": model_job_id, "status": "succeeded", "artifact_key": artifact_key}

    except (ModelingError, SoftTimeLimitExceeded):
        elapsed = time.monotonic() - _timer_start
        logger.exception("[train:%s] job=%s — failed after %.1fs", _run_id, model_job_id, elapsed)
        _db_mark_failed(model_job_id, f"soft-time-limit-exceeded after {elapsed:.0f}s")
        raise

    except Exception as exc:
        elapsed = time.monotonic() - _timer_start
        logger.exception("[train:%s] job=%s — failed after %.1fs", _run_id, model_job_id, elapsed)
        _db_mark_failed(model_job_id, str(exc))
        raise InfraError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------

def _save_artifact(model: MMMModel, model_job_id: str, model_config: ModelConfig) -> Path:
    """Persist the fitted model to disk and write a metadata sidecar.

    Storage layout::

        {MODEL_STORAGE_PATH}/{model_job_id}/
            model.json       — PyMC-Marketing serialised weights
            fit_data.pkl     — training DataFrame
            channels.pkl     — list[str] of channel column names
            metadata.json    — provenance (config, packages, timestamp)

    Returns the job artifact directory (absolute path).
    """
    settings = get_settings()
    job_dir = Path(settings.model_storage_path) / model_job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    model.save(job_dir)

    # Write provenance metadata (docs/02-trd.md §10.3)
    try:
        import pymc_marketing  # noqa: F811 — lazy to avoid import at module level
        pm_version = getattr(pymc_marketing, "__version__", "unknown")
    except ImportError:
        pm_version = "not-installed"

    try:
        import pymc  # noqa: F811
        pm_core_version = getattr(pymc, "__version__", "unknown")
    except ImportError:
        pm_core_version = "not-installed"

    metadata = {
        "model_job_id": model_job_id,
        "model_config": model_config.model_dump(mode="json"),
        "model_id": model.model_id,
        "packages": {
            "pymc_marketing": pm_version,
            "pymc": pm_core_version,
        },
        "random_seed": model_config.random_seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = job_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return job_dir


def _build_result_summary(fit_result: Any, contributions: list[ChannelContribution], _timer_start: float) -> dict[str, Any]:
    """Build a lightweight summary for ``model_jobs.result_summary``."""
    elapsed = time.monotonic() - _timer_start
    diag = fit_result.diagnostics
    return {
        "model_name": fit_result.model_name,
        "model_id": fit_result.model_id,
        "training_seconds": round(elapsed, 1),
        "channels_count": len(contributions),
        "r2": round(diag.r2, 4) if diag else None,
        "mape": round(diag.mape, 4) if diag else None,
        "rhat_max": round(diag.rhat_max, 4) if diag else None,
        "converged": diag.converged if diag else None,
        "top_channel": contributions[0].channel if contributions else None,
        "top_roas": round(contributions[0].roas, 4) if contributions else None,
    }


# ---------------------------------------------------------------------------
# Input building
# ---------------------------------------------------------------------------

def _build_run_inputs(
    model_job_id: str,
    config: dict[str, Any] | None,
) -> tuple[ModelConfig, MMMDataset]:
    """Resolve run configuration and build the training objects.

    Priority order:
        1. Explicit *config* dict (for testing / API-v1 without DB)
        2. DB load via ``model_jobs.config`` (TODO: wire persistence)
    """
    if config is None:
        config = _db_load_job_config(model_job_id)   # TODO: impl + remove noqa

    # Build ModelConfig (safe defaults for every optional field)
    mc = config.get("model", {})
    model_config = ModelConfig(
        name=mc.get("name", f"job-{model_job_id}"),
        target_column=mc.get("target_column", "revenue"),
        granularity=mc.get("granularity", "week"),
        adstock_max_lag=mc.get("adstock_max_lag", 8),
        saturation_beta=mc.get("saturation_beta", []),
        adstock_first=mc.get("adstock_first", True),
        sampler=mc.get("sampler", "nuts"),
        draws=mc.get("draws", 1000),
        tune=mc.get("tune", 1000),
        chains=mc.get("chains", 4),
        random_seed=mc.get("random_seed", 42),
    )

    # Build MMMDataset from raw record dicts
    raw_records = config.get("records", [])
    control_columns = config.get("control_columns", [])

    dataset = MMMDataset(
        records=[MediaRecord(**r) for r in raw_records],
        control_columns=control_columns,
    )

    if not dataset.records:
        raise ModelingError("training records list is empty")

    return model_config, dataset


# ---------------------------------------------------------------------------
# Database / persistence stubs  (TODO: wire to SQLAlchemy / Supabase)
#
# All functions below are best-effort no-ops.  They log warnings so the
# task is usable in dev mode without a database, while clearly documenting
# the exact SQL operations required when persistence is connected.
# ---------------------------------------------------------------------------

def _db_mark_running(model_job_id: str) -> None:
    """TODO: UPDATE model_jobs SET status='running', started_at=now() WHERE id=:id

    Called at the very start of the task, before any compute.
    """
    logger.warning("DB stub: skipping _db_mark_running for job %s", model_job_id)


def _db_mark_succeeded(
    model_job_id: str,
    *,
    artifact_key: str,
    result_summary: dict[str, Any],
) -> None:
    """TODO: UPDATE model_jobs
    SET    status='succeeded',
           artifact_key=:artifact_key,
           result_summary=:result_summary,
           diagnostics=:diagnostics,
           finished_at=now()
    WHERE  id=:id
    """
    logger.warning(
        "DB stub: skipping _db_mark_succeeded for job %s (artifact=%s)",
        model_job_id,
        artifact_key,
    )


def _db_mark_failed(model_job_id: str, error_message: str) -> None:
    """TODO: UPDATE model_jobs
    SET    status='failed',
           error=:error_message,
           finished_at=now()
    WHERE  id=:id
    """
    logger.warning(
        "DB stub: skipping _db_mark_failed for job %s (error=%s)",
        model_job_id,
        error_message,
    )


def _db_write_channel_results(
    model_job_id: str,
    model_name: str,
    contributions: list[ChannelContribution],
) -> None:
    """TODO: INSERT INTO channel_results
    (id, organization_id, client_id, model_job_id, channel,
     contribution, share, roas, spend, created_at)
    VALUES ...

    Requires ``organization_id`` and ``client_id`` which should be loaded
    from the ``model_jobs`` row (or passed via the config dict for dev mode).
    """
    logger.warning(
        "DB stub: skipping _db_write_channel_results for job %s — %d channels",
        model_job_id,
        len(contributions),
    )


def _db_load_job_config(model_job_id: str) -> dict[str, Any]:
    """TODO: SELECT config FROM model_jobs WHERE id=:model_job_id

    Returns the JSONB ``config`` column, which must contain the ``model``
    and ``records`` keys expected by :func:`_build_run_inputs`.

    Raises NotImplementedError until the DB persistence layer is wired.
    """
    raise NotImplementedError(
        f"DB persistence not wired — cannot load config for job {model_job_id}. "
        "Pass the config dict explicitly when calling the task."
    )
