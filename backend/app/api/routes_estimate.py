"""INTEGRATOR owns this file: GET /api/v1/estimate/method (how every estimate is calculated)."""
from fastapi import APIRouter

from app.estimate import explain_method

router = APIRouter(prefix="/api/v1")


@router.get("/estimate/method")
def estimate_method() -> dict:
    return explain_method()
