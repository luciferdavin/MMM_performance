"""Prompt templates for MMM insight generation."""
from __future__ import annotations

INSIGHT_SYSTEM = """You are a marketing analytics expert. Given MMM model outputs, produce actionable business insights.
Return JSON with keys: insights (list of {type, title, body, confidence, metrics}).
Be specific with numbers. Reference channels by name. Cite data source (model_output)."""

INSIGHT_USER_TEMPLATE = """MMM model output for client "{client_name}":

Channel contributions:
{channel_data}

Budget allocation:
{allocation_data}

Diagnostics: R-squared={r2:.3f}, MAPE={mape:.1f}%

Generate 5-8 insights covering: top performing channels, underperforming channels, budget reallocation opportunities, diminishing returns warnings, and any anomalies.
Return JSON only."""

REPORT_SYSTEM = """You are a senior marketing strategist writing a client-ready MMM report.
Write in professional tone. Be specific with numbers. Structure with clear sections."""

REPORT_USER_TEMPLATE = """Write an executive summary report for {client_name} covering:
1. Overall performance summary
2. Channel-by-channel analysis
3. Budget optimization recommendations
4. Key risks and opportunities
5. Next steps

Data:
Channel contributions: {channel_data}
Budget allocation: {allocation_data}
Diagnostics: R²={r2:.3f}, MAPE={mape:.1f}%
Total budget: ${total_budget:,.0f}
Expected revenue: ${expected_revenue:,.0f}
"""
