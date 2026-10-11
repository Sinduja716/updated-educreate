"""Test every material and every retrieval type, with several pictures at once. Free and offline.

Run from the repo root (venv active):   python scripts/test_all_materials.py
Uses a fake image provider that SAVES to the library (the real mock does not), in a temporary folder, so your real
data, library and database are never touched and no neurons are spent.

For each material (image=colouring, flashcards, worksheet, poster) it checks:
  1 generate N pictures at once      -> N new pictures
  2 same request again               -> exact reuse, 0 new pictures
  3 reworded request (free text)     -> similar reuse
  4 colour picture, outline wanted   -> converted for free (not for worksheets: they stay in colour)
  5 higher quality than stored       -> generated again
  6 export the PDF                   -> N + 1 pages (last page = resource report)
It saves the PDFs and a picture sheet to outputs/test_all/ and prints a table. Exit code 1 if anything fails.
"""
import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.config import settings  # noqa: E402
from app.pipeline import db  # noqa: E402
from app.pipeline import jobs as job_runner  # noqa: E402
from app.providers.base import ProviderResult  # noqa: E402
from app.schemas import ResolvedField  # noqa: E402
from app.store import store  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="educreate_test_"))
settings.library_dir = TMP / "lib"
settings.outputs_dir = TMP / "out"
settings.data_dir = TMP
settings.mongodb_uri = ""
settings.image_provider = "mock"
db.reset()
OUT = ROOT / "outputs" / "test_all"
OUT.mkdir(parents=True, exist_ok=True)


class FakeProvider:
    """Draws a coloured picture with the prompt words on it. Counts real calls."""

    name = "fake"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, steps):
        self.calls += 1
        seed = sum(map(ord, prompt))
        img = Image.new("RGB", (512, 512), "white")
        d = ImageDraw.Draw(img)
        d.ellipse([60 + seed % 80, 60, 400 - seed % 60, 420], fill=((seed * 7) % 200 + 30, (seed * 3) % 200 + 30, (seed * 11) % 200 + 30), outline="black", width=8)
        d.text((20, 470), prompt[:60], fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return ProviderResult(buf.getvalue(), "image/png", "fake", steps, 5, None)


provider = FakeProvider()
job_runner.get_provider = lambda: provider
client = TestClient(app := __import__("app.main", fromlist=["app"]).app)
rows, failures, sheet = [], [], []


def run(material, prompt, expect, label, mode=None, **over):
    store.clear() if False else None
    body = {"material_type": material, "prompt": prompt}
    if over:
        body["overrides"] = over
    plan_json = client.post("/api/v1/plans", json=body).json()
    plan = store.get(plan_json["plan_id"])
    if mode:
        plan.resolved["colour_mode"] = ResolvedField(value=mode, source="user")
    before = provider.calls
    job_runner.run_plan(plan.plan_id)
    made = provider.calls - before
    jobs = plan.jobs
    models = [j.model for j in jobs]
    reused = sum(1 for j in jobs if j.cache_hit)
    done = all(j.status.value == "completed" for j in jobs)
    m = client.get(f"/api/v1/plans/{plan.plan_id}/metrics").json()
    ok = done and made == expect["made"] and reused == len(jobs) - expect["made"]
    if "model" in expect:
        ok = ok and all(x == expect["model"] for x in models if x not in ("fake",)) and expect["model"] in models
    rows.append((material, label, len(jobs), made, reused, m["neurons_used"], m["saving_percent"], "PASS" if ok else "FAIL"))
    if not ok:
        failures.append(f"{material} / {label}: made={made} reused={reused} models={set(models)}")
    return plan


def check_pdf(plan, label="pdf"):
    r = client.post(f"/api/v1/plans/{plan.plan_id}/export")
    data = client.get(f"/api/v1/plans/{plan.plan_id}/download").content if r.status_code == 200 else b""
    pages = len(re.findall(rb"/Type /Page\b", data))
    ok = pages == len(plan.jobs) + 1
    (OUT / f"{plan.material_type.value}.pdf").write_bytes(data)
    rows.append((plan.material_type.value, f"6 {label}: {pages} pages", len(plan.jobs), 0, 0, None, None, "PASS" if ok else "FAIL"))
    if not ok:
        failures.append(f"{plan.material_type.value}: pdf has {pages} pages, expected {len(plan.jobs) + 1}")
    for j in plan.jobs[:3]:
        sheet.append((plan.material_type.value, client.get(f"/api/v1/jobs/{j.job_id}/asset").content))


# material, wordlist prompt used for the multi-picture test, count, can convert to outline
CASES = [
    ("colouring", "farm animals A to Z", 4, True),
    ("flashcards", "fruits A to Z", 5, True),
    ("worksheet", "counting fruits", 3, False),
    ("poster", "healthy food for school", 2, True),
]
for material, prompt, n, can_outline in CASES:
    first = run(material, prompt, {"made": n}, f"1 generate {n} at once", count=n)
    run(material, prompt, {"made": 0, "model": "reuse"}, "2 same request again (exact reuse)", count=n)
    free = f"a happy cheetah and her cub ({material})"
    run(material, free, {"made": 1}, "3a first free-text request", count=1)
    run(material, f"{free.replace('a happy', 'happy').replace('and her', 'with')}", {"made": 0, "model": "reuse-similar"}, "3b reworded (similar reuse)", count=1)
    if can_outline:
        run(material, f"colour test {material}", {"made": 1}, "4a colour picture stored", mode="colour", count=1)
        run(material, f"colour test {material}", {"made": 0, "model": "reuse-outline"}, "4b outline wanted (converted free)", mode="outline", count=1)
    else:
        run(material, f"colour test {material}", {"made": 1}, "4a worksheet stays colour", count=1)
        run(material, f"colour test {material}", {"made": 0, "model": "reuse"}, "4b worksheet outline asked: still colour, reused", mode="outline", count=1)
    quality = {"colouring": "sleepy elephant", "flashcards": "tall giraffe", "worksheet": "green frog", "poster": "volcano eruption"}[material]
    run(material, quality, {"made": 1}, "5a draft stored", count=1, tier="draft")
    run(material, quality, {"made": 1}, "5b high wanted: generated again", count=1, tier="high")
    check_pdf(first)

# picture sheet
if sheet:
    cols = 3
    tiles = [Image.open(io.BytesIO(b)).convert("RGB").resize((256, 256)) for _, b in sheet]
    rws = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * 266, rws * 286 + 10), "white")
    d = ImageDraw.Draw(img)
    for i, ((name, _), t) in enumerate(zip(sheet, tiles)):
        x, y = (i % cols) * 266 + 5, (i // cols) * 286 + 5
        img.paste(t, (x, y + 20))
        d.text((x, y + 3), name, fill="black")
    img.save(OUT / "pictures.png")

w = [max(len(str(r[i])) for r in rows) for i in range(8)]
head = ("material", "scenario", "pics", "new", "reused", "neurons", "saved%", "result")
w = [max(a, len(h)) for a, h in zip(w, head)]
print(" | ".join(h.ljust(x) for h, x in zip(head, w)))
print("-+-".join("-" * x for x in w))
for r in rows:
    print(" | ".join(str(c).ljust(x) for c, x in zip(r, w)))
print(f"\nFake provider calls in total: {provider.calls}   Files saved in: {OUT}")
if failures:
    print("\nFAILED:\n  " + "\n  ".join(failures))
    sys.exit(1)
print("\nALL GOOD: every material and every retrieval type works.")