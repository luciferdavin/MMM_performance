"""Tests for Pydantic schemas."""
import pytest
from mmm.models.schemas import (
    AllocationResult, Allocation, BudgetConstraints, ChannelContribution,
    FitResult, Insight, MediaRecord, MMMDataset, ModelConfig,
)

def test_media_record_validation():
    r = MediaRecord(date="2024-01-01", channel="meta", spend=100)
    assert r.impressions == 0
    assert r.revenue == 0.0

def test_media_record_negative_spend_rejected():
    with pytest.raises(Exception):
        MediaRecord(date="2024-01-01", channel="meta", spend=-10)

def test_mmm_dataset_channels():
    records = [
        MediaRecord(date="2024-01-01", channel="meta", spend=100),
        MediaRecord(date="2024-01-01", channel="google", spend=200),
    ]
    ds = MMMDataset(records=records)
    assert set(ds.channels) == {"meta", "google"}

def test_allocation_feasibility():
    result = AllocationResult(
        total_budget=10000,
        allocations=[
            Allocation(channel="meta", allocated_budget=5000, share=0.5, expected_revenue=15000),
            Allocation(channel="google", allocated_budget=5000, share=0.5, expected_revenue=12000),
        ],
        expected_total_revenue=27000,
    )
    assert result.is_feasible

def test_allocation_infeasible():
    result = AllocationResult(
        total_budget=10000,
        allocations=[Allocation(channel="meta", allocated_budget=8000, share=0.8, expected_revenue=20000)],
        expected_total_revenue=20000,
    )
    assert not result.is_feasible

def test_model_config_defaults():
    config = ModelConfig(name="test_model")
    assert config.draws == 1000
    assert config.chains == 4
    assert config.sampler == "nuts"
