"""TRACK 2: runs the jobs of a plan. Contract: run_plan(plan_id) fills each job; retry_job(job_id) redoes one.

Per job: reuse library first (0 neurons) -> budget guard -> provider with bounded retries and backoff ->
save to the library. Jobs run in a thread pool of MAX_CONCURRENT_IMAGE_JOBS. A failed job never stops the
others; only failed jobs are retried later.
"""
from __future__ import annotations

import io
import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from app.config import settings
from app.estimate import make_estimate, neurons_for_steps
from app.pipeline import budget, compose, history, library, materials, retrieval
from app.providers import get_provider
from app.providers.base import ProviderError
from app.schemas import Job, JobStatus, Plan
from app.store import store

RETRYABLE = {"timeout", "server_error"}
BACKOFF_SECONDS = (1.0, 3.0)
# Cloudflare's NSFW filter sometimes rejects harmless prompts at random (the same prompt passes on a later try).
# Retry those with a gentle child-friendly suffix; it is a different prompt each time, so it is not a blind repeat.
FILTER_RETRIES = 5
FILTER_SUFFIXES = (
    "",
    ", cute, friendly, for a children's picture book",
    ", child-friendly educational illustration, wholesome",
    ", simple cartoon for young children, safe for school",
    ", gentle kindergarten style, cheerful",
    ", family-friendly clip art style",
)


def _asset_path(job: Job):
    folder = settings.outputs_dir / job.plan_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{job.job_id}.png"


def _to_png(data: bytes) -> bytes:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _lib_key(plan: Plan, job: Job) -> tuple[str, str, str, str]:
    r = plan.resolved
    return (
        job.item_key,
        plan.material_type.value,
        materials.library_style(plan),
        "any",  # age only changes the words on the page, not the picture
    )


def _generate_with_retries(provider, job: Job, base_prompt: str):
    last: ProviderError | None = None
    failures = 0       # timeout / server errors
    filtered = 0       # content-filter false positives
    while True:
        job.attempts += 1
        prompt = base_prompt + FILTER_SUFFIXES[min(filtered, len(FILTER_SUFFIXES) - 1)]
        try:
            return provider.generate(prompt, job.steps)
        except ProviderError as exc:
            last = exc
            if exc.code == "filtered":
                filtered += 1
                if filtered > FILTER_RETRIES:
                    break
                time.sleep(0.5)
            elif exc.code in RETRYABLE:
                failures += 1
                if failures > settings.max_retries:
                    break
                time.sleep(BACKOFF_SECONDS[min(failures - 1, len(BACKOFF_SECONDS) - 1)])
            else:
                break
    assert last is not None
    raise last


def _run_one(plan: Plan, job: Job) -> None:
    _run_one_inner(plan, job)
    store._persist(plan)
    if job.status == JobStatus.completed:
        try:
            history.add_history(job, plan)
        except Exception:  # history must never break a generation
            pass


def _run_one_inner(plan: Plan, job: Job) -> None:
    job.status = JobStatus.processing
    job.error_code = None
    key = _lib_key(plan, job)

    hit = retrieval.find_stored(plan, job)
    if hit is not None:
        cached, how = hit
        _asset_path(job).write_bytes(compose.compose(plan, job, cached))
        job.asset_uri = f"/api/v1/jobs/{job.job_id}/asset"
        job.cache_hit = True
        job.provider = "library"
        job.model = how
        job.latency_ms = 0
        job.neurons = 0.0
        job.estimate = make_estimate(job.tier, actual_neurons=0.0)
        job.status = JobStatus.completed
        return

    job.cache_hit = False
    provider = get_provider()
    real = provider.name != "mock"
    reserved = neurons_for_steps(job.steps) if real else 0.0
    if real and not budget.reserve(reserved):
        job.status = JobStatus.failed
        job.error_code = "budget"
        return
    try:
        result = _generate_with_retries(provider, job, materials.build_prompt(plan, job))
        png = materials.finish_image(plan, job, _to_png(result.image_bytes))  # raw picture: this is what the library keeps
        final = compose.compose(plan, job, png)                              # finished image: picture + words
    except ProviderError as exc:
        if real:
            budget.release(reserved)
        job.status = JobStatus.failed
        job.error_code = exc.code
        return
    except Exception:  # unreadable image bytes
        if real:
            budget.settle(reserved, reserved)  # the call was made and paid for
        job.status = JobStatus.failed
        job.error_code = "bad_image"
        return

    _asset_path(job).write_bytes(final)
    neurons = result.neurons if result.neurons is not None else neurons_for_steps(job.steps)
    if real:
        budget.settle(reserved, neurons)
        library.save(*key, png, {"steps": job.steps, "model": result.model, "provider": provider.name,
                                 "subject": materials.subject_of(job, plan)})
    job.asset_uri = f"/api/v1/jobs/{job.job_id}/asset"
    job.provider = provider.name
    job.model = result.model
    job.latency_ms = result.latency_ms
    job.neurons = neurons
    job.estimate = make_estimate(job.tier, actual_neurons=result.neurons, actual_seconds=result.latency_ms / 1000.0)
    job.status = JobStatus.completed


def run_jobs(plan: Plan, selected: list[Job]) -> None:
    """Runs the given jobs of a plan in the thread pool. Called by the four make_* functions in materials.py."""
    todo = [j for j in sorted(selected, key=lambda j: j.sequence) if j.status in (JobStatus.pending, JobStatus.failed)]
    with ThreadPoolExecutor(max_workers=max(1, settings.max_concurrent_jobs)) as pool:
        list(pool.map(lambda j: _run_one(plan, j), todo))


def run_plan(plan_id: str) -> None:
    plan = store.get(plan_id)
    if plan is None:
        return
    materials.make(plan)


def retry_job(job_id: str) -> bool:
    found = store.find_job(job_id)
    if found is None:
        return False
    plan, job = found
    if job.status != JobStatus.failed:
        return False
    _run_one(plan, job)
    return True
