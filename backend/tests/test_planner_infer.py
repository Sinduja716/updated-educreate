"""Track 1 (done on Sinduja's side): colour mode, audience, ranges, settings table, honest reasons, time metrics."""
from app.planner import infer_age_band, infer_colour_mode, make_plan
from app.pipeline import jobs as job_runner
from app.schemas import GenerationRequest, MaterialType, Overrides


def plan(material, prompt, **over):
    return make_plan(GenerationRequest(material_type=material, prompt=prompt, overrides=Overrides(**over) if over else None))


def test_colour_mode_defaults_and_words():
    assert plan(MaterialType.colouring, "a cat").resolved["colour_mode"].value == "outline"
    assert plan(MaterialType.poster, "a cat").resolved["colour_mode"].value == "colour"
    p = plan(MaterialType.colouring, "a colourful parrot")
    assert p.resolved["colour_mode"].value == "colour" and p.resolved["colour_mode"].source == "planner"
    assert plan(MaterialType.flashcards, "black and white animals").resolved["colour_mode"].value == "outline"
    assert plan(MaterialType.poster, "a cat", colour_mode="outline").resolved["colour_mode"].source == "user"


def test_settings_table_changes_tier_with_colour_mode():
    assert plan(MaterialType.colouring, "a cat").tier == "draft"
    assert plan(MaterialType.colouring, "a cat", colour_mode="colour").tier == "standard"
    assert plan(MaterialType.poster, "water cycle").tier == "high"
    assert plan(MaterialType.poster, "water cycle", colour_mode="outline").tier == "standard"
    assert plan(MaterialType.flashcards, "a cat", colour_mode="outline").tier == "draft"
    p = plan(MaterialType.worksheet, "a cat", colour_mode="outline")  # never outline for worksheets
    assert p.resolved["colour_mode"].value == "colour" and any("stay in colour" in w for w in p.warnings)
    assert plan(MaterialType.poster, "water cycle", tier="draft").tier_reason == "Chosen by you."


def test_audience_sets_age_band():
    assert infer_age_band("flashcards for toddlers") == ("3-5", "toddler")
    assert infer_age_band("a worksheet for adults")[0] == "adult"
    assert infer_age_band("fractions for grade 5")[0] == "9-12"
    assert infer_age_band("a cat")[0] is None
    p = plan(MaterialType.worksheet, "counting for kindergarten")
    assert p.resolved["age_band"].value == "3-5" and p.resolved["age_band"].source == "planner"
    assert plan(MaterialType.worksheet, "counting for kindergarten", age_band="9-12").resolved["age_band"].source == "user"
    assert plan(MaterialType.worksheet, "counting").resolved["age_band"].source == "default"


def test_number_ranges():
    p = plan(MaterialType.flashcards, "numbers 1 to 5")
    assert len(p.jobs) == 5 and p.jobs[0].item_key == "numbers:one" and p.jobs[4].item_key == "numbers:five"
    p = plan(MaterialType.flashcards, "numbers 1 to 15")
    assert len(p.jobs) == 15 and p.jobs[14].item_key == "numbers:15"


def test_honest_reason_for_unclear_prompt_and_detected_for_clear_one(client):
    unclear = client.post("/api/v1/plans", json={"material_type": "auto", "prompt": "draw a cat"}).json()
    assert unclear["tier_reason"].startswith("Guessed") and "wrong" in unclear["tier_reason"]
    clear = client.post("/api/v1/plans", json={"material_type": "auto", "prompt": "a poster about the water cycle"}).json()
    assert clear["material_type"] == "poster" and clear["tier_reason"].startswith("Detected poster")


def test_metrics_have_time_fields(client):
    pid = client.post("/api/v1/plans", json={"material_type": "colouring", "prompt": "a cat", "overrides": {"count": 2}}).json()["plan_id"]
    job_runner.run_plan(pid)
    m = client.get(f"/api/v1/plans/{pid}/metrics").json()
    assert m["seconds_used"] > 0 and m["baseline_seconds"] > m["seconds_used"] and m["time_saving_percent"] > 0


def test_age_from_number_of_years():
    from app.planner import infer_age_band
    assert infer_age_band("animals for 4 year olds")[0] == "3-5"
    assert infer_age_band("maths for a 7-year-old")[0] == "6-8"
    assert infer_age_band("science for 12 year old students")[0] == "9-12"
    assert infer_age_band("safety for age 30")[0] == "adult"
    assert infer_age_band("a picture of a cat")[0] is None


def test_tier_from_words_and_auto_material():
    from app.planner import make_plan
    from app.schemas import GenerationRequest, MaterialType

    def plan(prompt, **ov):
        return make_plan(GenerationRequest(material_type=MaterialType.auto, prompt=prompt, overrides=ov or None))

    p = plan("a highly detailed poster of the solar system")
    assert p.material_type == MaterialType.poster and p.tier == "high" and "detailed" in p.tier_reason
    p = plan("a quick rough flashcard set of animals")
    assert p.material_type == MaterialType.flashcards and p.tier == "draft"
    p = plan("worksheet on fruits")
    assert p.material_type == MaterialType.worksheet and p.tier == "standard"
    p = plan("a cute puppy")
    assert p.material_type == MaterialType.thumbnail and p.tier_reason.startswith("Guessed")
    assert plan("a highly detailed poster of cats", tier="draft").tier == "draft"      # the user always wins
    assert plan("solar system for the classroom wall").material_type == MaterialType.poster
