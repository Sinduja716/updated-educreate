"""TRACK 1 (Planner and Measurement) owns this package.

Contract: make_plan(request) -> Plan. Must return one Job per page, in order, with unique job_ids,
every resolved field marked user/planner/default, and warnings for anything the teacher should check.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from app.estimate import TIER_STEPS, make_estimate
from app.planner import gemini
from app.planner.defaults import DEFAULT_COLOUR_MODE, DEFAULTS, SETTINGS_TABLE
from app.schemas import GenerationRequest, Job, MaterialType, Plan, ResolvedField


_KEYWORDS = [
    ("poster", MaterialType.poster), ("wall chart", MaterialType.poster), ("banner", MaterialType.poster),
    ("colouring", MaterialType.colouring), ("coloring", MaterialType.colouring), ("line art", MaterialType.colouring),
    ("flashcard", MaterialType.flashcards), ("flash card", MaterialType.flashcards),
    ("worksheet", MaterialType.worksheet), ("homework", MaterialType.worksheet), ("exercise sheet", MaterialType.worksheet),
    ("thumbnail", MaterialType.thumbnail), ("icon", MaterialType.thumbnail),
    ("avatar", MaterialType.thumbnail), ("draft", MaterialType.thumbnail),
]

def _load_wordlists() -> dict[str, list[str]]:
    path = Path(__file__).parent.parent.parent.parent / "data" / "wordlists.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}

WORDLISTS = _load_wordlists()

_OUTLINE_WORDS = ("outline", "black and white", "black-and-white", "line art", "line drawing", "colouring page",
                  "coloring page", "colouring book", "coloring book", "to colour", "to color", "b/w")
_COLOUR_WORDS = ("colourful", "colorful", "in colour", "in color", "full colour", "full color", "painted", "coloured picture")
_AUDIENCES = [  # first match wins; (words, age_band)
    (("toddler", "preschool", "pre-school", "nursery", "kindergarten", "lkg", "ukg", "age 3", "age 4", "age 5"), "3-5"),
    (("adult", "grown-up", "grown up", "professional", "office", "employees"), "adult"),
    (("teen", "high school", "grade 7", "grade 8", "grade 9", "class 7", "class 8", "class 9"), "9-12"),
    (("grade 4", "grade 5", "grade 6", "class 4", "class 5", "class 6", "older kids", "age 9", "age 10", "age 11"), "9-12"),
    (("grade 1", "grade 2", "grade 3", "class 1", "class 2", "class 3", "first grade", "second grade", "age 6", "age 7", "age 8", "kids", "children"), "6-8"),
]


def infer_colour_mode(prompt: str, material: MaterialType) -> tuple[str, str, str | None]:
    """Returns (mode, source, matched_word). Outline words win over colour words. Else the material default."""
    low = prompt.lower()
    for w in _OUTLINE_WORDS:
        if w in low:
            return "outline", "planner", w
    for w in _COLOUR_WORDS:
        if w in low:
            return "colour", "planner", w
    return DEFAULT_COLOUR_MODE.get(material, "colour"), "default", None


def infer_age_band(prompt: str) -> tuple[str | None, str | None]:
    """Returns (age_band, matched_word) or (None, None). Matches whole words only."""
    low = prompt.lower()
    m = re.search(r"(\d{1,2})\s*[- ]?(?:years?|yrs?)[- ]?olds?", low) or re.search(r"\bage[sd]?\s+(\d{1,2})\b", low)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 90:
            return ("3-5" if n <= 5 else "6-8" if n <= 8 else "9-12" if n <= 14 else "adult"), m.group(0)
    for words, band in _AUDIENCES:
        for w in words:
            if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"s?(?![a-z0-9])", low):
                return band, w
    return None, None


def resolve_purpose(req: GenerationRequest) -> tuple[MaterialType, list[str]]:
    """Rule-based purpose resolution."""
    warnings = []

    # Check for conflicts in the prompt against explicitly chosen material_type
    prompt_lower = req.prompt.lower()
    inferred_purpose = None
    for word, purpose in _KEYWORDS:
        if word in prompt_lower:
            inferred_purpose = purpose
            break

    if req.material_type != MaterialType.auto:
        if inferred_purpose and inferred_purpose != req.material_type:
            warnings.append(f"Prompt mentions {inferred_purpose.value} but {req.material_type.value} was selected.")
        return req.material_type, warnings

    if inferred_purpose:
        return inferred_purpose, [f"Purpose chosen automatically: {inferred_purpose.value}."]

    return MaterialType.worksheet, ["Purpose guessed (worksheet). Pick a button if that is wrong."]

def parse_count_and_subjects(prompt: str) -> tuple[int | None, list[str] | None, str | None]:
    prompt_lower = prompt.lower()

    # Check "a to z"
    if "a to z" in prompt_lower:
        for category, items in WORDLISTS.items():
            if category in prompt_lower and len(items) == 26:
                return 26, items, category
        if "animals" in prompt_lower and "animals" in WORDLISTS:
             return 26, WORDLISTS["animals"], "animals"
        return 26, None, None

    # Check "1 to 10"
    if "1 to 10" in prompt_lower:
        for category, items in WORDLISTS.items():
            if category in prompt_lower:
                return 10, items[:10], category
        if "numbers" in WORDLISTS:
            return 10, WORDLISTS["numbers"], "numbers"
        return 10, None, None

    # Check number ranges e.g. "1 to 5", "1 to 20" (letters "a to z" are handled above)
    rng = re.search(r"\b(\d+)\s*to\s*(\d+)\b", prompt_lower)
    if rng and int(rng.group(2)) >= int(rng.group(1)) and int(rng.group(2)) - int(rng.group(1)) < 100:
        lo, hi = int(rng.group(1)), int(rng.group(2))
        words = WORDLISTS.get("numbers", [])
        subjects = [words[n - 1] if 1 <= n <= len(words) else str(n) for n in range(lo, hi + 1)]
        return hi - lo + 1, subjects, "numbers"

    # Check explicit count e.g. "5 animals"
    match = re.search(r'\b(\d+)\s+([a-z]+)\b', prompt_lower)
    if match:
        count = int(match.group(1))
        category = match.group(2)
        if category in WORDLISTS:
            return count, WORDLISTS[category][:count], category
        return count, None, None

    # Check bare categories
    for category, items in WORDLISTS.items():
        if category in prompt_lower:
            return len(items), items, category

    return 1, None, None

def make_plan(req: GenerationRequest) -> Plan:
    purpose, warnings = resolve_purpose(req)
    ai = gemini.suggest(req.prompt)  # None when Gemini is off or failed; the rules below always work
    if gemini.configured() and ai is None:
        warnings.append("Gemini was not available, so simple rules were used.")
    ai_reason = None
    if ai and req.material_type == MaterialType.auto and any("guessed" in w.lower() for w in warnings) and ai["material_type"]:
        purpose = MaterialType(ai["material_type"])
        warnings = [w for w in warnings if "guessed" not in w.lower()] + [f"Purpose chosen by Gemini: {ai['reason'] or purpose.value}."]
        ai_reason = ai["reason"] or purpose.value
    d = DEFAULTS[purpose]
    resolved: dict[str, ResolvedField] = {}

    # Determine counts and subjects from prompt via planner rules
    planner_count, subjects, category = parse_count_and_subjects(req.prompt)
    if ai and not subjects and ai["subjects"] and not (req.overrides and req.overrides.count):
        subjects, category = ai["subjects"], (ai["topic"] or "topic")
        planner_count = len(subjects) if planner_count in (None, 1) else planner_count
        warnings.append(f"Items chosen by Gemini for '{category}': {', '.join(subjects[:5])}{'...' if len(subjects) > 5 else ''}.")
    elif ai and ai["count"] and planner_count in (None, 1) and not subjects:
        planner_count = ai["count"]

    wanted = req.overrides.count if req.overrides and req.overrides.count else None

    if wanted:
        count = min(wanted, d.max_count)
        resolved["count"] = ResolvedField(value=count, source="user")
        if wanted > d.max_count:
            warnings.append(f"Count reduced to the maximum of {d.max_count}.")
    elif planner_count:
        count = min(planner_count, d.max_count)
        resolved["count"] = ResolvedField(value=count, source="planner")
        if planner_count > d.max_count:
            warnings.append(f"Count reduced to the maximum of {d.max_count}.")
    else:
        count = d.count
        resolved["count"] = ResolvedField(value=count, source="default")

    age = req.overrides.age_band if req.overrides and req.overrides.age_band else None
    inferred_age, age_word = infer_age_band(req.prompt)
    if age:
        resolved["age_band"] = ResolvedField(value=age, source="user")
    elif inferred_age:
        resolved["age_band"] = ResolvedField(value=inferred_age, source="planner")
        warnings.append(f"Age group {inferred_age} chosen from the word '{age_word}'. Change it if that is wrong.")
    elif ai and ai["age_band"]:
        resolved["age_band"] = ResolvedField(value=ai["age_band"], source="planner")
        warnings.append(f"Age group {ai['age_band']} chosen by Gemini. Change it if that is wrong.")
    else:
        resolved["age_band"] = ResolvedField(value="6-8", source="default")

    user_mode = req.overrides.colour_mode if req.overrides and req.overrides.colour_mode else None
    if user_mode:
        mode, mode_source, mode_word = user_mode, "user", None
    else:
        mode, mode_source, mode_word = infer_colour_mode(req.prompt, purpose)
        if mode_source == "default" and ai and ai["colour_mode"]:
            mode, mode_source, mode_word = ai["colour_mode"], "planner", None
            warnings.append(f"Colour mode '{mode}' chosen by Gemini.")
    if mode == "outline" and purpose == MaterialType.worksheet:
        mode, mode_source = "colour", "default"
        warnings.append("Worksheet pictures stay in colour.")
    resolved["colour_mode"] = ResolvedField(value=mode, source=mode_source)  # type: ignore[arg-type]
    if mode_word:
        warnings.append(f"Colour mode '{mode}' chosen from the words '{mode_word}'.")
    lang = req.overrides.language if req.overrides and req.overrides.language else None
    resolved["language"] = ResolvedField(value=lang or "en", source="user" if lang else "default")
    resolved["style"] = ResolvedField(value="simple_outline", source="default")

    manual = req.overrides.tier if req.overrides and req.overrides.tier else None
    table_tier, table_reason = SETTINGS_TABLE.get((purpose, mode), (d.tier, d.reason))
    tier = manual or table_tier
    if manual:
        reason = "Chosen by you."
    else:
        reason = table_reason
        if req.material_type == MaterialType.auto:
            guessed = any("guessed" in w.lower() for w in warnings)
            reason = (f"Detected {purpose.value} by Gemini ({ai_reason}). {table_reason}" if ai_reason else
                      f"Guessed: your request did not say what it is for, so {purpose.value} was chosen. {table_reason} "
                      "Pick a material or a quality level if that is wrong." if guessed else
                      f"Detected {purpose.value} from your words. {table_reason}")
    resolved["tier"] = ResolvedField(value=tier, source="user" if manual else "planner")
    estimate = make_estimate(tier)  # type: ignore[arg-type]
    steps = TIER_STEPS[tier]

    plan_id = uuid.uuid4().hex[:12]
    jobs = []

    for i in range(1, count + 1):
        if subjects and i - 1 < len(subjects) and category:
            item_key = f"{category}:{subjects[i-1]}"
            job_prompt = f"{req.prompt} ({subjects[i-1]})"
        else:
            safe_prompt = re.sub(r'[^a-z0-9]+', '-', req.prompt.lower()).strip('-')
            if not safe_prompt:
                safe_prompt = "empty"
            item_key = f"free:{safe_prompt}-{i}"
            job_prompt = f"{req.prompt} (item {i})"

        jobs.append(Job(
            job_id=f"{plan_id}-{i:02d}",
            plan_id=plan_id,
            sequence=i,
            item_key=item_key,
            prompt=job_prompt,
            steps=steps,
            tier=tier,  # type: ignore[arg-type]
            estimate=estimate,
        ))

    return Plan(
        plan_id=plan_id,
        material_type=purpose,
        original_prompt=req.prompt,
        page_format=d.page_format,  # type: ignore[arg-type]
        profile=d.profile,
        steps=steps,
        tier=tier,  # type: ignore[arg-type]
        tier_reason=reason,
        estimate=estimate,
        resolved=resolved,
        warnings=warnings,
        jobs=jobs,
    )
