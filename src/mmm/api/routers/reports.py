"""Report generation endpoint with PDF export.

Training + allocation + NL report are persisted to the ``reports`` table so
results survive restarts. The PDF is rendered on demand from stored content.
"""

from __future__ import annotations

import io
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mmm.api.auth import OrgContext
from mmm.core.engine import MMMModel
from mmm.db import repo
from mmm.models.schemas import MediaRecord, MMMDataset, ModelConfig

# ---------------------------------------------------------------------------
# Chart helpers (reportlab Drawing-based, no chart library quirks)
# ---------------------------------------------------------------------------
_INDIGO = "#4F46E5"
_TEAL = "#0D9488"
_SLATE_300 = "#CBD5E1"
_SLATE_400 = "#94A3B8"
_SLATE_600 = "#475569"
_SLATE_900 = "#0F172A"

_LABEL_WIDTH = 90
_BAR_GAP = 6
_BAR_HEIGHT = 22
_CHART_PAD_LEFT = 0
_CHART_PAD_RIGHT = 8
_CHART_PAD_TOP = 20
_CHART_PAD_BOTTOM = 10
_CHART_TOTAL_WIDTH = 460


def _fmt_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _build_horizontal_bar_chart(labels, values, bar_color, title, value_fmt="currency"):
    from reportlab.graphics.shapes import Drawing, Rect, String

    n = len(labels)
    chart_height = _CHART_PAD_TOP + n * (_BAR_HEIGHT + _BAR_GAP) + _CHART_PAD_BOTTOM
    d: Drawing = Drawing(_CHART_TOTAL_WIDTH, chart_height)  # type: ignore[assignment]

    d.add(String(_CHART_PAD_LEFT, chart_height - 16, title, fontSize=10, fontName="Helvetica-Bold", fillColor=_SLATE_600))

    max_val = max(values) if values else 1
    bar_area_width = _CHART_TOTAL_WIDTH - _LABEL_WIDTH - _CHART_PAD_RIGHT

    for i, (label, value) in enumerate(zip(labels, values, strict=False)):
        y = chart_height - _CHART_PAD_TOP - (i + 1) * (_BAR_HEIGHT + _BAR_GAP) + _BAR_GAP
        d.add(String(_CHART_PAD_LEFT, y + 6, label, fontSize=8, fontName="Helvetica", fillColor=_SLATE_900))
        d.add(Rect(bar_x := _LABEL_WIDTH, y, bar_area_width, _BAR_HEIGHT, fillColor=_SLATE_300, strokeColor=None, rx=3, ry=3))
        bar_width = (value / max_val) * bar_area_width if max_val > 0 else 0
        if bar_width > 0:
            d.add(Rect(bar_x, y, bar_width, _BAR_HEIGHT, fillColor=bar_color, strokeColor=None, rx=3, ry=3))
        val_text = _fmt_currency(value) if value_fmt == "currency" else (f"{value:.1%}" if value_fmt == "percent" else str(value))
        d.add(String(bar_x + bar_width + 6, y + 6, val_text, fontSize=8, fontName="Courier", fillColor=_SLATE_600))
    return d


def _build_budget_allocation_chart(allocations):
    return _build_horizontal_bar_chart(
        [a["channel"] for a in allocations], [a["allocated_budget"] for a in allocations],
        _INDIGO, "Budget Allocation by Channel ($)", value_fmt="currency",
    )


def _build_contribution_share_chart(contributions):
    return _build_horizontal_bar_chart(
        [c["channel"] for c in contributions], [c["share"] for c in contributions],
        _TEAL, "Channel Contribution Share (%)", value_fmt="percent",
    )


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    records: list[MediaRecord]
    config: ModelConfig
    client_name: str = "Client"
    total_budget: float = 50000


@router.post("/generate", status_code=201)
async def generate_report(body: ReportRequest, ctx: OrgContext):
    """Train a model, allocate, generate an NL report, and persist it."""
    if not body.records:
        raise HTTPException(status_code=400, detail="records must be non-empty")
    dataset = MMMDataset(records=body.records)
    model = MMMModel(body.config)
    result = model.fit(dataset)
    if result.status != "ok":
        raise HTTPException(status_code=500, detail=f"model train failed: {result.error}")
    contribs = model.get_channel_contributions()
    alloc = model.allocate_budget(body.total_budget)

    from mmm.ai.report import generate_report as llm_report

    diag = model._diagnostics
    report_md = llm_report(
        contributions=contribs, allocation=alloc,
        r2=diag.r2 if diag else 0.0, mape=diag.mape if diag else 0.0,
        client_name=body.client_name,
    )

    content = {
        "client_name": body.client_name,
        "markdown": report_md,
        "contributions": [c.model_dump() for c in contribs],
        "allocation": alloc.model_dump(),
        "r2": diag.r2 if diag else None,
        "mape": diag.mape if diag else None,
    }
    report = await repo.create_report(
        organization_id=ctx.organization_id,
        client_id=None,
        model_job_id=None,
        client_name=body.client_name,
        content=content,
    )
    return {"report_id": report.id, "markdown": report_md}


@router.get("")
async def list_reports(ctx: OrgContext):
    reports = await repo.list_reports(ctx.organization_id)
    return [
        {"report_id": r.id, "client_name": r.client_name, "created_at": r.created_at.isoformat()}
        for r in reports
    ]


@router.get("/{report_id}")
async def get_report(report_id: str, ctx: OrgContext):
    report = await repo.get_report(report_id)
    if not report or report.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="report not found")
    import json

    return {"report_id": report.id, "client_name": report.client_name, **json.loads(report.content_json)}


@router.get("/{report_id}/pdf")
async def download_pdf(report_id: str, ctx: OrgContext):
    report = await repo.get_report(report_id)
    if not report or report.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="report not found")
    import json

    r = json.loads(report.content_json)
    client_name = report.client_name or "Client"
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=12)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6)

        story = [Paragraph(f"MMM Report — {client_name}", title_style), Spacer(1, 12)]
        story.append(Paragraph("Channel Contributions", h2_style))
        contribs_data = r.get("contributions", [])
        if contribs_data:
            story.append(_build_contribution_share_chart(contribs_data))
            story.append(Spacer(1, 12))
        for c in contribs_data:
            story.append(Paragraph(
                f"<b>{c['channel']}</b>: spend ${c['spend']:,.0f} · ROAS {c['roas']:.2f}x · share {c['share']:.1%}",
                styles["Normal"],
            ))
            story.append(Spacer(1, 4))

        alloc = r.get("allocation", {})
        story.append(Paragraph("Budget Allocation", h2_style))
        alloc_data = alloc.get("allocations", [])
        if alloc_data:
            story.append(_build_budget_allocation_chart(alloc_data))
            story.append(Spacer(1, 12))
        for a in alloc_data:
            story.append(Paragraph(f"<b>{a['channel']}</b>: ${a['allocated_budget']:,.0f} ({a['share']:.1%})", styles["Normal"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("AI Analysis", h2_style))
        for para in r["markdown"].split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), styles["Normal"]))
                story.append(Spacer(1, 6))

        doc.build(story)
        buf.seek(0)
        filename = f"{client_name.lower().replace(' ', '-')}-mmm-report.pdf"
        return StreamingResponse(buf, media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed: pip install reportlab")
    except Exception as e:  # noqa: BLE001
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=str(e))
