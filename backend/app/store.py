"""In-memory plan store shared by all tracks. OWNER: integrator. Do not edit."""
from __future__ import annotations

from threading import RLock

from app.schemas import Job, Plan


class PlanStore:
    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}
        self._lock = RLock()

    def save(self, plan: Plan) -> None:
        with self._lock:
            self._plans[plan.plan_id] = plan

    def get(self, plan_id: str) -> Plan | None:
        with self._lock:
            return self._plans.get(plan_id)

    def find_job(self, job_id: str) -> tuple[Plan, Job] | None:
        with self._lock:
            for plan in self._plans.values():
                for job in plan.jobs:
                    if job.job_id == job_id:
                        return plan, job
        return None

    def clear(self) -> None:
        with self._lock:
            self._plans.clear()


store = PlanStore()
