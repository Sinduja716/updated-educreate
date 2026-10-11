"""TRACK 2 owns this file: GET /api/v1/history and the picture of one history item."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.pipeline import history as history_store
from app.schemas import HistoryResponse

router = APIRouter(prefix="/api/v1")


@router.get("/history", response_model=HistoryResponse)
def history(limit: int = Query(20, ge=1, le=200), material_type: str | None = None) -> HistoryResponse:
    return HistoryResponse(items=history_store.list_history(limit, material_type))


@router.get("/history/{creation_id}/asset")
def history_asset(creation_id: str):
    path = history_store.asset_path(creation_id)
    if "/" in creation_id or "\\" in creation_id or not path.exists():
        raise HTTPException(404, "history item not found")
    return FileResponse(path, media_type="image/png")
