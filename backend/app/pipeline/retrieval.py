"""TRACK 2: the retrieval order for one picture. Cheapest first; generating is the last resort.

  1. database lookup  : same item, material, colour mode, age band, enough steps          -> reuse, 0 neurons
  2. similar lookup   : same material, colour mode, age band; prompt words overlap >= 0.6   -> reuse, 0 neurons
  3. change a match   : a stored COLOUR picture while OUTLINE is wanted -> line-art convert -> 0 neurons
  4. online search    : not built (ONLINE_SEARCH is read but has no effect yet)
  5. generate         : done by jobs.py (budget guard, retries, then library.save)

find_stored(plan, job) runs steps 1 to 3 and returns (png_bytes, how) or None.
"""
from __future__ import annotations

import io
import re

from PIL import Image

from app.pipeline import library, materials
from app.pipeline.lineart import to_line_art
from app.schemas import Job, Plan

SIMILAR_OVERLAP = 0.6
_STOP = {"a", "an", "the", "and", "her", "his", "its", "with", "of", "in", "on", "at", "to", "for", "item", "page", "picture", "image"}


def prompt_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", str(text).lower())
    return {w for w in words if w not in _STOP and len(w) > 1}


def overlap(a: set[str], b: set[str]) -> float:
    """Shared words divided by the words of the shorter prompt."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _stem(key: str) -> str:
    return re.sub(r"-\d+$", "", str(key).strip().lower())


def _style(plan: Plan, mode: str) -> str:
    field = plan.resolved.get("style")
    style = str(field.value) if field is not None else "default"
    return f"{style}/{mode}"


def _age(plan: Plan) -> str:
    """The picture does not depend on age (age only changes the words on the page), so every age shares one stored picture."""
    return "any"


def _in_mode(plan: Plan, job: Job, mode: str):
    """Steps 1 and 2 inside one colour mode. Returns png bytes or None."""
    material = plan.material_type.value
    style, age = _style(plan, mode), _age(plan)
    exact = library.find(job.item_key, material, style, age, min_steps=job.steps)
    if exact is not None:
        return exact, "reuse"
    wanted = prompt_tokens(materials.subject_of(job, plan))
    best, best_score = None, 0.0
    stem = _stem(job.item_key)
    for c in library.candidates(material, style, age):
        if c["steps"] < job.steps:
            continue
        if _stem(c["subject"]) == stem:  # other pages of the same request must stay different pictures
            continue
        score = overlap(wanted, prompt_tokens(c["meta"].get("subject") or c["subject"]))
        if score > best_score:
            best, best_score = c, score
    if best is not None and best_score >= SIMILAR_OVERLAP:
        data = library.read_file(best["file"])
        if data is not None:
            return data, "reuse-similar"
    return None


def find_stored(plan: Plan, job: Job):
    if not library.is_reusable(job.item_key):
        return None
    mode = materials.colour_mode_of(plan)
    hit = _in_mode(plan, job, mode)
    if hit is not None:
        return hit
    if mode == "outline":  # step 3: only colour -> outline, never the other way round
        other = _in_mode(plan, job, "colour")
        if other is not None:
            img = Image.open(io.BytesIO(other[0])).convert("RGB")
            buf = io.BytesIO()
            to_line_art(img).save(buf, format="PNG")
            return buf.getvalue(), "reuse-outline"
    return None
