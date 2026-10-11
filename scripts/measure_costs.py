"""TRACK 2: measure the real cost of each quality tier and write the tables every estimate is built from.

Run from the repo root with the real provider configured in .env (CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN):

    python scripts/measure_costs.py --n 10

It generates N images at 2, 4 and 8 steps, times each one and writes the MEDIAN seconds to
data/library/timings.json (also saves the pictures in outputs/measure/ so you can judge quality).

Neurons are not reported in Cloudflare's reply, so read them from the dashboard (Workers AI -> usage):
note the total before a run, run ONE tier (--only 2), wait a minute, read the total again, then
(after - before) / N is the neurons per image. Pass the three results:

    python scripts/measure_costs.py --write-neurons --neurons-2 11.2 --neurons-4 20.4 --neurons-8 39.0

Never invent these numbers: the app labels estimates as placeholders until both files exist.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
import time  # noqa: E402

from app.providers.base import ProviderError  # noqa: E402
from app.providers.cloudflare_flux import CloudflareFluxProvider  # noqa: E402

PROMPTS = [
    "a cute friendly cartoon elephant for a children's colouring book, simple clean outlines, plain white background",
    "a cute friendly cartoon cat for a children's picture book, simple clean outlines, plain white background",
    "a cheerful cartoon red apple for young children, simple shapes, plain white background",
    "a friendly cartoon house with a tree for a kindergarten worksheet, simple outlines, plain white background",
    "a cute smiling cartoon fish for a children's colouring book, simple outlines, plain white background",
]
MAX_ATTEMPTS = 6  # per image; Cloudflare's content filter rejects harmless prompts at random


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="images per tier (default 10)")
    ap.add_argument("--only", type=int, choices=(2, 4, 8), help="measure just one tier")
    ap.add_argument("--write-neurons", action="store_true")
    ap.add_argument("--neurons-2", type=float)
    ap.add_argument("--neurons-4", type=float)
    ap.add_argument("--neurons-8", type=float)
    a = ap.parse_args()
    lib = settings.library_dir
    lib.mkdir(parents=True, exist_ok=True)

    if a.write_neurons:
        vals = {"2": a.neurons_2, "4": a.neurons_4, "8": a.neurons_8}
        if any(v is None or v <= 0 for v in vals.values()):
            sys.exit("Give all three: --neurons-2 --neurons-4 --neurons-8 (per image, > 0)")
        (lib / "neurons.json").write_text(json.dumps({k: float(v) for k, v in vals.items()}, indent=1))
        print("wrote", lib / "neurons.json")
        return

    provider = CloudflareFluxProvider()
    out = ROOT / "outputs" / "measure"
    out.mkdir(parents=True, exist_ok=True)
    path = lib / "timings.json"
    table = json.loads(path.read_text()) if path.exists() else {}
    for steps in ([a.only] if a.only else [2, 4, 8]):
        times, rejected = [], 0
        for i in range(a.n):
            for attempt in range(MAX_ATTEMPTS):
                try:
                    r = provider.generate(PROMPTS[i % len(PROMPTS)], steps)
                except ProviderError as exc:  # filtered / timeout / network: try again, do not count it
                    rejected += 1
                    print(f"   image {i}: attempt {attempt + 1} failed ({exc.code}), retrying")
                    time.sleep(2)
                    continue
                times.append(r.latency_ms / 1000.0)
                (out / f"steps{steps}_{i:02d}.jpg").write_bytes(r.image_bytes)
                break
        if not times:
            sys.exit(f"steps={steps}: no image succeeded; check the network and try again")
        med = round(statistics.median(times), 3)
        table[str(steps)] = med
        print(f"steps={steps}: {len(times)} images OK ({rejected} failed attempts not counted). "
              f"median {med}s (min {min(times):.2f}, max {max(times):.2f})")
        print(f"   >>> divide the dashboard's neuron increase by {len(times)} to get neurons per image for steps={steps}")
    path.write_text(json.dumps(table, indent=1))
    print("wrote", path, "- now read the neuron totals from the Cloudflare dashboard")


if __name__ == "__main__":
    main()
