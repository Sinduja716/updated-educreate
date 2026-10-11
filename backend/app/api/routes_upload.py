"""TRACK 2 owns this file: POST /api/v1/uploads/outline (turn an uploaded picture into grayscale or outline)."""
import base64
import binascii
import datetime as dt
import io
import time
import uuid

from fastapi import APIRouter, HTTPException
from PIL import Image

from app.pipeline import history
from app.pipeline.outline import to_grayscale, to_outline
from app.schemas import HistoryItem, UploadOutlineRequest, UploadOutlineResponse

router = APIRouter(prefix="/api/v1")
MAX_BYTES = 5 * 1024 * 1024


@router.post("/uploads/outline", response_model=UploadOutlineResponse)
def upload_outline(req: UploadOutlineRequest) -> UploadOutlineResponse:
    data = req.image_base64.split(",", 1)[1] if req.image_base64.startswith("data:") else req.image_base64
    if len(data) > MAX_BYTES * 4 // 3 + 16:
        raise HTTPException(413, "file is larger than 5 MB")
    try:
        raw = base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "image_base64 is not valid base64")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "file is larger than 5 MB")
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        raise HTTPException(400, "file is not an image")

    start = time.perf_counter()
    try:
        png = to_outline(raw, req.threshold) if req.mode == "outline" else to_grayscale(raw)
    except Exception:
        raise HTTPException(400, "could not read this image")
    seconds = round(time.perf_counter() - start, 3)

    creation_id = "up-" + uuid.uuid4().hex[:10]
    history.add_upload(
        HistoryItem(
            creation_id=creation_id, material_type="colouring", prompt=req.filename[:200], item_key=f"upload:{req.filename[:60]}",
            colour_mode="outline" if req.mode == "outline" else None, neurons=0.0, seconds=seconds, cost_usd=0.0,
            provider="upload", cache_hit=False, created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        ),
        png,
    )
    return UploadOutlineResponse(
        creation_id=creation_id, seconds=seconds, asset_uri=f"/api/v1/history/{creation_id}/asset"
    )
