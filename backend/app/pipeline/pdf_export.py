"""TRACK 2: OPTIONAL PDF of the finished images. The images themselves are the main output (see compose.py).

build_pdf(plan) -> path. One page per finished image (full page, page size from plan.page_format), then a last
resource page: neurons, cost, saving against the maximum setting, and how it is calculated.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A3, A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.config import settings
from app.estimate import METHOD
from app.metrics import compute_metrics
from app.schemas import JobStatus, MaterialType, Plan

PAGE_SIZES = {"A4_PORTRAIT": A4, "A3_PORTRAIT": A3, "CARD_3X5": (3 * inch, 5 * inch), "SQUARE_SMALL": (4 * inch, 4 * inch)}

# Fixed worksheet words per age band. No AI writes these.
WORKSHEET_TEXT = {
    "3-5": ("Look and say", "Look at the picture. Say what you see.", 1),
    "6-8": ("Look and write", "Look at the picture. Write the name on the line.", 2),
    "9-12": ("Look and describe", "Look at the picture. Write two sentences about it.", 3),
    "adult": ("Look and describe", "Look at the picture. Write a short description of it.", 3),
}


def _page(pdf, job, folder: Path, size) -> None:
    """The finished image already holds the picture and all words, so a page is just that image, full page."""
    img = folder / f"{job.job_id}.png"
    if img.exists():
        pdf.drawImage(ImageReader(str(img)), 0, 0, size[0], size[1], preserveAspectRatio=True, anchor="c")


def _resource_page(pdf: canvas.Canvas, plan: Plan) -> None:
    pdf.setPageSize(A4)
    W, H = A4
    m = 60
    met = compute_metrics(plan)
    est = plan.estimate
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(m, H - m - 10, "Resource report")
    lines = [
        f"Material: {plan.material_type.value}    Quality level: {plan.tier} ({plan.steps} steps)",
        f"Pictures: {met.image_calls + met.cache_hits}    Newly generated: {met.image_calls}    Reused: {met.cache_hits}",
        f"Neurons used: {met.neurons_used}    Cost: ${met.estimated_cost_usd}",
        f"Same job at the maximum setting: {met.baseline_neurons} neurons, ${met.baseline_cost_usd}",
        f"Compute saved against the maximum setting: {met.saving_percent}%",
    ]
    if met.seconds_used is not None and met.baseline_seconds is not None:
        lines.append(f"Time: {met.seconds_used} s    Maximum setting: {met.baseline_seconds} s    Saved: {met.time_saving_percent}%")
    if est.placeholder:
        lines.append("Note: neuron numbers are estimates from a placeholder table, not yet measured.")
    lines += ["", "How this is calculated:", METHOD]
    lines += list(met.notes)
    y = H - m - 50
    pdf.setFont("Helvetica", 11)
    for text in lines:
        # simple word wrap
        words, row = text.split(), ""
        if not words:
            y -= 10
            continue
        for w in words:
            trial = (row + " " + w).strip()
            if pdf.stringWidth(trial, "Helvetica", 11) > W - 2 * m:
                pdf.drawString(m, y, row)
                y -= 16
                row = w
            else:
                row = trial
        pdf.drawString(m, y, row)
        y -= 20
    pdf.showPage()


def build_pdf(plan: Plan) -> Path:
    folder = settings.outputs_dir / plan.plan_id
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{plan.plan_id}.pdf"
    size = PAGE_SIZES[plan.page_format]
    pdf = canvas.Canvas(str(out), pagesize=size)
    for job in sorted(plan.jobs, key=lambda j: j.sequence):
        if job.status != JobStatus.completed:
            continue
        pdf.setPageSize(size)
        _page(pdf, job, folder, size)
        pdf.showPage()
    _resource_page(pdf, plan)
    pdf.save()
    return out
