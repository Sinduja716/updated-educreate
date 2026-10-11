"""TRACK 2: turns a raw picture into the FINISHED IMAGE the user sees and downloads.

  flashcards -> a card image (3:5): picture on top, the word under it
  worksheet  -> an A4-shaped page image: title, instruction line, Name line, picture, answer lines
  poster     -> an A4/A3-shaped image: headline on top, picture below
  colouring  -> an A4-shaped page image with the black-and-white picture (no resizing, so lines stay pure black/white)
  thumbnail  -> the picture as it is

The image model draws pictures only. Every word is added here. The raw picture (no words) is what the reuse
library stores, so a stored picture can be reused for any word, language or age group.
All text is set to fit the width. Fonts: Arial (Windows) or DejaVu, with Nirmala UI for Indian scripts.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from app.pipeline.materials import colour_mode_of, subject_of
from app.schemas import Job, MaterialType, Plan

PAGE = (1240, 1754)   # A4 / A3 shape
CARD = (900, 1500)    # 3 x 5 inch shape
ACCENT = {MaterialType.flashcards: (231, 111, 81), MaterialType.worksheet: (42, 157, 143), MaterialType.poster: (38, 70, 83)}

# Fixed worksheet words per age band. No AI writes these.
WORKSHEET_TEXT = {
    "3-5": ("Look and say", "Look at the picture. Say what you see.", 1),
    "6-8": ("Look and write", "Look at the picture. Write the name on the line.", 2),
    "9-12": ("Look and describe", "Look at the picture. Write two sentences about it.", 3),
    "adult": ("Look and describe", "Look at the picture. Write a short description of it.", 3),
}


def _font(size: int, bold: bool = True, text: str = "") -> ImageFont.ImageFont:
    names = (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    if any(ord(c) > 0x024F for c in text):  # Indian and other scripts
        names = ["NirmalaB.ttf" if bold else "Nirmala.ttf", "Nirmala.ttf", "NotoSans-Regular.ttf"] + names
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int, bold: bool = True) -> ImageFont.ImageFont:
    size = start
    while size > 14:
        f = _font(size, bold, text)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _font(14, bold, text)


def _paste_fit(canvas: Image.Image, pic: Image.Image, box: tuple[int, int, int, int], resample: bool = True) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    scale = min(w / pic.width, h / pic.height)
    if not resample:
        scale = min(scale, 1.0)
    new = (max(1, int(pic.width * scale)), max(1, int(pic.height * scale)))
    p = pic if new == pic.size else pic.resize(new, Image.LANCZOS if resample else Image.NEAREST)
    canvas.paste(p, (x0 + (w - new[0]) // 2, y0 + (h - new[1]) // 2))


def _center(draw, text, y, width, start, fill, bold=True, margin=70):
    f = _fit_text(draw, text, width - 2 * margin, start, bold)
    draw.text(((width - draw.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def label_for(plan: Plan, job: Job) -> str:
    word = subject_of(job, plan).strip()
    lang = str(plan.resolved["language"].value) if "language" in plan.resolved else "en"
    if lang and lang != "en":
        try:
            from app.planner import gemini

            word = gemini.translate_word(word, lang) or word
        except Exception:
            pass
    return word[:1].upper() + word[1:]


def compose(plan: Plan, job: Job, raw_png: bytes) -> bytes:
    """Never raises: if the layout fails the raw picture is returned so the job still completes."""
    try:
        return _compose(plan, job, raw_png)
    except Exception:
        return raw_png


def _compose(plan: Plan, job: Job, raw_png: bytes) -> bytes:
    pic = Image.open(io.BytesIO(raw_png)).convert("RGB")
    kind = plan.material_type
    if kind == MaterialType.flashcards:
        img = _card(plan, job, pic)
    elif kind == MaterialType.worksheet:
        img = _worksheet(plan, pic)
    elif kind == MaterialType.poster:
        img = _poster(plan, pic)
    elif kind == MaterialType.colouring and colour_mode_of(plan) == "outline":
        img = Image.new("RGB", PAGE, "white")
        _paste_fit(img, pic, (60, 140, PAGE[0] - 60, PAGE[1] - 140), resample=False)
    else:
        return raw_png
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _card(plan: Plan, job: Job, pic: Image.Image) -> Image.Image:
    w, h = CARD
    img = Image.new("RGB", CARD, "white")
    d = ImageDraw.Draw(img)
    color = ACCENT[MaterialType.flashcards]
    d.rounded_rectangle([14, 14, w - 14, h - 14], radius=60, outline=color, width=14)
    _paste_fit(img, pic, (60, 60, w - 60, h - 380))
    _center(d, label_for(plan, job), h - 330, w, 190, color, margin=70)
    return img


def _worksheet(plan: Plan, pic: Image.Image) -> Image.Image:
    w, h = PAGE
    age = str(plan.resolved["age_band"].value) if "age_band" in plan.resolved else "6-8"
    title, instruction, lines = WORKSHEET_TEXT.get(age, WORKSHEET_TEXT["6-8"])
    color = ACCENT[MaterialType.worksheet]
    img = Image.new("RGB", PAGE, "white")
    d = ImageDraw.Draw(img)
    _center(d, title, 70, w, 100, color)
    _center(d, instruction, 200, w, 46, (60, 60, 60), bold=False)
    d.text((80, 290), "Name: ______________________", font=_font(40, False), fill=(60, 60, 60))
    bottom = h - 120 - lines * 130
    _paste_fit(img, pic, (80, 370, w - 80, bottom))
    for i in range(lines):
        y = h - 110 - i * 130
        d.line([80, y, w - 80, y], fill=(90, 90, 90), width=4)
    d.rectangle([30, 30, w - 30, h - 30], outline=color, width=8)
    return img


def _poster(plan: Plan, pic: Image.Image) -> Image.Image:
    w, h = PAGE
    color = ACCENT[MaterialType.poster]
    img = Image.new("RGB", PAGE, "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 230], fill=color)
    headline = plan.original_prompt.strip()[:60].upper()
    f = _fit_text(d, headline, w - 120, 120)
    d.text(((w - d.textlength(headline, font=f)) / 2, 60), headline, font=f, fill="white")
    _paste_fit(img, pic, (50, 270, w - 50, h - 50))
    return img
