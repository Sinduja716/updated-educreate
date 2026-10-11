"""In-memory plan store shared by all tracks. OWNER: integrator. Do not edit."""
from __future__ import annotations

from threading import RLock

from app.schemas import Job, Plan


def _rebuild_from_history(plan_id: str) -> Plan | None:
    """Plans made before plans were saved still have their finished pictures in history: rebuild the plan from those rows."""
    from app.pipeline import history
    from app.planner import make_plan
    from app.schemas import GenerationRequest, JobStatus, MaterialType, Overrides

    items = sorted((i for i in history.list_history(100000) if i.plan_id == plan_id), key=lambda i: i.job_id or "")
    if not items:
        return None
    first = items[0]
    ov = Overrides(count=len(items), tier=first.tier, colour_mode=first.colour_mode, age_band=first.age_band)  # type: ignore[arg-type]
    plan = make_plan(GenerationRequest(material_type=MaterialType(first.material_type), prompt=first.prompt, overrides=ov))
    plan.plan_id = plan_id
    jobs = []
    for n, item in enumerate(items, start=1):
        job = plan.jobs[min(n - 1, len(plan.jobs) - 1)].model_copy(deep=True)
        job.job_id, job.plan_id, job.sequence, job.item_key = item.job_id or f"{plan_id}-{n:02d}", plan_id, n, item.item_key
        job.status = JobStatus.completed
        job.cache_hit = item.cache_hit
        job.neurons = item.neurons
        job.tier = item.tier or job.tier  # type: ignore[assignment]
        job.asset_uri = f"/api/v1/jobs/{job.job_id}/asset"
        jobs.append(job)
    plan.jobs = jobs
    return plan


class PlanStore:
    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}
        self._lock = RLock()

    def save(self, plan: Plan) -> None:
        with self._lock:
            self._plans[plan.plan_id] = plan

    @staticmethod
    def _persist(plan: Plan) -> None:
        """Plans are also kept in the database so upgrade, retry, export and zip still work after a restart."""
        try:
            from app.pipeline import app_state

            app_state.put("plans", plan.plan_id, plan.model_dump(mode="json"))
        except Exception:  # the database must never break a request
            pass

    @staticmethod
    def _load(plan_id: str) -> Plan | None:
        try:
            from app.pipeline import app_state

            doc = app_state.get("plans", plan_id)
            return _rebuild_from_history(plan_id) if doc is None else Plan(**doc)
        except Exception:
            return None

    def get(self, plan_id: str) -> Plan | None:
        with self._lock:
            plan = self._plans.get(plan_id)
        if plan is None:
            plan = self._load(plan_id)
            if plan is not None:
                with self._lock:
                    plan = self._plans.setdefault(plan_id, plan)
        return plan

    def find_job(self, job_id: str) -> tuple[Plan, Job] | None:
        with self._lock:
            for plan in self._plans.values():
                for job in plan.jobs:
                    if job.job_id == job_id:
                        return plan, job
        plan = self.get(job_id.rsplit("-", 1)[0]) if "-" in job_id else None  # job ids look like <plan_id>-01
        if plan is not None:
            for job in plan.jobs:
                if job.job_id == job_id:
                    return plan, job
        return None

    def clear(self) -> None:
        with self._lock:
            self._plans.clear()


store = PlanStore()
