"""Purpose defaults. TRACK 1 owns this file. Tier = how much compute the purpose deserves.
Calibration (docs/track1) may change a purpose's tier, but keep at least two different tiers in use."""
from dataclasses import dataclass

from app.schemas import MaterialType


@dataclass(frozen=True)
class ButtonDefaults:
    page_format: str
    count: int
    max_count: int
    profile: str
    tier: str
    reason: str


DEFAULTS: dict[MaterialType, ButtonDefaults] = {
    MaterialType.colouring: ButtonDefaults(
        "A4_PORTRAIT", 1, 30, "colouring_basic", "draft",
        "Colouring pages need clean outlines, not fine detail, so the lowest effort is enough."),
    MaterialType.worksheet: ButtonDefaults(
        "A4_PORTRAIT", 1, 30, "worksheet_basic", "standard",
        "Worksheet pictures must be clear but sit small on the page."),
    MaterialType.flashcards: ButtonDefaults(
        "CARD_3X5", 6, 30, "flashcard_basic", "standard",
        "Flashcard pictures are printed small but must be instantly recognisable."),
    MaterialType.poster: ButtonDefaults(
        "A3_PORTRAIT", 1, 3, "poster_high", "high",
        "Posters are printed large and viewed from a distance, so detail matters."),
    MaterialType.thumbnail: ButtonDefaults(
        "SQUARE_SMALL", 1, 12, "thumbnail_draft", "draft",
        "Thumbnails and icons are tiny, so a quick draft is enough."),
}


# Settings table: (material, colour_mode) -> (tier, reason). The planner reads this; "user" overrides still win.
SETTINGS_TABLE: dict[tuple[MaterialType, str], tuple[str, str]] = {
    (MaterialType.colouring, "outline"): ("draft", "Black-and-white outlines need clean lines, not fine detail, so the lowest effort is enough."),
    (MaterialType.colouring, "colour"): ("standard", "A coloured picture needs more detail than an outline, so a middle effort is used."),
    (MaterialType.flashcards, "outline"): ("draft", "Outline cards only need clear shapes, so the lowest effort is enough."),
    (MaterialType.flashcards, "colour"): ("standard", "Flashcard pictures are printed small but must be instantly recognisable."),
    (MaterialType.worksheet, "outline"): ("standard", "Worksheet pictures must be clear but sit small on the page."),
    (MaterialType.worksheet, "colour"): ("standard", "Worksheet pictures must be clear but sit small on the page."),
    (MaterialType.poster, "outline"): ("standard", "An outline poster is large but has no colour detail, so a middle effort is used."),
    (MaterialType.poster, "colour"): ("high", "Coloured posters are printed large and viewed from a distance, so detail matters."),
    (MaterialType.thumbnail, "outline"): ("draft", "Thumbnails and icons are tiny, so a quick draft is enough."),
    (MaterialType.thumbnail, "colour"): ("draft", "Thumbnails and icons are tiny, so a quick draft is enough."),
}

# Default colour mode per material when the user says nothing.
DEFAULT_COLOUR_MODE: dict[MaterialType, str] = {
    MaterialType.colouring: "outline", MaterialType.flashcards: "colour", MaterialType.worksheet: "colour",
    MaterialType.poster: "colour", MaterialType.thumbnail: "colour",
}
