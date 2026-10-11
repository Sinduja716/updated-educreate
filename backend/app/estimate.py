"""Shared resource-estimate maths. OWNER: integrator. Do not edit.

Every number a user sees about compute, cost or energy comes from make_estimate(), so the planner (before
generating), the job runner (after generating) and the metrics (totals) can never disagree.

Honest by design:
- Neurons are Cloudflare's own compute unit. Until Dev 2 measures real values into
  data/library/neurons.json the table is a PLACEHOLDER and every estimate says so.
- Energy in watt-hours is shown only when ENERGY_WH_PER_1000_NEURONS is set in .env, and is labelled illustrative.
"""
from __future__ import annotations

import json

from app.config import settings
from app.schemas import ResourceEstimate, Tier

TIER_STEPS: dict[str, int] = {"draft": 2, "standard": 4, "high": 8}
MAX_TIER = "high"
USD_PER_1000_NEURONS = 0.011  # Cloudflare paid rate; an estimate for free-tier usage
PLACEHOLDER_NEURONS: dict[int, float] = {2: 30.0, 4: 50.0, 8: 90.0}
PLACEHOLDER_SECONDS: dict[int, float] = {2: 1.0, 4: 1.6, 8: 2.8}
METHOD = (
    "Neurons per image come from our measured table (steps -> neurons). Cost = neurons / 1000 x $0.011. "
    "Time = measured seconds per image. Saving = 1 - (this image / the same image at 8 steps)."
)


def neuron_table() -> tuple[dict[int, float], bool]:
    """Returns ({steps: neurons per image}, is_placeholder)."""
    path = settings.library_dir / "neurons.json"
    try:
        raw = json.loads(path.read_text())
        table = {int(k): float(v) for k, v in raw.items() if str(k).isdigit()}
        if {2, 4, 8} <= table.keys():
            return table, False
    except Exception:
        pass
    return dict(PLACEHOLDER_NEURONS), True


def _load_table(filename: str, placeholder: dict[int, float]) -> tuple[dict[int, float], bool]:
    path = settings.library_dir / filename
    try:
        raw = json.loads(path.read_text())
        table = {int(k): float(v) for k, v in raw.items() if str(k).isdigit()}
        if {2, 4, 8} <= table.keys():
            return table, False
    except Exception:
        pass
    return dict(placeholder), True


def seconds_table() -> tuple[dict[int, float], bool]:
    """Returns ({steps: seconds per image}, is_placeholder). Measured values live in data/library/timings.json."""
    return _load_table("timings.json", PLACEHOLDER_SECONDS)


def neurons_for_steps(steps: int) -> float:
    table, _ = neuron_table()
    nearest = min(table, key=lambda k: abs(k - steps))
    return table[nearest]


def _energy(neurons: float) -> float | None:
    wh = settings.energy_wh_per_1000_neurons
    return None if wh is None else round(neurons / 1000.0 * wh, 6)


def make_estimate(tier: Tier, actual_neurons: float | None = None, actual_seconds: float | None = None) -> ResourceEstimate:
    steps = TIER_STEPS[tier]
    table, placeholder = neuron_table()
    max_steps = TIER_STEPS[MAX_TIER]
    max_neurons = table[max_steps]
    neurons = float(actual_neurons) if actual_neurons is not None else table[min(table, key=lambda k: abs(k - steps))]
    stable, sec_placeholder = seconds_table()
    max_seconds = stable[max_steps]
    nearest_s = stable[min(stable, key=lambda k: abs(k - steps))]
    if actual_seconds is not None:
        seconds = float(actual_seconds)
    elif actual_neurons == 0:  # reused page: nothing was generated
        seconds = 0.0
    else:
        seconds = nearest_s
    # The time SAVING compares table values (expected seconds at this tier vs at the maximum), never one noisy
    # real reading against the table: a single slow network round trip must not erase or invent a saving.
    # `seconds` still shows how long this image really took. A reused page takes no generation time at all.
    expected = 0.0 if actual_neurons == 0 else nearest_s
    time_saving = 0.0 if max_seconds <= 0 else max(0.0, min(100.0, (1 - expected / max_seconds) * 100))
    saving = 0.0 if max_neurons <= 0 else max(0.0, min(100.0, (1 - neurons / max_neurons) * 100))
    notes = [f"Cost is an estimate at ${USD_PER_1000_NEURONS} per 1,000 neurons (Cloudflare's paid rate)."]
    if placeholder:
        notes.append("Neuron values are placeholders until they are measured.")
    if sec_placeholder:
        notes.append("Time values are placeholders until they are measured.")
    if actual_seconds is not None:
        notes.append("Time is the measured end-to-end duration of this generation.")
    if settings.energy_wh_per_1000_neurons is not None:
        notes.append(f"Energy is illustrative: assumes {settings.energy_wh_per_1000_neurons} Wh per 1,000 neurons.")
    return ResourceEstimate(
        tier=tier,
        steps=steps,
        neurons=round(neurons, 3),
        cost_usd=round(neurons / 1000.0 * USD_PER_1000_NEURONS, 6),
        energy_wh=_energy(neurons),
        max_steps=max_steps,
        max_neurons=round(max_neurons, 3),
        max_cost_usd=round(max_neurons / 1000.0 * USD_PER_1000_NEURONS, 6),
        max_energy_wh=_energy(max_neurons),
        saving_percent=round(saving, 1),
        measured=actual_neurons is not None,
        placeholder=placeholder or sec_placeholder,
        seconds=round(seconds, 3),
        max_seconds=round(max_seconds, 3),
        time_saving_percent=round(time_saving, 1),
        method=METHOD,
        notes=notes,
    )


def explain_method() -> dict:
    """Plain-language description of how every estimate is calculated (served at GET /api/v1/estimate/method)."""
    n, n_placeholder = neuron_table()
    t, t_placeholder = seconds_table()
    wh = settings.energy_wh_per_1000_neurons
    return {
        "summary": METHOD,
        "unit": "neuron = Cloudflare Workers AI's own compute unit, the same unit the free allowance and bill use",
        "maximum_setting": {"tier": MAX_TIER, "steps": TIER_STEPS[MAX_TIER]},
        "tiers": [
            {
                "tier": tier,
                "steps": steps,
                "neurons": n[min(n, key=lambda k: abs(k - steps))],
                "seconds": t[min(t, key=lambda k: abs(k - steps))],
            }
            for tier, steps in TIER_STEPS.items()
        ],
        "formulas": [
            "cost_usd = neurons / 1000 x 0.011 (Cloudflare's paid rate; free-tier use costs $0, so this is an estimate)",
            "saving_percent = (1 - neurons / neurons_at_8_steps) x 100",
            "time_saving_percent = (1 - expected_seconds_at_this_tier / expected_seconds_at_8_steps) x 100 (from the timing table; the real seconds of each image are shown separately)",
            "reused page: nothing is generated, so neurons = 0, seconds = 0 and saving = 100%",
            "request total saving = 1 - (sum of neurons actually used / (pages x neurons_at_8_steps))",
        ],
        "energy": (
            f"Illustrative only: assumes {wh} Wh per 1,000 neurons (set by the team, source cited in docs)."
            if wh is not None
            else "Not shown: no energy-per-neuron figure is published for this service, so we show relative compute instead."
        ),
        "measured": not (n_placeholder or t_placeholder),
        "caveats": [
            "Neuron values are measured by us: usage shown in the Cloudflare dashboard divided by images generated.",
            "Seconds are end-to-end time seen by our server (network included), not pure GPU time.",
            "Estimates, not invoices. Quality differences between tiers are judged separately (see calibration).",
        ],
    }
