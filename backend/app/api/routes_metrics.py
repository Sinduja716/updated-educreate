"""TRACK 1 owns this file: GET /api/v1/plans/{id}/metrics."""
from fastapi import APIRouter, HTTPException

from app.metrics import compute_metrics
from app.schemas import MetricsResponse
from app.store import store

router = APIRouter(prefix="/api/v1")


@router.get("/plans/{plan_id}/metrics", response_model=MetricsResponse)
def plan_metrics(plan_id: str) -> MetricsResponse:
    plan = store.get(plan_id)
    if plan is None:
        raise HTTPException(404, "plan not found")
    return compute_metrics(plan)
