"""Model train / allocate / contributions / insights endpoints.

Training is **dispatched as a background Celery job** (``train_model_job``).
The API immediately returns the created ``model_jobs`` row (status = queued);
the worker fits the model, saves the artifact to ``model_storage_path``, and
writes results back to the same row + ``channel_results``. Because fitted
models are serialized to disk, ``allocate`` / ``contributions`` / ``insights``
reload the artifact on demand — no in-process memory needed.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mmm.api.auth import OrgContext
from mmm.config import get_settings
from mmm.core.engine import MMMModel
from mmm.db import repo
from mmm.models.schemas import (
    AllocationResult,
    BudgetConstraints,
    ChannelContribution,
    FitResult,
    MediaRecord,
    MMMDataset,
    ModelConfig,
)
from mmm.worker import enqueue_train_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------
def _artifact_path(model_job_id: str) -> Path:
    settings = get_settings()
    return Path(settings.model_storage_path) / model_job_id


def _load_fitted_model(model_job_id: str, config: ModelConfig) -> MMMModel:
    """Load a previously-trained model from its on-disk artifact."""
    path = _artifact_path(model_job_id)
    if not (path / "model.json").exists():
        raise HTTPException(status_code=404, detail="model artifact not found; retrain first")
    return MMMModel.load(path, config)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class TrainRequest(BaseModel):
    config: ModelConfig
    records: list[MediaRecord]
    client_id: str | None = None


class AllocateRequest(BaseModel):
    total_budget: float
    channel_bounds: dict[str, tuple[float, float]] | None = None


class InsightRequest(BaseModel):
    client_name: str = "Client"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/train", response_model=dict, status_code=202)
async def train_model(body: TrainRequest, ctx: OrgContext):
    """Create a model job and dispatch background training.

    Returns the job id immediately (status=queued). Poll ``GET /models/{id}``
    or trigger ``GET /models/{id}/contributions`` once status is succeeded.
    """
    if not body.records:
        raise HTTPException(status_code=400, detail="records must be non-empty")

    dataset = MMMDataset(records=body.records)
    config_payload = body.config.model_dump_json()
    job = await repo.create_model_job(
        job_id=None,
        organization_id=ctx.organization_id,
        client_id=body.client_id,
        name=body.config.name or "unnamed",
        config_json=config_payload,
        status="queued",
    )

    # Save the raw records alongside the config so the worker can rebuild the
    # dataset without re-posting it through the queue.
    _persist_training_input(job.id, body.records)

    enqueue_train_job(model_job_id=job.id, config=body.config.model_dump(mode="json"))
    return {"model_job_id": job.id, "status": "queued", "channels": dataset.channels}


@router.post("/train-sync", response_model=FitResult)
async def train_model_sync(body: TrainRequest, ctx: OrgContext):
    """Train synchronously and return a ``FitResult`` immediately.

    Used by the onboarding / optimize flows for instant feedback. Results are
    still persisted to the ``model_jobs`` row + ``channel_results`` so they
    survive restarts (not held in process memory).
    """
    if not body.records:
        raise HTTPException(status_code=400, detail="records must be non-empty")

    dataset = MMMDataset(records=body.records)
    config_payload = body.config.model_dump_json()

    job = await repo.create_model_job(
        job_id=None,
        organization_id=ctx.organization_id,
        client_id=body.client_id,
        name=body.config.name or "unnamed",
        config_json=config_payload,
        status="running",
    )

    model = MMMModel(body.config)
    result = model.fit(dataset)
    if result.status != "ok":
        await repo.update_model_job(job.id, status="failed", error=result.error)
        return result

    artifact_dir = _save_artifact_sync(model, job.id, body.config)
    contributions = model.get_channel_contributions()
    summary = {
        "model_name": result.model_name,
        "model_id": result.model_id,
        "r2": result.diagnostics.r2 if result.diagnostics else None,
        "mape": result.diagnostics.mape if result.diagnostics else None,
        "rhat_max": result.diagnostics.rhat_max if result.diagnostics else None,
        "converged": result.diagnostics.converged if result.diagnostics else None,
    }
    await repo.update_model_job(
        job.id,
        status="succeeded",
        artifact_key=artifact_dir.as_posix(),
        result_summary=summary,
        finished_at=datetime.now(UTC),
    )
    if contributions:
        await repo.add_channel_results(
            job_id=job.id,
            organization_id=ctx.organization_id,
            client_id=body.client_id,
            results=[c.model_dump() for c in contributions],
        )
    # Attach the job id so callers can fetch persisted results later.
    result.model_id = job.id
    return result


def _save_artifact_sync(model: MMMModel, job_id: str, config: ModelConfig) -> Path:
    settings = get_settings()
    job_dir = Path(settings.model_storage_path) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    model.save(job_dir)
    metadata = {
        "model_job_id": job_id,
        "model_config": config.model_dump(mode="json"),
        "model_id": model.model_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    (job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return job_dir


def _persist_training_input(job_id: str, records: list[MediaRecord]) -> None:
    """Stash training records to disk so the Celery worker can load them.

    Keeps the queue payload small and avoids re-serializing big datasets.
    """
    path = _artifact_path(job_id)
    path.mkdir(parents=True, exist_ok=True)
    import json

    payload = {
        "records": [r.model_dump(mode="json") for r in records],
    }
    (path / "training_input.json").write_text(json.dumps(payload, default=str), encoding="utf-8")


async def _get_job_or_404(model_id: str, ctx: OrgContext):
    job = await repo.get_model_job(model_id)
    if not job or job.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="model job not found")
    return job


@router.post("/{model_id}/allocate", response_model=AllocationResult)
async def allocate(model_id: str, body: AllocateRequest, ctx: OrgContext):
    job = await _get_job_or_404(model_id, ctx)
    if job.status != "succeeded":
        raise HTTPException(status_code=409, detail=f"model is {job.status}; train first")
    config = ModelConfig.model_validate_json(job.config_json)
    model = _load_fitted_model(model_id, config)
    constraints = BudgetConstraints(total_budget=body.total_budget, channel_bounds=body.channel_bounds or {})
    result = model.allocate_budget(body.total_budget, constraints=constraints)
    # Persist the optimization
    await repo.create_budget_optimization(
        organization_id=ctx.organization_id,
        client_id=job.client_id,
        model_job_id=model_id,
        constraints=body.model_dump(),
        allocations=result.model_dump(),
        total_budget=result.total_budget,
        expected_total_revenue=result.expected_total_revenue,
        is_feasible=result.is_feasible,
    )
    return result


@router.get("/{model_id}/contributions")
async def contributions(model_id: str, ctx: OrgContext):
    job = await _get_job_or_404(model_id, ctx)
    rows = await repo.get_channel_results(model_id)
    if rows:
        return [
            ChannelContribution(
                channel=r.channel,
                contribution=r.contribution,
                share=r.share,
                roas=r.roas,
                spend=r.spend,
            ).model_dump()
            for r in rows
        ]
    # Fall back to reloading the artifact if DB rows are missing.
    if job.status != "succeeded":
        raise HTTPException(status_code=409, detail=f"model is {job.status}; train first")
    config = ModelConfig.model_validate_json(job.config_json)
    model = _load_fitted_model(model_id, config)
    return [c.model_dump() for c in model.get_channel_contributions()]


@router.post("/{model_id}/insights")
async def insights(model_id: str, body: InsightRequest, ctx: OrgContext):
    job = await _get_job_or_404(model_id, ctx)
    if job.status != "succeeded":
        raise HTTPException(status_code=409, detail=f"model is {job.status}; train first")
    config = ModelConfig.model_validate_json(job.config_json)
    model = _load_fitted_model(model_id, config)
    contribs = model.get_channel_contributions()
    diag = model._diagnostics
    try:
        from mmm.ai.insights import generate_insights

        result = generate_insights(
            contributions=contribs,
            allocation=None,
            r2=diag.r2 if diag else 0.0,
            mape=diag.mape if diag else 0.0,
            client_name=body.client_name,
        )
        # Persist insights
        for i in result:
            await repo.add_insight(
                organization_id=ctx.organization_id,
                client_id=job.client_id,
                model_job_id=model_id,
                type=i.type,
                title=i.title,
                body=i.body,
                confidence=i.confidence,
                metrics=i.metrics,
            )
        return [i.model_dump() for i in result]
    except Exception as e:  # noqa: BLE001
        logger.warning("insight generation failed: %s", e)
        return [{"title": "Insights unavailable", "body": str(e)}]


# ---------------------------------------------------------------------------
# Listing / detail
# ---------------------------------------------------------------------------
class ModelJobOut(BaseModel):
    id: str
    organization_id: str
    client_id: str | None
    name: str
    status: str
    error: str | None = None
    r2: float | None = None
    mape: float | None = None
    duration_seconds: float | None = None
    created_at: str | None = None


@router.get("", response_model=list[ModelJobOut])
async def list_model_jobs(ctx: OrgContext):
    jobs = await repo.list_model_jobs(ctx.organization_id)
    return [
        ModelJobOut(
            id=j.id,
            organization_id=j.organization_id,
            client_id=j.client_id,
            name=j.name,
            status=j.status,
            error=j.error,
            r2=_r2(j),
            mape=_mape(j),
            duration_seconds=j.duration_seconds,
            created_at=j.created_at.isoformat() if j.created_at else None,
        )
        for j in jobs
    ]


@router.get("/{model_id}", response_model=ModelJobOut)
async def get_model_job(model_id: str, ctx: OrgContext):
    job = await _get_job_or_404(model_id, ctx)
    return ModelJobOut(
        id=job.id,
        organization_id=job.organization_id,
        client_id=job.client_id,
        name=job.name,
        status=job.status,
        error=job.error,
        r2=_r2(job),
        mape=_mape(job),
        duration_seconds=job.duration_seconds,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


def _r2(job):
    if job.result_summary_json:
        import json

        try:
            return json.loads(job.result_summary_json).get("r2")
        except Exception:  # noqa: BLE001
            return None
    return None


def _mape(job):
    if job.result_summary_json:
        import json

        try:
            return json.loads(job.result_summary_json).get("mape")
        except Exception:  # noqa: BLE001
            return None
    return None
