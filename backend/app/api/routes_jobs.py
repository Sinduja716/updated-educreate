"""TRACK 2 owns this file: generate, status, job, retry, asset, export, download."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.pipeline import jobs as job_runner
from app.pipeline.pdf_export import build_pdf
from app.schemas import ExportResponse, GenerateResponse, Job, JobStatus, StatusResponse
from app.store import store

router = APIRouter(prefix="/api/v1")


def _plan_or_404(plan_id: str):
    plan = store.get(plan_id)
    if plan is None:
        raise HTTPException(404, "plan not found")
    return plan


@router.post("/plans/{plan_id}/generate", response_model=GenerateResponse, status_code=202)
def generate(plan_id: str, background: BackgroundTasks) -> GenerateResponse:
    _plan_or_404(plan_id)
    background.add_task(job_runner.run_plan, plan_id)
    return GenerateResponse(plan_id=plan_id, accepted=True)


@router.get("/plans/{plan_id}/status", response_model=StatusResponse)
def status(plan_id: str) -> StatusResponse:
    plan = _plan_or_404(plan_id)
    count = lambda s: sum(1 for j in plan.jobs if j.status == s)  # noqa: E731
    return StatusResponse(
        plan_id=plan_id,
        total=len(plan.jobs),
        completed=count(JobStatus.completed),
        failed=count(JobStatus.failed),
        pending=count(JobStatus.pending),
        processing=count(JobStatus.processing),
        complete=count(JobStatus.completed) == len(plan.jobs),
        jobs=sorted(plan.jobs, key=lambda j: j.sequence),
    )


@router.get("/jobs/{job_id}", response_model=Job)
def read_job(job_id: str) -> Job:
    found = store.find_job(job_id)
    if found is None:
        raise HTTPException(404, "job not found")
    return found[1]


@router.post("/jobs/{job_id}/retry", response_model=Job)
def retry(job_id: str) -> Job:
    found = store.find_job(job_id)
    if found is None:
        raise HTTPException(404, "job not found")
    if not job_runner.retry_job(job_id):
        raise HTTPException(409, "only failed jobs can be retried")
    return found[1]


@router.get("/jobs/{job_id}/asset")
def asset(job_id: str):
    found = store.find_job(job_id)
    if found is None or found[1].asset_uri is None:
        raise HTTPException(404, "asset not found")
    path = settings.outputs_dir / found[0].plan_id / f"{job_id}.png"
    return FileResponse(path, media_type="image/png")


@router.post("/plans/{plan_id}/export", response_model=ExportResponse)
def export(plan_id: str) -> ExportResponse:
    plan = _plan_or_404(plan_id)
    if any(j.status != JobStatus.completed for j in plan.jobs):
        raise HTTPException(409, "not all pages are completed")
    build_pdf(plan)
    return ExportResponse(plan_id=plan_id, download_url=f"/api/v1/plans/{plan_id}/download")


@router.get("/plans/{plan_id}/download")
def download(plan_id: str):
    path = settings.outputs_dir / plan_id / f"{plan_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "export not found")
    return FileResponse(path, media_type="application/pdf", filename=f"{plan_id}.pdf")
