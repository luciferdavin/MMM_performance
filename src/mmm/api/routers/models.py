"""Model train / allocate / contributions endpoints."""
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mmm.api.auth import OrganizationContext, get_org_id
from mmm.core.engine import MMMModel
from mmm.db import repo
from mmm.models.schemas import (
    ModelConfig, MMMDataset, MediaRecord, FitResult, AllocationResult,
    BudgetConstraints,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])

# In-memory model store for dev (model_id → MMMModel)
_models: dict[str, MMMModel] = {}


class TrainRequest(BaseModel):
    config: ModelConfig
    records: list[MediaRecord]


@router.post("/train", response_model=FitResult)
async def train_model(body: TrainRequest, ctx: OrganizationContext = Depends(get_org_id)):
    organization_id = ctx.organization_id
    dataset = MMMDataset(records=body.records)
    model = MMMModel(body.config)
    result = model.fit(dataset)
    if result.status == "ok":
        _models[result.model_id] = model
        # Persist model job to database
        job_id = result.model_id
        config_json = body.config.model_dump_json()
        await repo.create_model_job(
            job_id=job_id,
            organization_id=organization_id,
            client_id=None,
            model_name=body.config.name or "unnamed",
            config_json=config_json,
            status="completed",
            r2=result.diagnostics.r2 if result.diagnostics else None,
            mape=result.diagnostics.mape if result.diagnostics else None,
        )
        # Persist channel results
        contribs = model.get_channel_contributions()
        channel_results = [
            {
                "channel": c.channel,
                "contribution": c.contribution,
                "share": c.share,
                "roas": c.roas,
                "spend": c.spend,
            }
            for c in contribs
        ]
        if channel_results:
            await repo.add_channel_results(job_id, channel_results)
    return result


class AllocateRequest(BaseModel):
    total_budget: float
    channel_bounds: dict[str, tuple[float, float]] | None = None

@router.post("/{model_id}/allocate", response_model=AllocationResult)
async def allocate(model_id: str, body: AllocateRequest, ctx: OrganizationContext = Depends(get_org_id)):
    model = _models.get(model_id)
    if not model:
        raise HTTPException(404, "model not found; retrain first")
    constraints = BudgetConstraints(total_budget=body.total_budget, channel_bounds=body.channel_bounds or {})
    return model.allocate_budget(body.total_budget, constraints=constraints)


@router.get("/{model_id}/contributions")
async def contributions(model_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    model = _models.get(model_id)
    if not model:
        raise HTTPException(404, "model not found; retrain first")
    return [c.model_dump() for c in model.get_channel_contributions()]


class InsightRequest(BaseModel):
    client_name: str = "Client"

@router.post("/{model_id}/insights")
async def insights(model_id: str, body: InsightRequest, ctx: OrganizationContext = Depends(get_org_id)):
    model = _models.get(model_id)
    if not model:
        raise HTTPException(404, "model not found; retrain first")
    contribs = model.get_channel_contributions()
    diag = model._diagnostics
    try:
        from mmm.ai.insights import generate_insights
        result = generate_insights(
            contributions=contribs, allocation=None,
            r2=diag.r2 if diag else 0.0, mape=diag.mape if diag else 0.0,
            client_name=body.client_name,
        )
        return [i.model_dump() for i in result]
    except Exception as e:
        logger.warning("insight generation failed: %s", e)
        return [{"title": "Insights unavailable", "body": str(e)}]


# ---------------------------------------------------------------------------
# Model job listing endpoints (database-backed)
# ---------------------------------------------------------------------------


class ModelJobOut(BaseModel):
    id: str
    organization_id: str
    client_id: str | None
    model_name: str
    status: str
    r2: float | None
    mape: float | None


@router.get("", response_model=list[ModelJobOut])
async def list_model_jobs(ctx: OrganizationContext = Depends(get_org_id)):
    """List all model jobs for the organization."""
    organization_id = ctx.organization_id
    jobs = await repo.list_model_jobs(organization_id)
    return [
        ModelJobOut(
            id=j.id,
            organization_id=j.organization_id,
            client_id=j.client_id,
            model_name=j.model_name,
            status=j.status,
            r2=j.r2,
            mape=j.mape,
        )
        for j in jobs
    ]


@router.get("/{model_id}", response_model=ModelJobOut)
async def get_model_job(model_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    """Get a single model job by ID."""
    organization_id = ctx.organization_id
    job = await repo.get_model_job(model_id)
    if not job or job.organization_id != organization_id:
        raise HTTPException(404, "model job not found")
    return ModelJobOut(
        id=job.id,
        organization_id=job.organization_id,
        client_id=job.client_id,
        model_name=job.model_name,
        status=job.status,
        r2=job.r2,
        mape=job.mape,
    )
