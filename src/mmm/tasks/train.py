"""Celery task: background MMM model training.

Orchestrates the full lifecycle of a single training run:

    1. Load job config + training records (from disk, posted by the API)
    2. Build ``ModelConfig`` + ``MMMDataset``
    3. Run ``MMMModel.fit(dataset)``
    4. Persist the artifact to ``model_storage_path/{job_id}``
    5. Write results back to the ``model_jobs`` row + ``channel_results``

All persistence now goes through the SQLAlchemy repository (``mmm.db.repo``),
so results survive restarts and are multi-tenant scoped.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded

from mmm.config import get_settings
from mmm.core.engine import MMMModel
from mmm.models.schemas import (
    ChannelContribution,
    MediaRecord,
    MMMDataset,
    ModelConfig,
)
from mmm.worker import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------
class ModelingError(RuntimeError):
    """Raised when the MMM fit routine signals a failure (not retried)."""


class InfraError(RuntimeError):
    """Transient infrastructure failure (DB timeout, storage unreachable)."""


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
    _timer_start = time.monotonic()
    _run_id = uuid.uuid4().hex[:8]
    logger.info("[train:%s] job=%s — starting", _run_id, model_job_id)

    # Import the DB layer lazily so importing the task module never touches
    # the event loop / DB at import time (important under Celery fork).
    from mmm.db.session import close_db, init_db

    async def _run() -> dict[str, Any]:
        await init_db()
        try:
            model_config, dataset = await _build_run_inputs(model_job_id, config)

            logger.info(
                "[train:%s] config=%s channels=%d records=%d",
                _run_id, model_config.name, len(dataset.channels), len(dataset.records),
            )

            model = MMMModel(config=model_config)
            await _db_mark_running(model_job_id)
            fit_result = model.fit(dataset)

            if fit_result.status != "ok":
                await _db_mark_failed(model_job_id, str(fit_result.error or "fit returned status=failed"))
                raise ModelingError(fit_result.error or "model fit returned status=failed")

            artifact_dir = _save_artifact(model, model_job_id, model_config)
            artifact_key = artifact_dir.as_posix()

            contributions = model.get_channel_contributions()
            summary = _build_result_summary(fit_result, contributions, _timer_start)

            await _db_mark_succeeded(model_job_id, artifact_key=artifact_key, result_summary=summary)
            await _db_write_channel_results(model_job_id, model_config.name, contributions)

            elapsed = time.monotonic() - _timer_start
            logger.info(
                "[train:%s] job=%s — succeeded in %.1fs, artifact=%s",
                _run_id, model_job_id, elapsed, artifact_key,
            )
            return {"model_job_id": model_job_id, "status": "succeeded", "artifact_key": artifact_key}
        except (ModelingError, SoftTimeLimitExceeded):
            elapsed = time.monotonic() - _timer_start
            logger.exception("[train:%s] job=%s — failed after %.1fs", _run_id, model_job_id, elapsed)
            await _db_mark_failed(model_job_id, f"training failed after {elapsed:.0f}s")
            raise
        except Exception as exc:
            elapsed = time.monotonic() - _timer_start
            logger.exception("[train:%s] job=%s — failed after %.1fs", _run_id, model_job_id, elapsed)
            await _db_mark_failed(model_job_id, str(exc))
            raise InfraError(str(exc)) from exc
        finally:
            await close_db()

    # Celery tasks run on a worker thread; run the coroutine to completion.
    import asyncio

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------
def _save_artifact(model: MMMModel, model_job_id: str, model_config: ModelConfig) -> Path:
    settings = get_settings()
    job_dir = Path(settings.model_storage_path) / model_job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    model.save(job_dir)

    try:
        import pymc_marketing

        pm_version = getattr(pymc_marketing, "__version__", "unknown")
    except ImportError:
        pm_version = "not-installed"

    metadata = {
        "model_job_id": model_job_id,
        "model_config": model_config.model_dump(mode="json"),
        "model_id": model.model_id,
        "packages": {"pymc_marketing": pm_version},
        "random_seed": model_config.random_seed,
        "created_at": datetime.now(UTC).isoformat(),
    }
    (job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return job_dir


def _build_result_summary(fit_result, contributions: list[ChannelContribution], _timer_start: float) -> dict[str, Any]:
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
async def _build_run_inputs(model_job_id: str, config: dict[str, Any] | None):
    if config is None:
        config = await _db_load_job_config(model_job_id)

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

    raw_records = config.get("records", [])
    # Fall back to on-disk training input posted by the API.
    if not raw_records:
        raw_records = _load_training_input(model_job_id)

    control_columns = config.get("control_columns", [])
    dataset = MMMDataset(
        records=[MediaRecord(**r) for r in raw_records],
        control_columns=control_columns,
    )
    if not dataset.records:
        raise ModelingError("training records list is empty")
    return model_config, dataset


def _load_training_input(model_job_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    path = Path(settings.model_storage_path) / model_job_id / "training_input.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("records", [])


# ---------------------------------------------------------------------------
# Database persistence (now real)
# ---------------------------------------------------------------------------
async def _db_mark_running(model_job_id: str) -> None:
    from mmm.db import repo
    from mmm.db.session import init_db

    await init_db()
    await repo.update_model_job(model_job_id, status="running")


async def _db_mark_succeeded(
    model_job_id: str,
    *,
    artifact_key: str,
    result_summary: dict[str, Any],
) -> None:
    from mmm.db import repo

    await repo.update_model_job(
        model_job_id,
        status="succeeded",
        artifact_key=artifact_key,
        result_summary=result_summary,
        finished_at=datetime.now(UTC),
    )


async def _db_mark_failed(model_job_id: str, error_message: str) -> None:
    from mmm.db import repo

    await repo.update_model_job(
        model_job_id,
        status="failed",
        error=error_message,
        finished_at=datetime.now(UTC),
    )


async def _db_write_channel_results(
    model_job_id: str,
    model_name: str,
    contributions: list[ChannelContribution],
) -> None:
    from mmm.db import repo

    job = await repo.get_model_job(model_job_id)
    if job is None:
        logger.warning("job %s not found; skipping channel results", model_job_id)
        return
    if contributions:
        await repo.add_channel_results(
            job_id=model_job_id,
            organization_id=job.organization_id,
            client_id=job.client_id,
            results=[c.model_dump() for c in contributions],
        )


async def _db_load_job_config(model_job_id: str) -> dict[str, Any]:
    """Load config from the ``model_jobs.config_json`` column."""
    from mmm.db import repo
    from mmm.db.session import init_db

    await init_db()
    job = await repo.get_model_job(model_job_id)
    if job is None:
        raise InfraError(f"model job {model_job_id} not found")
    cfg = json.loads(job.config_json) if job.config_json else {}
    records = _load_training_input(model_job_id)
    return {"model": cfg.get("model", {}), "records": records}
