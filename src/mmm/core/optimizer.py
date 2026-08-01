"""Budget allocation optimizer — scipy-based fallback + pymc wrapper."""
from __future__ import annotations
import logging
import numpy as np
from scipy.optimize import minimize
from mmm.models.schemas import (
    Allocation, AllocationResult, BudgetConstraints, ChannelContribution,
)

logger = logging.getLogger(__name__)


def allocate_budget_scipy(
    model,  # MMMModel instance
    total_budget: float,
    *,
    constraints: BudgetConstraints | None = None,
) -> AllocationResult:
    """Maximize expected revenue via response curves under budget constraints."""
    contributions = model.get_channel_contributions()
    channels = [c.channel for c in contributions]
    n = len(channels)
    if n == 0:
        return AllocationResult(total_budget=total_budget, allocations=[], expected_total_revenue=0)

    # Estimate per-channel elasticity from historical ROAS.
    # revenue_i ≈ spend_i * roas_i * (1 - (spend_i / (sat_i + spend_i)) )  # Hill-like curve
    roas = np.array([c.roas for c in contributions])
    spend = np.array([c.spend for c in contributions])
    # Saturation point estimate: where marginal ROAS = 50% of current ROAS
    sat = np.maximum(spend * 3, total_budget / n * 2)  # heuristic

    def neg_revenue(x: np.ndarray) -> float:
        # x = [budget_i] per channel. Hill function response.
        return -np.sum(roas * x * (1 - x / (sat + x)))

    bounds = []
    floors = []
    for ch in channels:
        lo_f = constraints.channel_floors.get(ch, 0) if constraints else 0
        floors.append(lo_f)
        lo = max(lo_f, total_budget * (constraints.min_per_channel_pct if constraints else 0))
        hi = total_budget * (constraints.max_per_channel_pct if constraints else 1.0)
        if constraints and ch in constraints.channel_bounds:
            lo, hi = constraints.channel_bounds[ch]
        bounds.append((lo, hi))

    # Ensure total feasible
    if sum(b[0] for b in bounds) > total_budget:
        logger.warning("floor constraints exceed total budget; relaxing floors")
        scale = total_budget / sum(b[0] for b in bounds) * 0.95
        bounds = [(b[0] * scale, b[1]) for b in bounds]

    cons = [{"type": "eq", "fun": lambda x: np.sum(x) - total_budget}]
    x0 = np.array([(b[0] + b[1]) / 2 for b in bounds])
    x0 = x0 / x0.sum() * total_budget

    result = minimize(neg_revenue, x0, method="SLSQP", bounds=bounds, constraints=cons)
    allocs_np = np.maximum(result.x, 0)
    total_check = allocs_np.sum()
    if total_check > 0:
        allocs_np = allocs_np / total_check * total_budget

    allocations: list[Allocation] = []
    for i, ch in enumerate(channels):
        share = allocs_np[i] / total_budget if total_budget else 0
        expected_rev = float(roas[i] * allocs_np[i] * (1 - allocs_np[i] / (sat[i] + allocs_np[i])))
        allocations.append(Allocation(
            channel=ch, allocated_budget=float(allocs_np[i]),
            share=float(share), expected_revenue=max(expected_rev, 0),
        ))
    total_rev = sum(a.expected_revenue for a in allocations)
    return AllocationResult(total_budget=total_budget, allocations=allocations, expected_total_revenue=total_rev)
