"""TRACK 2: one function per material. A request makes ONE material only; they never mix.

make_images(plan)      -> material_type "colouring" (and "thumbnail")
make_flashcards(plan)  -> material_type "flashcards"
make_worksheet(plan)   -> material_type "worksheet"
make_poster(plan)      -> material_type "poster"

Each one reads plan.resolved["count"] and runs only that many jobs. What differs per material:
the picture prompt, whether the picture is turned into black and white outline, and the tier (set by the planner).
Words on the page are NOT drawn by the image model; the PDF layout adds them (pdf_export.py).
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

from app.pipeline.lineart import to_line_art
from app.schemas import Job, MaterialType, Plan

OUTLINE_PROMPT = (
    "black and white line drawing of {s}, thick clean black outlines, no colour, no shading, no grey, "
    "white background, simple colouring page for children"
)


@dataclass(frozen=True)
class Spec:
    colour_prompt: str          # used when colour_mode is "colour"
    default_colour_mode: str    # used when the plan has no colour_mode
    can_outline: bool           # worksheet pictures are never converted


SPECS: dict[MaterialType, Spec] = {
    MaterialType.colouring: Spec("{s}, simple cartoon illustration for a children's picture book, white background", "outline", True),
    MaterialType.thumbnail: Spec("{s}, simple cartoon illustration for a children's picture book, white background", "colour", True),
    MaterialType.flashcards: Spec("a single {s}, centred, clear and instantly recognisable, plain white background, no text, cute cartoon style for young children", "colour", True),
    MaterialType.worksheet: Spec("{s}, clear simple educational illustration for a children's worksheet, white background, no text", "colour", False),
    MaterialType.poster: Spec("{s}, bright colourful poster illustration for a classroom wall, detailed and cheerful, no text", "colour", True),
}


def colour_mode_of(plan: Plan) -> str:
    """'outline' or 'colour'. Reads plan.resolved['colour_mode'] when the planner sets it, else the material's default.
    Conversion to outline depends ONLY on this value, never on the material alone."""
    spec = SPECS.get(plan.material_type, SPECS[MaterialType.colouring])
    field = plan.resolved.get("colour_mode")
    mode = str(field.value) if field is not None else spec.default_colour_mode
    if mode not in ("outline", "colour"):
        mode = spec.default_colour_mode
    if mode == "outline" and not spec.can_outline:
        mode = "colour"
    return mode


def subject_of(job: Job, plan: Plan) -> str:
    """Word list keys look like 'animals:bear' -> 'bear'. Free text keys use the job prompt."""
    key = job.item_key
    if ":" in key and not key.startswith("free:"):
        return key.split(":", 1)[1].replace("-", " ").replace("_", " ")
    return job.prompt


def build_prompt(plan: Plan, job: Job) -> str:
    spec = SPECS.get(plan.material_type, SPECS[MaterialType.colouring])
    template = OUTLINE_PROMPT if colour_mode_of(plan) == "outline" else spec.colour_prompt
    return template.format(s=subject_of(job, plan))


def finish_image(plan: Plan, job: Job, png: bytes) -> bytes:
    """Turn the picture into outline when colour_mode is 'outline'. Otherwise return it unchanged."""
    if colour_mode_of(plan) != "outline":
        return png
    img = Image.open(io.BytesIO(png)).convert("RGB")
    buf = io.BytesIO()
    to_line_art(img).save(buf, format="PNG")
    return buf.getvalue()


def library_style(plan: Plan) -> str:
    """Part of the library key, so an outline picture is never reused for a colour request."""
    field = plan.resolved.get("style")
    style = str(field.value) if field is not None else "default"
    return f"{style}/{colour_mode_of(plan)}"


def count_of(plan: Plan) -> int:
    field = plan.resolved.get("count")
    try:
        return max(1, int(field.value)) if field is not None else len(plan.jobs)
    except (TypeError, ValueError):
        return len(plan.jobs)


def _run(plan: Plan) -> None:
    from app.pipeline import jobs as job_runner  # imported here: jobs.py imports this file

    wanted = {j.job_id for j in sorted(plan.jobs, key=lambda j: j.sequence)[: count_of(plan)]}
    job_runner.run_jobs(plan, [j for j in plan.jobs if j.job_id in wanted])


def make_images(plan: Plan) -> None:
    _run(plan)


def make_flashcards(plan: Plan) -> None:
    _run(plan)


def make_worksheet(plan: Plan) -> None:
    _run(plan)


def make_poster(plan: Plan) -> None:
    _run(plan)


MAKERS = {
    MaterialType.colouring: make_images,
    MaterialType.thumbnail: make_images,
    MaterialType.flashcards: make_flashcards,
    MaterialType.worksheet: make_worksheet,
    MaterialType.poster: make_poster,
}


def make(plan: Plan) -> None:
    MAKERS.get(plan.material_type, make_images)(plan)
