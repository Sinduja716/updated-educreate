"""TRACK 2 owns this file: what the web app needs besides generating.

Sessions (the user's creation sessions), preferences, saved images (= finished pictures in history) and the
global usage numbers. Everything is stored through app_state / history (MongoDB or SQLite), nothing is hard coded.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.estimate import USD_PER_1000_NEURONS, make_estimate
from app.pipeline import app_state, history as history_store

router = APIRouter(prefix="/api/v1")

CATEGORY_OF = {"colouring": "Images", "thumbnail": "Images", "flashcards": "Flashcards", "worksheet": "Worksheets", "poster": "Posters"}

DEFAULT_PREFERENCES = {
    "theme": "System", "density": "Comfortable", "defaultOrientation": "Portrait", "defaultQuantity": 1,
    "showCostEstimates": True, "defaultDownloadFormat": "PNG", "defaultExportSize": "A4",
}


# ---------- sessions ----------
@router.get("/sessions")
def list_sessions() -> list[dict]:
    return sorted(app_state.list_all("sessions"), key=lambda s: s.get("timestamp", ""), reverse=True)


@router.put("/sessions/{session_id}")
def save_session(session_id: str, body: dict) -> dict:
    body["id"] = session_id
    app_state.put("sessions", session_id, body)
    return body


class Rename(BaseModel):
    title: str


@router.patch("/sessions/{session_id}")
def rename_session(session_id: str, body: Rename) -> dict:
    session = app_state.get("sessions", session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    session["title"] = body.title
    app_state.put("sessions", session_id, session)
    return session


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    app_state.delete("sessions", session_id)


@router.delete("/sessions", status_code=204)
def clear_sessions() -> None:
    app_state.clear("sessions")


# ---------- preferences ----------
@router.get("/preferences")
def read_preferences() -> dict:
    return {**DEFAULT_PREFERENCES, **(app_state.get("preferences", "default") or {})}


@router.put("/preferences")
def write_preferences(body: dict) -> dict:
    merged = {**read_preferences(), **body}
    app_state.put("preferences", "default", merged)
    return merged


# ---------- saved images (finished pictures kept in history) ----------
@router.get("/saved-images")
def saved_images(q: str | None = None) -> list[dict]:
    """All saved pictures, newest first. With q, only pictures whose prompt or subject contains every word of q."""
    words = [w for w in (q or "").lower().split() if w]
    items = history_store.list_history(1000)
    if words:
        items = [i for i in items if all(w in f"{i.prompt} {i.item_key} {i.material_type}".lower().replace("-", " ").replace(":", " ") for w in words)]
    return [
        {
            "id": i.creation_id,
            "url": f"/api/v1/history/{i.creation_id}/asset",
            "title": i.prompt,
            "category": CATEGORY_OF.get(i.material_type, "Images"),
            "date": i.created_at,
        }
        for i in items
    ]


@router.delete("/saved-images/{image_id}", status_code=204)
def delete_saved_image(image_id: str) -> None:
    history_store.delete_history(image_id)


@router.delete("/saved-images", status_code=204)
def clear_saved_images() -> None:
    history_store.clear_history()


# ---------- global numbers ----------
@router.get("/metrics/global")
def global_metrics() -> dict:
    """Totals over every finished picture in history. Saving = against making each picture fresh at maximum quality."""
    items = history_store.list_history(100000)
    items = [i for i in items if i.provider != "upload"]
    requested = len(items)
    reused = sum(1 for i in items if i.cache_hit)
    generated = requested - reused
    used = sum((i.neurons or 0.0) for i in items if not i.cache_hit)
    baseline = make_estimate("high").neurons * requested
    saved = max(0.0, baseline - used)
    to_usd = lambda n: n / 1000.0 * USD_PER_1000_NEURONS  # noqa: E731
    return {
        "totalRequested": requested,
        "totalGenerated": generated,
        "totalReused": reused,
        "neuronsUsed": round(used, 3),
        "neuronsSaved": round(saved, 3),
        "costUsd": round(to_usd(used), 6),
        "costSavedUsd": round(to_usd(saved), 6),
        "savingsPercent": round(saved / baseline * 100, 1) if baseline > 0 else 0.0,
    }
