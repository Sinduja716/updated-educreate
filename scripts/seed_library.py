"""TRACK 2: pre-fill the reuse library ("RAG") so common requests are free at demo time.

It goes through the REAL planner and job runner, so the library keys (item, purpose, style, age band) are
exactly what a teacher's request will produce later. Every image generated here is saved by the job runner.

    python scripts/seed_library.py --dry-run                      (show what would be generated, spend nothing)
    python scripts/seed_library.py                                (seed the default list with the real provider)
    python scripts/seed_library.py --type colouring --prompt "farm animals A to Z" --tier high

Seeding at tier "high" (8 steps) lets every later request reuse the picture, because the library only reuses an
image made with at least as many steps as the request needs. It also spends neurons: check the estimate first.
Run it AFTER scripts/measure_costs.py so seeding does not disturb the measurements.
Needs meaningful item keys from the planner (Track 1): jobs with placeholder keys (item-1, item-2) are skipped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.estimate import make_estimate, neurons_for_steps  # noqa: E402
from app.pipeline import budget, library  # noqa: E402
from app.pipeline import jobs as job_runner  # noqa: E402
from app.planner import make_plan  # noqa: E402
from app.schemas import GenerationRequest, JobStatus, Overrides  # noqa: E402
from app.store import store  # noqa: E402

DEFAULT_SEEDS = [
    ("colouring", "farm animals A to Z"),
    ("flashcards", "numbers 1 to 10"),
    ("flashcards", "shapes"),
    ("flashcards", "colours"),
    ("worksheet", "fruits A to Z"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", dest="mtype", help="material type for --prompt")
    ap.add_argument("--prompt", help="seed one prompt instead of the default list")
    ap.add_argument("--tier", choices=("draft", "standard", "high"), default="high")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-mock", action="store_true", help="run with the mock provider (nothing is saved)")
    a = ap.parse_args()
    seeds = [(a.mtype, a.prompt)] if a.prompt and a.mtype else DEFAULT_SEEDS

    real = settings.image_provider != "mock"
    if not real and not a.dry_run and not a.allow_mock:
        sys.exit("IMAGE_PROVIDER is 'mock' (nothing would be saved). Set cloudflare_flux in .env or use --dry-run.")

    plans = []
    for mtype, prompt in seeds:
        req = GenerationRequest(material_type=mtype, prompt=prompt, overrides=Overrides(tier=a.tier))
        plan = make_plan(req)
        reusable = [j for j in plan.jobs if library.is_reusable(j.item_key)]
        plans.append((plan, reusable))
        print(f"[{mtype}] {prompt!r}: {len(plan.jobs)} pages, {len(reusable)} reusable keys, tier {plan.tier}")
        if len(reusable) < len(plan.jobs):
            print("   note: planner still gives placeholder item keys for some pages; those are skipped")

    new_images = 0
    for plan, reusable in plans:
        for j in reusable:
            if library.find(*job_runner._lib_key(plan, j), min_steps=j.steps) is None:
                new_images += 1
    est = make_estimate(a.tier)
    need = new_images * neurons_for_steps(est.steps)
    print(f"\nNew images to generate: {new_images}. Estimated neurons: {need:.0f}"
          f"{' (placeholder values)' if est.placeholder else ''}. Budget left today: {budget.remaining():.0f}")
    if a.dry_run:
        return
    if real and need > budget.remaining():
        sys.exit("Not enough daily budget left. Seed fewer prompts or wait for the 00:00 UTC reset.")

    for plan, reusable in plans:
        plan.jobs = reusable
        if not plan.jobs:
            continue
        store.save(plan)
        job_runner.run_plan(plan.plan_id)
        done = sum(1 for j in plan.jobs if j.status == JobStatus.completed)
        hits = sum(1 for j in plan.jobs if j.cache_hit)
        failed = [j.item_key for j in plan.jobs if j.status == JobStatus.failed]
        print(f"{plan.original_prompt!r}: {done}/{len(plan.jobs)} done, {hits} already in library, failed: {failed or 'none'}")
    print(f"\nLibrary now holds {library.count()} images. Budget used today: {budget.used_today():.0f}")
    print("Re-run the same command to retry only the failed ones (finished ones are skipped).")


if __name__ == "__main__":
    main()
