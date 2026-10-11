"""TRACK 2: PDF export with ReportLab. Contract: build_pdf(plan) -> path of the PDF.

One PDF per request, one material only:
  colouring  -> A4, one picture per page
  flashcards -> 3x5 inch card, picture plus the word under it
  worksheet  -> A4, title, instruction line, picture, answer lines (fixed text per age band)
  poster     -> A3 (or A4), headline on top, picture below
The last page is the resource page: neurons, cost, saving against the maximum setting, and how it was calculated.
The image model never draws words; every word on a page is added here.
Built-in Helvetica covers Latin text only. A non-Latin language would need a registered font (not done yet).
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
from app.pipeline.materials import subject_of
from app.schemas import JobStatus, MaterialType, Plan

PAGE_SIZES = {"A4_PORTRAIT": A4, "A3_PORTRAIT": A3, "CARD_3X5": (3 * inch, 5 * inch), "SQUARE_SMALL": (4 * inch, 4 * inch)}

# Fixed worksheet words per age band. No AI writes these.
WORKSHEET_TEXT = {
    "3-5": ("Look and say", "Look at the picture. Say what you see.", 1),
    "6-8": ("Look and write", "Look at the picture. Write the name on the line.", 2),
    "9-12": ("Look and describe", "Look at the picture. Write two sentences about it.", 3),
    "adult": ("Look and describe", "Look at the picture. Write a short description of it.", 3),
}


def _fit(pdf: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> float:
    while size > 6 and pdf.stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _centered(pdf, text: str, x_mid: float, y: float, font: str, size: float, max_width: float) -> None:
    size = _fit(pdf, text, font, size, max_width)
    pdf.setFont(font, size)
    pdf.drawCentredString(x_mid, y, text)


def _picture(pdf, path: Path, x: float, y: float, w: float, h: float) -> None:
    if path.exists():
        pdf.drawImage(ImageReader(str(path)), x, y, w, h, preserveAspectRatio=True, anchor="c")


def _page(pdf, plan: Plan, job, folder: Path, size) -> None:
    W, H = size
    m = 0.08 * min(size)
    img = folder / f"{job.job_id}.png"
    kind = plan.material_type
    label = subject_of(job, plan).strip().capitalize()
    if kind == MaterialType.flashcards:
        _picture(pdf, img, m, m + 0.55 * inch, W - 2 * m, H - 2 * m - 0.55 * inch)
        _centered(pdf, label, W / 2, m + 0.15 * inch, "Helvetica-Bold", 22, W - 2 * m)
    elif kind == MaterialType.worksheet:
        age = str(plan.resolved["age_band"].value) if "age_band" in plan.resolved else "6-8"
        title, instruction, lines = WORKSHEET_TEXT.get(age, WORKSHEET_TEXT["6-8"])
        _centered(pdf, title, W / 2, H - m - 20, "Helvetica-Bold", 28, W - 2 * m)
        _centered(pdf, instruction, W / 2, H - m - 50, "Helvetica", 14, W - 2 * m)
        pdf.setFont("Helvetica", 12)
        pdf.drawString(m, H - m - 80, "Name: ______________________")
        top = H - m - 100
        bottom = m + 40 + lines * 36
        _picture(pdf, img, m, bottom, W - 2 * m, top - bottom)
        for i in range(lines):
            y = m + 30 + i * 36
            pdf.line(m, y, W - m, y)
    elif kind == MaterialType.poster:
        headline = plan.original_prompt.strip()[:60].upper()
        _centered(pdf, headline, W / 2, H - m - 30, "Helvetica-Bold", 44, W - 2 * m)
        _picture(pdf, img, m, m, W - 2 * m, H - 2 * m - 70)
    else:
        _picture(pdf, img, m, m, W - 2 * m, H - 2 * m)


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
        _page(pdf, plan, job, folder, size)
        pdf.showPage()
    _resource_page(pdf, plan)
    pdf.save()
    return out
