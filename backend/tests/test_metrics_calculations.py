import pytest
from app.estimate import make_estimate
from app.metrics import compute_metrics
from app.schemas import Job, JobStatus, MaterialType, Plan, ResolvedField

def mock_plan(jobs_data: list[tuple[str, bool, JobStatus]]) -> Plan:
    jobs = []
    for i, (tier, is_hit, status) in enumerate(jobs_data):
        jobs.append(
            Job(
                job_id=f"job-{i}",
                plan_id="plan-1",
                sequence=i+1,
                item_key=f"item-{i}",
                prompt="test",
                status=status,
                tier=tier,
                cache_hit=is_hit,
                estimate=make_estimate(tier)
            )
        )
    return Plan(
        plan_id="plan-1",
        material_type=MaterialType.worksheet,
        original_prompt="test",
        page_format="A4_PORTRAIT",
        profile="test",
        steps=4,
        tier="standard",
        tier_reason="test",
        estimate=make_estimate("standard"),
        resolved={},
        jobs=jobs
    )

def test_all_high_tier_no_reuse():
    plan = mock_plan([("high", False, JobStatus.completed)] * 3)
    res = compute_metrics(plan)
    assert res.saving_percent == 0.0
    assert "Of the 0.0% compute saved, 0.0% comes from choosing lower tiers and 0.0% from reusing saved images." in res.notes

def test_lower_tier_no_reuse():
    plan = mock_plan([("draft", False, JobStatus.completed)] * 2)
    res = compute_metrics(plan)
    assert res.saving_percent > 0.0
    note = [n for n in res.notes if "Of the" in n][0]
    assert "comes from choosing lower tiers" in note
    assert "0.0% from reusing saved images" in note

def test_cache_hits_and_mixed_tiers():
    plan = mock_plan([
        ("high", True, JobStatus.completed),     # 100% saved via reuse
        ("draft", False, JobStatus.completed)    # Saved via tier
    ])
    res = compute_metrics(plan)
    assert res.image_calls == 1
    assert res.cache_hits == 1
    
    note = [n for n in res.notes if "Of the" in n][0]
    # We should see positive values for both tier and reuse savings
    assert " 0.0%" not in note

def test_failed_pending_jobs_ignored():
    plan = mock_plan([
        ("high", False, JobStatus.completed),
        ("draft", False, JobStatus.failed),
        ("draft", False, JobStatus.pending)
    ])
    res = compute_metrics(plan)
    # Only 1 completed job (high tier) should be counted
    assert res.saving_percent == 0.0
    assert res.image_calls == 1

def test_zero_completed_jobs():
    plan = mock_plan([
        ("high", False, JobStatus.failed),
    ])
    res = compute_metrics(plan)
    assert res.saving_percent is None
    assert res.baseline_neurons == 0.0
    assert res.neurons_used == 0.0
    # No split note when baseline is 0
    assert not any("Of the" in n for n in res.notes)
