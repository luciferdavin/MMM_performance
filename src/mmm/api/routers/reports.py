"""Report generation endpoint with PDF export."""
from __future__ import annotations
import io, logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from mmm.api.auth import OrganizationContext, get_org_id
from mmm.core.engine import MMMModel
from mmm.models.schemas import ModelConfig, MMMDataset, MediaRecord

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

        # Channel contributions table
        story.append(Paragraph("Channel Contributions", h2_style))
        for c in r.get("contributions", []):
            story.append(Paragraph(
                f"<b>{c['channel']}</b>: spend ${c['spend']:,.0f} · ROAS {c['roas']:.2f}x · share {c['share']:.1%}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 4))

        # Budget allocation
        alloc = r.get("allocation", {})
        story.append(Paragraph("Budget Allocation", h2_style))
        for a in alloc.get("allocations", []):
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
