"""Pydantic schemas shared across the platform."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MediaRecord(BaseModel):
    """One row of normalized marketing + outcome data.

    This is the canonical schema every connector must produce.
    """

    date: datetime
    channel: str
    spend: float = Field(ge=0)
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    revenue: float = Field(default=0.0)


class MMMDataset(BaseModel):
    """A validated dataset ready for model training."""

    records: list[MediaRecord]
    control_columns: list[str] = Field(default_factory=list)

    @field_validator("records")
    @classmethod
    def _require_positive_spend(cls, records: list[MediaRecord]) -> list[MediaRecord]:
        if not records:
            raise ValueError("dataset must contain at least one record")
        return records

    @property
    def channels(self) -> list[str]:
        return sorted({r.channel for r in self.records})


class Granularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ModelConfig(BaseModel):
    """Configuration for one MMM model run.

    Production default is 4 chains / 1000 draws / 1000 tune.
    """

    name: str = "default"
    date_column: str = "date"
    target_column: str = "revenue"
    spend_column: str = "spend"
    granularity: Granularity = Granularity.WEEK
    adstock_max_lag: int = Field(default=8, ge=0)
    adstock_first: bool = True
    sampler: str = "nuts"
    draws: int = Field(default=1_000, ge=100)
    tune: int = Field(default=1_000, ge=100)
    chains: int = Field(default=4, ge=1)
    target_accept: float = Field(default=0.9, ge=0.5, le=1.0)
    forecast_days: int = Field(default=90, ge=0)
    random_seed: int = 42


class BudgetConstraints(BaseModel):
    """Constraints for budget allocation."""

    total_budget: float = Field(gt=0)
    min_per_channel_pct: float = Field(default=0.0, ge=0, lt=1.0)
    max_per_channel_pct: float = Field(default=1.0, gt=0.0, le=1.0)
    channel_bounds: dict[str, tuple[float, float]] = Field(default_factory=dict)
    channel_floors: dict[str, float] = Field(default_factory=dict)


class Allocation(BaseModel):
    channel: str
    allocated_budget: float
    share: float
    expected_revenue: float


class AllocationResult(BaseModel):
    total_budget: float
    allocations: list[Allocation]
    expected_total_revenue: float

    @property
    def is_feasible(self) -> bool:
        total = sum(a.allocated_budget for a in self.allocations)
        return abs(total - self.total_budget) <= max(self.total_budget * 0.01, 1.0)


class ChannelContribution(BaseModel):
    channel: str
    contribution: float
    share: float
    roas: float
    spend: float


class ModelDiagnostics(BaseModel):
    model_name: str
    converged: bool
    rhat_max: float
    r2: float
    mape: float
    warnings: list[str] = Field(default_factory=list)


class ForecastPoint(BaseModel):
    date: datetime
    predicted_revenue: float
    lower: float
    upper: float


class Insight(BaseModel):
    type: Literal["channel_performance", "budget_recommendation", "anomaly", "benchmark", "summary"]
    title: str
    body: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    metrics: dict[str, float] = Field(default_factory=dict)


class FitResult(BaseModel):
    model_name: str
    model_id: str
    status: Literal["ok", "failed"]
    diagnostics: ModelDiagnostics | None = None
    error: str | None = None
