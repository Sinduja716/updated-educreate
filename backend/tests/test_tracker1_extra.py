import pytest
from app.schemas import GenerationRequest, Overrides, MaterialType, JobStatus, Job, Plan
from app.planner import make_plan
from app.metrics import compute_metrics

# ---------- Planner extra tests ----------

def test_purpose_conflict_warning():
    # User explicitly selects worksheet but prompt mentions "poster"
    req = GenerationRequest(
        material_type=MaterialType.worksheet,
        prompt="Create a poster about plants",
        overrides=None,
    )
    plan = make_plan(req)
    # Expect a warning about mismatch
    assert any("Prompt mentions" in w for w in plan.warnings)
    assert plan.material_type == MaterialType.worksheet

def test_count_override_exceeds_max():
    # Use a count that exceeds the default max for *poster* (max 3) but is within schema limit (30)
    req = GenerationRequest(
        material_type=MaterialType.poster,
        prompt="Create a poster",
        overrides=Overrides(count=10),
    )
    plan = make_plan(req)
    # The resolved count should be capped to the default maximum for poster (3)
    count_val = plan.resolved["count"].value
    assert count_val == 3
    # A warning about reduction should be present
    assert any("maximum" in w.lower() for w in plan.warnings)

def test_item_key_stable_when_subjects_present():
    # Prompt referencing a known category with subjects (animals) and a count
    req = GenerationRequest(
        material_type=MaterialType.worksheet,
        prompt="3 animals",
        overrides=None,
    )
    plan = make_plan(req)
    # Verify each job's item_key contains "category:subject"
    for job in plan.jobs:
        assert ":" in job.item_key
        cat, subj = job.item_key.split(":", 1)
        assert cat == "animals"
        # subject should be one of the animal list (sample of a few for sanity)
        assert subj in [
            "alligator", "bear", "cat", "dog", "elephant", "frog", "giraffe",
            "hippo", "iguana", "jaguar", "koala", "lemur", "monkey", "newt",
            "owl", "panda", "quail", "rabbit", "sheep", "tiger", "urchin",
            "vulture", "wolf", "xenops", "yak", "zebra",
        ]

# ---------- Metrics extra tests ----------

def mock_plan(jobs_data):
    """Create a Plan with a list of tuples (tier, cache_hit, status)."""
    from app.estimate import make_estimate
    jobs = []
    plan_id = "plan-xyz"
    for i, (tier, hit, status) in enumerate(jobs_data):
        jobs.append(
            Job(
                job_id=f"job-{i}",
                plan_id=plan_id,
                sequence=i + 1,
                item_key=f"item-{i}",
                prompt="test",
                status=status,
                tier=tier,
                cache_hit=hit,
                estimate=make_estimate(tier),
            )
        )
    return Plan(
        plan_id=plan_id,
        material_type=MaterialType.worksheet,
        original_prompt="test",
        page_format="A4_PORTRAIT",
        profile="test",
        steps=4,
        tier="standard",
        tier_reason="test",
        estimate=make_estimate("standard"),
        resolved={},
        warnings=[],
        jobs=jobs,
    )

def test_processing_jobs_ignored():
    plan = mock_plan([
        ("high", False, JobStatus.completed),
        ("draft", False, JobStatus.processing),
    ])
    res = compute_metrics(plan)
    # Only the completed job should count toward calls and savings
    assert res.image_calls == 1
    assert res.cache_hits == 0

def test_empty_plan_metrics():
    # Build a plan with no jobs at all
    from app.estimate import make_estimate
    plan = Plan(
        plan_id="empty",
        material_type=MaterialType.worksheet,
        original_prompt="",
        page_format="A4_PORTRAIT",
        profile="test",
        steps=0,
        tier="draft",
        tier_reason="",
        estimate=make_estimate("draft"),
        resolved={},
        warnings=[],
        jobs=[],
    )
    res = compute_metrics(plan)
    # Baseline and savings should be zero/None and no split note present
    assert res.baseline_neurons == 0.0
    assert res.saving_percent is None
    assert not any("Of the" in n for n in res.notes)
