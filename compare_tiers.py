"""Compare ONE prompt at three quality levels (draft, standard, high) on Cloudflare FLUX.1 schnell.

Shows, for each level: the picture, the number of steps, the neurons used, the seconds it really took, the cost,
and what was saved against the maximum (high, 8 steps).

Run from the project folder with the venv active:
    python compare_tiers.py                                   (uses your prompt below, colour picture)
    python compare_tiers.py --prompt "a lion family"          (your own prompt)
    python compare_tiers.py --prompt "a cat" --outline        (black-and-white colouring-book version)
    python compare_tiers.py --mock                            (free test with fake pictures, no Cloudflare)
    python compare_tiers.py --save-table                      (also write data/library/neurons.json and timings.json)

Neurons: Cloudflare does not send the neuron count back in its reply, so we use Cloudflare's own published
price formula: 4.8 neurons per 512x512 tile + 9.6 neurons per step. A 1024x1024 picture is 4 tiles, so
2 steps = 38.4, 4 steps = 57.6, 8 steps = 96.0 neurons. You can check the real total in the Cloudflare
dashboard (Workers AI usage) before and after one run: the difference should be about 192 neurons.
"""
import argparse
import io
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402

from app.config import settings  # noqa: E402
from app.providers import get_provider  # noqa: E402
from app.providers.base import ProviderError  # noqa: E402

TIERS = [("DRAFT", 2), ("STANDARD", 4), ("HIGH", 8)]
TILES_1024 = 4                      # a 1024 x 1024 picture = 4 tiles of 512 x 512
NEURONS_PER_TILE = 4.8
NEURONS_PER_STEP = 9.6
USD_PER_1000_NEURONS = 0.011
SUFFIXES = ("", ", cute, friendly, for a children's picture book", ", child-friendly educational illustration, wholesome",
            ", simple cartoon for young children, safe for school")   # Cloudflare's filter sometimes rejects harmless prompts


def neurons_for(steps: int) -> float:
    return round(NEURONS_PER_TILE * TILES_1024 + NEURONS_PER_STEP * steps, 3)


def make_prompt(subject: str, outline: bool) -> str:
    if outline:
        return (f"black and white line drawing of {subject}, thick clean black outlines, no colour, no shading, no grey, "
                "white background, simple colouring page for children")
    return f"{subject}, cute cartoon illustration for a children's picture book, bright colours, white background"


def to_line_art(img: Image.Image, threshold: int = 170) -> Image.Image:
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    return gray.point(lambda p: 255 if p > threshold else 0, mode="1").convert("RGB")


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def generate(provider, prompt: str, steps: int):
    """Returns (PIL image, seconds). Retries a few times when Cloudflare's content filter rejects a harmless prompt."""
    last = None
    for i, suffix in enumerate(SUFFIXES):
        start = time.perf_counter()
        try:
            result = provider.generate(prompt + suffix, steps)
            seconds = time.perf_counter() - start
            return Image.open(io.BytesIO(result.image_bytes)).convert("RGB"), seconds
        except ProviderError as exc:
            last = exc
            if exc.code != "filtered":
                break
            time.sleep(0.5)
    raise last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="a cute cheetah and her cub")
    ap.add_argument("--outline", action="store_true", help="black-and-white colouring-book picture")
    ap.add_argument("--mock", action="store_true", help="free fake pictures, no Cloudflare")
    ap.add_argument("--save-table", action="store_true", help="write data/library/neurons.json and timings.json")
    args = ap.parse_args()

    if not args.mock and settings.image_provider != "cloudflare_flux":
        print("IMAGE_PROVIDER in .env is not cloudflare_flux. Set it, or run with --mock.")
        return 1
    provider = get_provider("mock" if args.mock else None)
    prompt = make_prompt(args.prompt, args.outline)
    total_planned = sum(neurons_for(s) for _, s in TIERS)

    try:
        from app.pipeline import budget
        if not args.mock and not budget.reserve(total_planned):
            print(f"Daily neuron budget would be exceeded (need {total_planned}, left {budget.remaining()}).")
            return 1
        record = budget.settle if not args.mock else None
    except Exception:
        record = None
    print(f"Prompt: {prompt}\nThis run uses about {total_planned} neurons (3 pictures).\n")

    rows = []
    for name, steps in TIERS:
        try:
            img, seconds = generate(provider, prompt, steps)
        except ProviderError as exc:
            print(f"{name}: failed ({exc.code}) {exc}")
            return 1
        if args.outline:
            img = to_line_art(img)
        n = neurons_for(steps)
        rows.append((name, steps, n, seconds, img))
        print(f"{name:9} {steps} steps | {n} neurons | {seconds:.2f}s | ${n / 1000 * USD_PER_1000_NEURONS:.5f}")
    if record:
        try:
            budget.settle(total_planned, total_planned)
        except Exception:
            pass

    max_n, max_s = rows[-1][2], rows[-1][3]
    pic_w = 400
    pad = 24
    head_h = 130
    foot_h = 110
    sheet = Image.new("RGB", (pad + 3 * (pic_w + pad), head_h + pic_w + foot_h), "white")
    d = ImageDraw.Draw(sheet)
    f, fs = font(17), font(14)
    for i, (name, steps, n, seconds, img) in enumerate(rows):
        x = pad + i * (pic_w + pad)
        save_n = (1 - n / max_n) * 100
        save_t = max(0.0, (1 - seconds / max_s) * 100) if max_s else 0.0  # a slow network round trip must not show a negative saving
        label = "Maximum quality: 0% saved" if name == "HIGH" else f"Saved {save_n:.1f}% compute, {save_t:.1f}% time vs max"
        lines = [f"{name} ({steps} steps)", f"{n} neurons   {seconds:.2f}s   ${n / 1000 * USD_PER_1000_NEURONS:.5f}", label]
        for j, line in enumerate(lines):
            d.text((x, 14 + j * 24), line, fill="black", font=f if j == 0 else fs)
        t = img.copy()
        t.thumbnail((pic_w, pic_w))
        sheet.paste(t, (x + (pic_w - t.width) // 2, head_h))
        img.save(ROOT / f"compare_{name.lower()}.png")
    total_n = sum(r[2] for r in rows)
    foot = [f"Total {total_n:.1f} neurons for the three pictures. All three at maximum quality would be {3 * max_n:.1f} neurons.",
            "Neurons = 4.8 per 512x512 tile + 9.6 per step (Cloudflare's published price). Cost = neurons / 1000 x $0.011.",
            "Seconds are measured on this run and vary a little from run to run. Cost depends on the number of steps, not on colour or content."]
    if args.mock:
        foot.insert(0, "MOCK RUN: pictures are fake, seconds are not real.")
    for j, line in enumerate(foot):
        d.text((pad, head_h + pic_w + 14 + j * 22), line, fill="black" if j == 0 else (90, 90, 90), font=fs)

    out = ROOT / "compare_tiers.png"
    try:
        sheet.save(out)
    except OSError:
        out = ROOT / f"compare_tiers_{int(time.time())}.png"
        sheet.save(out)
    print(f"\nSaved comparison sheet: {out}")

    if args.save_table and not args.mock:
        import json
        lib = settings.library_dir
        lib.mkdir(parents=True, exist_ok=True)
        (lib / "neurons.json").write_text(json.dumps({str(s): n for _, s, n, _, _ in rows}, indent=2))
        (lib / "timings.json").write_text(json.dumps({str(s): round(sec, 2) for _, s, _, sec, _ in rows}, indent=2))
        print(f"Wrote {lib / 'neurons.json'} and {lib / 'timings.json'}. The app now shows these numbers everywhere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
