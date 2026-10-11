import pytest
from app.planner import make_plan, resolve_purpose
from app.schemas import GenerationRequest, MaterialType, Overrides

def test_resolve_purpose_auto():
    req = GenerationRequest(material_type=MaterialType.auto, prompt="Make a poster for animals")
    purpose, warnings = resolve_purpose(req)
    assert purpose == MaterialType.poster
    assert any("poster" in w for w in warnings)

def test_resolve_purpose_conflict():
    req = GenerationRequest(material_type=MaterialType.colouring, prompt="Make a poster for animals")
    purpose, warnings = resolve_purpose(req)
    assert purpose == MaterialType.colouring
    assert any("poster" in w for w in warnings)

def test_make_plan_a_to_z():
    req = GenerationRequest(material_type=MaterialType.flashcards, prompt="Animals A to Z")
    plan = make_plan(req)
    assert plan.resolved["count"].value == 26
    assert plan.resolved["count"].source == "planner"
    assert len(plan.jobs) == 26
    assert plan.jobs[0].item_key == "animals:alligator"
    assert plan.jobs[25].item_key == "animals:zebra"
    assert plan.jobs[0].sequence == 1
    assert plan.jobs[25].sequence == 26

def test_make_plan_1_to_10():
    req = GenerationRequest(material_type=MaterialType.flashcards, prompt="Numbers 1 to 10")
    plan = make_plan(req)
    assert plan.resolved["count"].value == 10
    assert plan.resolved["count"].source == "planner"
    assert len(plan.jobs) == 10
    assert plan.jobs[0].item_key == "numbers:one"
    assert plan.jobs[9].item_key == "numbers:ten"

def test_make_plan_max_count_limit():
    req = GenerationRequest(material_type=MaterialType.thumbnail, prompt="Animals A to Z")
    plan = make_plan(req)
    # Thumbnail max count is 12
    assert plan.resolved["count"].value == 12
    assert len(plan.jobs) == 12
    assert any("reduced to the maximum of 12" in w for w in plan.warnings)

def test_user_override():
    req = GenerationRequest(
        material_type=MaterialType.colouring, 
        prompt="Animals A to Z",
        overrides=Overrides(count=5, tier="high")
    )
    plan = make_plan(req)
    assert plan.resolved["count"].value == 5
    assert plan.resolved["count"].source == "user"
    assert plan.resolved["tier"].value == "high"
    assert plan.resolved["tier"].source == "user"
    assert len(plan.jobs) == 5

def test_explicit_count_planner():
    req = GenerationRequest(material_type=MaterialType.worksheet, prompt="3 colours")
    plan = make_plan(req)
    assert plan.resolved["count"].value == 3
    assert plan.resolved["count"].source == "planner"
    assert plan.jobs[0].item_key == "colours:red"


def test_make_plan_shapes():
    req = GenerationRequest(material_type=MaterialType.flashcards, prompt="shapes")
    plan = make_plan(req)
    assert len(plan.jobs) == 10
    assert plan.jobs[0].item_key == "shapes:circle"

def test_make_plan_colours():
    req = GenerationRequest(material_type=MaterialType.flashcards, prompt="colours")
    plan = make_plan(req)
    assert len(plan.jobs) == 11

def test_make_plan_fruits_a_to_z():
    req = GenerationRequest(material_type=MaterialType.worksheet, prompt="fruits A to Z")
    plan = make_plan(req)
    assert len(plan.jobs) == 26
    assert plan.jobs[0].item_key == "fruits:apple"

def test_make_plan_free_text():
    req = GenerationRequest(material_type=MaterialType.flashcards, prompt="a cheetah and her cub")
    plan = make_plan(req)
    assert len(plan.jobs) == 1
    assert plan.jobs[0].item_key == "free:a-cheetah-and-her-cub-1"

