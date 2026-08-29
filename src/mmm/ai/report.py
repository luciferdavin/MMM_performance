"""Generate structured reports from MMM results."""
from __future__ import annotations

import logging

from mmm.ai.prompts import REPORT_SYSTEM, REPORT_USER_TEMPLATE
from mmm.ai.providers import LLMProvider, get_llm_provider
from mmm.models.schemas import AllocationResult, ChannelContribution

logger = logging.getLogger(__name__)

def generate_report(
    contributions: list[ChannelContribution],
    allocation: AllocationResult,
    r2: float,
    mape: float,
    client_name: str = "Client",
    provider: LLMProvider | None = None,
) -> str:
    provider = provider or get_llm_provider()
    contrib_data = "\n".join(
        f"- {c.channel}: spend=${c.spend:,.0f}, contribution={c.share:.1%}, ROAS={c.roas:.2f}x"
        for c in contributions
    )
    alloc_data = "\n".join(
        f"- {a.channel}: allocated ${a.allocated_budget:,.0f} ({a.share:.1%})"
        for a in allocation.allocations
    )
    user_prompt = REPORT_USER_TEMPLATE.format(
        client_name=client_name, channel_data=contrib_data, allocation_data=alloc_data,
        r2=r2, mape=mape, total_budget=allocation.total_budget,
        expected_revenue=allocation.expected_total_revenue,
    )
    try:
        return provider.chat(REPORT_SYSTEM, user_prompt)
    except Exception as e:
        logger.warning("LLM report generation failed: %s", e)
        return _fallback_report(contributions, allocation, client_name)

def _fallback_report(contributions, allocation, client_name):
    lines = [f"# MMM Report: {client_name}\n", "## Channel Contributions\n"]
    for c in contributions:
        lines.append(f"- **{c.channel}**: ROAS {c.roas:.2f}x, share {c.share:.1%}")
    lines.append(f"\n## Budget Allocation (total: ${allocation.total_budget:,.0f})\n")
    for a in allocation.allocations:
        lines.append(f"- **{a.channel}**: ${a.allocated_budget:,.0f} ({a.share:.1%})")
    lines.append(f"\nExpected revenue: ${allocation.expected_total_revenue:,.0f}")
    return "\n".join(lines)
