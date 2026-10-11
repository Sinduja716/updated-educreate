"""TRACK 1 owns this file: POST /api/v1/plans and GET /api/v1/plans/{id}."""
from fastapi import APIRouter, HTTPException

from app.planner import make_plan
from app.schemas import GenerationRequest, Plan
from app.store import store

router = APIRouter(prefix="/api/v1")


@router.post("/plans", response_model=Plan)
def create_plan(req: GenerationRequest) -> Plan:
    plan = make_plan(req)
    store.save(plan)
    return plan


@router.get("/plans/{plan_id}", response_model=Plan)
def read_plan(plan_id: str) -> Plan:
    plan = store.get(plan_id)
    if plan is None:
        raise HTTPException(404, "plan not found")
    return plan
