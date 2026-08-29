"""Generate NL insights from trained MMM model via LLM."""
from __future__ import annotations

import logging

from mmm.ai.prompts import INSIGHT_SYSTEM, INSIGHT_USER_TEMPLATE
from mmm.ai.providers import LLMProvider, get_llm_provider
from mmm.models.schemas import AllocationResult, ChannelContribution, Insight

logger = logging.getLogger(__name__)

def generate_insights(
    contributions: list[ChannelContribution],
    allocation: AllocationResult | None,
    r2: float,
    mape: float,
    client_name: str = "Client",
    provider: LLMProvider | None = None,
) -> list[Insight]:
    provider = provider or get_llm_provider()
    contrib_data = "\n".join(
        f"  - {c.channel}: spend=${c.spend:,.0f}, contribution={c.share:.1%}, ROAS={c.roas:.2f}x"
        for c in contributions
    )
    alloc_data = "No allocation run yet"
    if allocation:
        alloc_data = "\n".join(
            f"  - {a.channel}: ${a.allocated_budget:,.0f} ({a.share:.1%})"
            for a in allocation.allocations
        )
    user_prompt = INSIGHT_USER_TEMPLATE.format(
        client_name=client_name, channel_data=contrib_data, allocation_data=alloc_data,
        r2=r2, mape=mape,
    )
    try:
        raw = provider.chat_json(INSIGHT_SYSTEM, user_prompt)
        if "_parse_error" in raw:
            return [Insight(type="summary", title="LLM Response (unparsed)", body=raw.get("raw", ""))]
        items = raw.get("insights", [])
        return [
            Insight(
                type=item.get("type", "summary"), title=item.get("title", ""),
                body=item.get("body", ""), confidence=float(item.get("confidence", 0.5)),
                metrics=item.get("metrics", {}),
            )
            for item in items
        ]
    except Exception as e:
        logger.warning("LLM insight generation failed: %s", e)
        return [Insight(type="summary", title="Insights unavailable", body=f"LLM error: {e}")]
