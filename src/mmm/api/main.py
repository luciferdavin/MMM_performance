"""FastAPI application for the MMM Platform API."""
from __future__ import annotations
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from mmm.core.engine import MMMModel
from mmm.core.config import build_model_config
from mmm.models.schemas import (
    AllocationResult, BudgetConstraints, FitResult, MMMDataset, ModelConfig,
    ChannelContribution, Insight,
)

app = FastAPI(title="MMM Platform API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/models/train", response_model=FitResult)
def train_model(config: ModelConfig, dataset: MMMDataset) -> FitResult:
    model = MMMModel(config)
    return model.fit(dataset)


@app.post("/models/allocate", response_model=AllocationResult)
def allocate(model_id: str, constraints: BudgetConstraints) -> AllocationResult:
    raise HTTPException(501, "Persistent model store not wired yet; use CLI locally")
