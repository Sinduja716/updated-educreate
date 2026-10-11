import io

import pytest
from PIL import Image

from app.config import settings
from app.pipeline import budget, library
from app.pipeline import jobs as job_runner
from app.providers.base import ProviderError, ProviderResult
from app.schemas import JobStatus
from app.store import store


def _png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(b, format="PNG")
    return b.getvalue()


class Fake:
    name = "fake"

    def __init__(self, fail_times=0, code="timeout"):
        self.calls = 0
        self.fail_times = fail_times
        self.code = code

    def generate(self, prompt, steps):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ProviderError(self.code)
        return ProviderResult(_png(), "image/png", "fake", steps, 1, None)


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "library_dir", tmp_path / "lib")
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "outputs_dir", tmp_path / "out")
    monkeypatch.setattr(job_runner.time, "sleep", lambda s: None)


def _plan(client, monkeypatch, fake):
    monkeypatch.setattr(job_runner, "get_provider", lambda: fake)
    plan = client.post("/api/v1/plans", json={"material_type": "flashcards", "prompt": "farm animals"}).json()
    p = store.get(plan["plan_id"])
    for j in p.jobs:  # meaningful keys, as the real planner will give
        j.item_key = f"animal:{j.sequence}"
    return p


def test_second_run_makes_zero_provider_calls(client, monkeypatch):
    fake = Fake()
    p1 = _plan(client, monkeypatch, fake)
    job_runner.run_plan(p1.plan_id)
    first = fake.calls
    assert first == len(p1.jobs) and library.count() == first
    p2 = _plan(client, monkeypatch, fake)
    job_runner.run_plan(p2.plan_id)
    assert fake.calls == first
    assert all(j.cache_hit and j.neurons == 0.0 and j.provider == "library" for j in p2.jobs)
    assert all(j.estimate.saving_percent == 100.0 for j in p2.jobs)


def test_placeholder_keys_never_reused():
    assert library.is_reusable("item-1") is False
    assert library.is_reusable("item-26") is False
    assert library.is_reusable("bear") is True
    assert library.is_reusable("a-cheetah-and-her-cub-1") is True


def test_draft_not_reused_for_high(client, monkeypatch):
    library.save("animal:x", "poster", "s", "6-8", _png(), {"steps": 2})
    assert library.find("animal:x", "poster", "s", "6-8", min_steps=8) is None
    assert library.find("animal:x", "poster", "s", "6-8", min_steps=2) is not None


def test_retry_only_retryable_and_bounded(client, monkeypatch):
    fake = Fake(fail_times=2, code="timeout")
    p = _plan(client, monkeypatch, fake)
    p.jobs = p.jobs[:1]
    job_runner.run_plan(p.plan_id)
    assert p.jobs[0].status == JobStatus.completed and p.jobs[0].attempts == 3
    bad = Fake(fail_times=99, code="bad_request")
    p2 = _plan(client, monkeypatch, bad)
    p2.jobs = p2.jobs[:1]
    p2.jobs[0].item_key = "animal:other"
    job_runner.run_plan(p2.plan_id)
    assert p2.jobs[0].status == JobStatus.failed and bad.calls == 1 and p2.jobs[0].error_code == "bad_request"


def test_budget_blocks_and_records(client, monkeypatch):
    monkeypatch.setattr(settings, "daily_neuron_budget", 100)
    fake = Fake()
    p = _plan(client, monkeypatch, fake)
    job_runner.run_plan(p.plan_id)
    done = [j for j in p.jobs if j.status == JobStatus.completed]
    blocked = [j for j in p.jobs if j.error_code == "budget"]
    assert done and blocked and budget.used_today() <= 100


def test_filter_false_positives_are_retried_with_a_different_prompt(client, monkeypatch):
    prompts = []

    class Flaky(Fake):
        def generate(self, prompt, steps):
            prompts.append(prompt)
            self.calls += 1
            if self.calls <= 3:
                raise ProviderError("filtered")
            return ProviderResult(_png(), "image/png", "fake", steps, 1, None)

    flaky = Flaky()
    p = _plan(client, monkeypatch, flaky)
    p.jobs = p.jobs[:1]
    job_runner.run_plan(p.plan_id)
    assert p.jobs[0].status == JobStatus.completed and p.jobs[0].attempts == 4
    assert len(set(prompts)) == 4  # each retry used a different wording


def test_filter_gives_up_after_bounded_retries(client, monkeypatch):
    always = Fake(fail_times=99, code="filtered")
    p = _plan(client, monkeypatch, always)
    p.jobs = p.jobs[:1]
    job_runner.run_plan(p.plan_id)
    assert p.jobs[0].status == JobStatus.failed and p.jobs[0].error_code == "filtered"
    assert always.calls == job_runner.FILTER_RETRIES + 1
