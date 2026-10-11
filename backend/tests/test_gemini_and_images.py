"""Gemini help for the planner (fake answers, no network) and the finished images."""
import io
import json

import pytest
from PIL import Image

from app.config import settings
from app.pipeline import jobs as job_runner
from app.planner import gemini, make_plan
from app.schemas import GenerationRequest, MaterialType, Overrides


@pytest.fixture()
def gem(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "k")
    monkeypatch.setattr(settings, "gemini_model", "m")
    gemini._cache.clear()
    gemini._translations.clear()
    answers = {}

    def fake_post(text):
        for needle, ans in answers.items():
            if needle in text:
                return ans if isinstance(ans, str) or ans is None else json.dumps(ans)
        return None

    monkeypatch.setattr(gemini, "_post", fake_post)
    return answers


def _plan(prompt, material=MaterialType.auto, **over):
    return make_plan(GenerationRequest(material_type=material, prompt=prompt, overrides=Overrides(**over) if over else None))


def test_off_without_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert gemini.suggest("anything") is None
    assert not any("Gemini" in w for w in _plan("draw a cat").warnings)


def test_gemini_picks_material_items_age_and_colour(gem):
    gem["tiny learners"] = {"material_type": "flashcards", "colour_mode": "colour", "age_band": "3-5", "count": 4,
                            "subjects": ["cow", "pig", "hen", "sheep"], "topic": "farm animals", "reason": "a set of picture cards"}
    p = _plan("something about the farm for my tiny learners")
    assert p.material_type == MaterialType.flashcards
    assert [j.item_key for j in p.jobs] == ["farm-animals:cow", "farm-animals:pig", "farm-animals:hen", "farm-animals:sheep"]
    assert p.resolved["age_band"].value == "3-5" and p.resolved["colour_mode"].value == "colour"
    assert p.tier_reason.startswith("Detected flashcards by Gemini") and any("Gemini" in w for w in p.warnings)


def test_user_choices_beat_gemini(gem):
    gem["tiny learners"] = {"material_type": "poster", "colour_mode": "outline", "age_band": "adult", "count": 9,
                            "subjects": ["a", "b"], "topic": "x", "reason": "r"}
    p = _plan("cats for my tiny learners", MaterialType.worksheet, count=2, age_band="6-8", colour_mode="colour")
    assert p.material_type == MaterialType.worksheet and len(p.jobs) == 2
    assert p.resolved["age_band"].value == "6-8" and p.resolved["age_band"].source == "user"


def test_bad_or_failed_gemini_falls_back_to_rules(gem):
    gem["alpha"] = "this is not json"
    p = _plan("alpha draw a cat")
    assert p.material_type == MaterialType.thumbnail and p.tier_reason.startswith("Guessed")
    assert any("Gemini was not available" in w for w in p.warnings)
    gem["beta"] = {"material_type": "rocket", "colour_mode": "pink", "age_band": "99", "count": 500, "subjects": "no"}
    assert gemini.suggest("beta x") == {"material_type": None, "colour_mode": None, "age_band": None, "count": None,
                                        "subjects": [], "topic": "", "reason": ""}


def test_translate_word(gem):
    gem["Translate the single word"] = {"word": "vache"}
    assert gemini.translate_word("cow", "fr") == "vache" and gemini.translate_word("cow", "en") is None


def _raw():
    b = io.BytesIO()
    Image.new("RGB", (200, 200), (30, 160, 60)).save(b, format="PNG")
    return b.getvalue()


def test_finished_images_have_the_right_shape_and_words(client):
    shapes = {}
    for material, prompt in [("flashcards", "fruits A to Z"), ("worksheet", "counting fruits"), ("poster", "healthy food"), ("colouring", "a cat")]:
        pid = client.post("/api/v1/plans", json={"material_type": material, "prompt": prompt, "overrides": {"count": 1}}).json()["plan_id"]
        job_runner.run_plan(pid)
        j = client.get(f"/api/v1/plans/{pid}/status").json()["jobs"][0]
        img = Image.open(io.BytesIO(client.get(j["asset_uri"]).content))
        shapes[material] = img.size
    assert shapes["flashcards"] == (900, 1500)   # 3 x 5 card
    assert shapes["worksheet"] == shapes["poster"] == shapes["colouring"] == (1240, 1754)  # page shape


def test_images_zip(client):
    pid = client.post("/api/v1/plans", json={"material_type": "flashcards", "prompt": "fruits A to Z", "overrides": {"count": 3}}).json()["plan_id"]
    assert client.get(f"/api/v1/plans/{pid}/images.zip").status_code == 404  # nothing finished yet
    job_runner.run_plan(pid)
    r = client.get(f"/api/v1/plans/{pid}/images.zip")
    import zipfile
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert len(names) == 3 and names[0].startswith("flashcards-01-")
