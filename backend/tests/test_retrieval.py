"""Track 2: retrieval order. A Fake provider counts real calls (mock never saves to the library)."""
import io

import pytest
from PIL import Image

from app.config import settings
from app.pipeline import jobs as job_runner
from app.providers.base import ProviderResult
from app.schemas import ResolvedField
from app.store import store


def _png() -> bytes:
    b = io.BytesIO()
    img = Image.new("RGB", (64, 64), "white")
    for x in range(10, 50):
        for y in range(10, 50):
            img.putpixel((x, y), (200, 40, 40))
    img.save(b, format="PNG")
    return b.getvalue()


class Fake:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, steps):
        self.calls += 1
        return ProviderResult(_png(), "image/png", "fake", steps, 1, None)


@pytest.fixture()
def fake(client, monkeypatch, tmp_path):
    f = Fake()
    monkeypatch.setattr(job_runner, "get_provider", lambda: f)
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    return f


def _go(client, material, prompt, mode=None, **over):
    body = {"material_type": material, "prompt": prompt}
    if over:
        body["overrides"] = over
    pid = client.post("/api/v1/plans", json=body).json()["plan_id"]
    plan = store.get(pid)
    if mode:
        plan.resolved["colour_mode"] = ResolvedField(value=mode, source="user")
    job_runner.run_plan(pid)
    return plan


def test_exact_reuse_costs_nothing(client, fake):
    _go(client, "flashcards", "a cheetah")
    assert fake.calls == 1
    p2 = _go(client, "flashcards", "a cheetah")
    assert fake.calls == 1 and p2.jobs[0].cache_hit and p2.jobs[0].neurons == 0 and p2.jobs[0].model == "reuse"


def test_similar_prompt_reuses(client, fake):
    _go(client, "flashcards", "a cheetah and her cub")
    p2 = _go(client, "flashcards", "cheetah with cub")
    assert fake.calls == 1 and p2.jobs[0].cache_hit and p2.jobs[0].model == "reuse-similar"


def test_unlike_prompt_generates(client, fake):
    _go(client, "flashcards", "a cheetah and her cub")
    p2 = _go(client, "flashcards", "a sleepy lion")
    assert fake.calls == 2 and not p2.jobs[0].cache_hit


def test_colour_match_changed_to_outline(client, fake):
    _go(client, "colouring", "a cheetah", mode="colour")
    p2 = _go(client, "colouring", "a cheetah")  # colouring defaults to outline
    j = p2.jobs[0]
    assert fake.calls == 1 and j.cache_hit and j.model == "reuse-outline" and j.neurons == 0
    img = Image.open(io.BytesIO(client.get(f"/api/v1/jobs/{j.job_id}/asset").content)).convert("RGB")
    assert {c for _, c in img.getcolors(100000)} <= {(0, 0, 0), (255, 255, 255)}


def test_outline_never_reused_as_colour(client, fake):
    _go(client, "colouring", "a cheetah", mode="outline")
    _go(client, "colouring", "a cheetah", mode="colour")
    assert fake.calls == 2


def test_not_enough_steps_regenerates(client, fake):
    _go(client, "worksheet", "counting", tier="draft")
    _go(client, "worksheet", "counting", tier="high")
    assert fake.calls == 2


def test_pages_of_one_request_stay_different(client, fake):
    _go(client, "colouring", "a happy dog", count=3)
    assert fake.calls == 3
