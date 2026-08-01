"""Report generation endpoint with PDF export."""
from __future__ import annotations
import io, logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from mmm.api.auth import OrganizationContext, get_org_id
from mmm.core.engine import MMMModel
from mmm.models.schemas import ModelConfig, MMMDataset, MediaRecord

# ---------------------------------------------------------------------------
# Chart helpers (reportlab Drawing-based, no chart library quirks)
# ---------------------------------------------------------------------------
_INDIGO = "#4F46E5"
_TEAL = "#0D9488"
_SLATE_300 = "#CBD5E1"
_SLATE_400 = "#94A3B8"
_SLATE_600 = "#475569"
_SLATE_900 = "#0F172A"

_LABEL_WIDTH = 90      # px reserved for channel labels
_BAR_GAP = 6           # vertical gap between bars
_BAR_HEIGHT = 22       # height of each horizontal bar
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


def _build_horizontal_bar_chart(
    labels: list[str],
    values: list[float],
    bar_color: str,
    title: str,
    value_fmt: str = "currency",
) -> "Drawing":  # noqa: F821 — runtime is reportlab
    from reportlab.graphics.shapes import Drawing, Rect, String

    n = len(labels)
    chart_height = _CHART_PAD_TOP + n * (_BAR_HEIGHT + _BAR_GAP) + _CHART_PAD_BOTTOM
    drawing = _CHART_TOTAL_WIDTH, chart_height

    d: Drawing = Drawing(_CHART_TOTAL_WIDTH, chart_height)  # type: ignore[assignment]

    # Title
    d.add(String(_CHART_PAD_LEFT, chart_height - 16, title,
                 fontSize=10, fontName="Helvetica-Bold", fillColor=_SLATE_600))

    max_val = max(values) if values else 1
    bar_area_width = _CHART_TOTAL_WIDTH - _LABEL_WIDTH - _CHART_PAD_RIGHT

    for i, (label, value) in enumerate(zip(labels, values)):
        y = chart_height - _CHART_PAD_TOP - (i + 1) * (_BAR_HEIGHT + _BAR_GAP) + _BAR_GAP

        # Channel label
        d.add(String(_CHART_PAD_LEFT, y + 6, label,
                     fontSize=8, fontName="Helvetica", fillColor=_SLATE_900))

        # Bar background (track)
        bar_x = _LABEL_WIDTH
        d.add(Rect(bar_x, y, bar_area_width, _BAR_HEIGHT,
                   fillColor=_SLATE_300, strokeColor=None, rx=3, ry=3))

        # Value bar
        bar_width = (value / max_val) * bar_area_width if max_val > 0 else 0
        if bar_width > 0:
            d.add(Rect(bar_x, y, bar_width, _BAR_HEIGHT,
                       fillColor=bar_color, strokeColor=None, rx=3, ry=3))

        # Value label (mono font for numbers)
        if value_fmt == "currency":
            val_text = _fmt_currency(value)
        elif value_fmt == "percent":
            val_text = f"{value:.1%}"
        else:
            val_text = str(value)

        d.add(String(bar_x + bar_width + 6, y + 6, val_text,
                     fontSize=8, fontName="Courier", fillColor=_SLATE_600))

    return d


def _build_budget_allocation_chart(allocations: list[dict]):  # type: ignore[type-arg]
    """Horizontal bar chart: allocated budget ($) per channel."""
    labels = [a["channel"] for a in allocations]
    values = [a["allocated_budget"] for a in allocations]
    return _build_horizontal_bar_chart(labels, values, _INDIGO,
                                       "Budget Allocation by Channel ($)",
                                       value_fmt="currency")


def _build_contribution_share_chart(contributions: list[dict]):  # type: ignore[type-arg]
    """Horizontal bar chart: contribution share (%) per channel."""
    labels = [c["channel"] for c in contributions]
    values = [c["share"] for c in contributions]
    return _build_horizontal_bar_chart(labels, values, _TEAL,
                                       "Channel Contribution Share (%)",
                                       value_fmt="percent")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

_reports: dict[str, dict] = {}

class ReportRequest(BaseModel):
    records: list[MediaRecord]
    config: ModelConfig
    client_name: str = "Client"
    total_budget: float = 50000

@router.post("/generate")
async def generate_report(body: ReportRequest, ctx: OrganizationContext = Depends(get_org_id)):
    """Train a model, allocate, generate NL report, store it."""
    dataset = MMMDataset(records=body.records)
    model = MMMModel(body.config)
    result = model.fit(dataset)
    if result.status != "ok":
        raise HTTPException(500, detail=f"model train failed: {result.error}")
    contribs = model.get_channel_contributions()
    alloc = model.allocate_budget(body.total_budget)

    # Generate NL report via LLM
    from mmm.ai.report import generate_report as llm_report
    diag = model._diagnostics
    report_md = llm_report(
        contributions=contribs, allocation=alloc,
        r2=diag.r2 if diag else 0.0, mape=diag.mape if diag else 0.0,
        client_name=body.client_name,
    )
    report_id = result.model_id
    _reports[report_id] = {"id": report_id, "client_name": body.client_name, "markdown": report_md,
                           "contributions": [c.model_dump() for c in contribs],
                           "allocation": alloc.model_dump()}
    return {"report_id": report_id, "markdown": report_md}

@router.get("/{report_id}")
async def get_report(report_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    r = _reports.get(report_id)
    if not r:
        raise HTTPException(404, "report not found")
    return r

@router.get("/{report_id}/pdf")
async def download_pdf(report_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    """Export report as PDF using reportlab."""
    r = _reports.get(report_id)
    if not r:
        raise HTTPException(404, "report not found")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=12)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6)

        story = []
        story.append(Paragraph(f"MMM Report — {r['client_name']}", title_style))
        story.append(Spacer(1, 12))

        # Channel contributions section with share chart
        story.append(Paragraph("Channel Contributions", h2_style))
        contribs_data = r.get("contributions", [])
        if contribs_data:
            story.append(_build_contribution_share_chart(contribs_data))
            story.append(Spacer(1, 12))
        for c in contribs_data:
            story.append(Paragraph(
                f"<b>{c['channel']}</b>: spend ${c['spend']:,.0f} · ROAS {c['roas']:.2f}x · share {c['share']:.1%}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 4))

        # Budget allocation section with bar chart
        alloc = r.get("allocation", {})
        story.append(Paragraph("Budget Allocation", h2_style))
        alloc_data = alloc.get("allocations", [])
        if alloc_data:
            story.append(_build_budget_allocation_chart(alloc_data))
            story.append(Spacer(1, 12))
        for a in alloc_data:
            story.append(Paragraph(
                f"<b>{a['channel']}</b>: ${a['allocated_budget']:,.0f} ({a['share']:.1%})",
                styles["Normal"]
            ))
        story.append(Spacer(1, 12))

        # NL report body
        story.append(Paragraph("AI Analysis", h2_style))
        for para in r["markdown"].split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), styles["Normal"]))
                story.append(Spacer(1, 6))

        doc.build(story)
        buf.seek(0)
        filename = f"{r['client_name'].lower().replace(' ', '-')}-mmm-report.pdf"
        return StreamingResponse(buf, media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except ImportError:
        raise HTTPException(500, detail="reportlab not installed: pip install reportlab")
    except Exception as e:
        logger.exception("PDF generation failed")
        raise HTTPException(500, detail=str(e))
