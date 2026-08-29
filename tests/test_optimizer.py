"""Tests for budget optimizer."""
import pandas as pd

from mmm.core.optimizer import allocate_budget_scipy
from mmm.models.schemas import ChannelContribution


class FakeModel:
    """Lightweight mock for MMMModel to test optimizer."""
    def __init__(self, contributions):
        self._contributions = contributions
        self._channel_columns = [c.channel for c in contributions]
        self._fit_data = pd.DataFrame({c.channel: [c.spend] for c in contributions})

    def get_channel_contributions(self):
        return self._contributions


CONTRIBUTIONS = [
    ChannelContribution(channel="meta", contribution=5000, share=0.4, roas=3.5, spend=2000),
    ChannelContribution(channel="google_ads", contribution=4000, share=0.3, roas=3.0, spend=1800),
    ChannelContribution(channel="tiktok", contribution=3000, share=0.2, roas=2.5, spend=1200),
    ChannelContribution(channel="tv", contribution=1500, share=0.1, roas=1.2, spend=1000),
]

def test_allocation_sums_to_budget():
    model = FakeModel(CONTRIBUTIONS)
    result = allocate_budget_scipy(model, 10000)
    total = sum(a.allocated_budget for a in result.allocations)
    assert abs(total - 10000) < 1.0

def test_allocation_has_all_channels():
    model = FakeModel(CONTRIBUTIONS)
    result = allocate_budget_scipy(model, 5000)
    allocated_channels = {a.channel for a in result.allocations}
    assert allocated_channels == {"meta", "google_ads", "tiktok", "tv"}

def test_higher_roas_gets_more_budget():
    model = FakeModel(CONTRIBUTIONS)
    result = allocate_budget_scipy(model, 10000)
    by_roas = sorted(result.allocations, key=lambda a: (a.expected_revenue / a.allocated_budget if a.allocated_budget > 0 else 0), reverse=True)
    # meta (ROAS 3.5) should get more than tv (ROAS 1.2)
    meta_alloc = next(a for a in result.allocations if a.channel == "meta")
    tv_alloc = next(a for a in result.allocations if a.channel == "tv")
    assert meta_alloc.allocated_budget > tv_alloc.allocated_budget

def test_is_feasible():
    model = FakeModel(CONTRIBUTIONS)
    result = allocate_budget_scipy(model, 10000)
    assert result.is_feasible
