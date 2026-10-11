"""The problem statement: at least two quality tiers and a visible resource estimate per generation."""
from app.estimate import make_estimate


def test_tiers_use_different_effort():
    draft, std, high = make_estimate("draft"), make_estimate("standard"), make_estimate("high")
    assert draft.steps < std.steps < high.steps
    assert draft.neurons < std.neurons < high.neurons
    assert high.saving_percent == 0.0
    assert draft.saving_percent > std.saving_percent > 0


def test_reused_page_saves_everything():
    assert make_estimate("standard", actual_neurons=0.0).saving_percent == 100.0


def test_estimates_are_labelled():
    est = make_estimate("draft")
    assert est.notes and any("estimate" in n.lower() for n in est.notes)
    assert est.placeholder is True  # until data/library/neurons.json is measured


def test_time_is_a_second_cost_measure():
    draft, high = make_estimate("draft"), make_estimate("high")
    assert draft.seconds < high.seconds == high.max_seconds
    assert high.time_saving_percent == 0.0 and draft.time_saving_percent > 0
    assert make_estimate("standard", actual_neurons=0.0).seconds == 0.0
    assert make_estimate("standard", actual_neurons=0.0).time_saving_percent == 100.0
    assert make_estimate("draft", actual_seconds=0.5).seconds == 0.5
    assert draft.method


def test_time_saving_ignores_one_noisy_reading():
    slow = make_estimate("draft", actual_seconds=15.0)   # a slow network round trip
    assert slow.seconds == 15.0
    assert slow.time_saving_percent == make_estimate("draft").time_saving_percent > 0
