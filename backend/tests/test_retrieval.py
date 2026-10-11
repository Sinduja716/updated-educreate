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


def test_other_age_group_reuses_same_picture(client, fake):
    def run(age):
        plan = client.post("/api/v1/plans", json={"material_type": "colouring", "prompt": "a rocket", "overrides": {"count": 1, "age_band": age}}).json()
        client.post(f"/api/v1/plans/{plan['plan_id']}/generate")
        return client.get(f"/api/v1/plans/{plan['plan_id']}/metrics").json()
    assert run("3-5")["image_calls"] == 1
    again = run("9-12")
    assert again["image_calls"] == 0 and again["cache_hits"] == 1


def _run(client, material, prompt, **ov):
    plan = client.post("/api/v1/plans", json={"material_type": material, "prompt": prompt, "overrides": {"count": 1, **ov}}).json()
    client.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    return plan, client.get(f"/api/v1/plans/{plan['plan_id']}/metrics").json()


def test_related_prompt_and_other_material_reuse_stored_picture(client, fake):
    _, m = _run(client, "thumbnail", "a cute puppy")
    assert m["image_calls"] == 1
    _, m = _run(client, "thumbnail", "puppy")                      # shorter, related prompt
    assert m["image_calls"] == 0 and m["cache_hits"] == 1
    plan, m = _run(client, "auto", "a cute puppy for a colouring book")  # other material, outline wanted
    assert plan["resolved"]["colour_mode"]["value"] == "outline" and plan["material_type"] == "colouring"
    assert m["image_calls"] == 0 and m["cache_hits"] == 1          # colour picture converted to outline, 0 neurons


def test_reuse_preview_before_generating(client, fake):
    _run(client, "thumbnail", "a cute puppy")
    plan = client.post("/api/v1/plans", json={"material_type": "thumbnail", "prompt": "puppy", "overrides": {"count": 1}}).json()
    r = client.get(f"/api/v1/plans/{plan['plan_id']}/reuse").json()
    assert r["total"] == 1 and r["reusable"] == 1
    other = client.post("/api/v1/plans", json={"material_type": "thumbnail", "prompt": "a red train", "overrides": {"count": 1}}).json()
    assert client.get(f"/api/v1/plans/{other['plan_id']}/reuse").json()["reusable"] == 0
