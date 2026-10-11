"""Track 2: each material is made on its own, with the right count, outline rule and PDF."""
import io
import re

from PIL import Image

from app.config import settings
from app.pipeline import jobs as job_runner
from app.pipeline import materials
from app.schemas import JobStatus


def _make(client, material, prompt, **overrides):
    body = {"material_type": material, "prompt": prompt}
    if overrides:
        body["overrides"] = overrides
    plan = client.post("/api/v1/plans", json=body).json()
    job_runner.run_plan(plan["plan_id"])
    return plan["plan_id"]


def _pdf_pages(client, plan_id):
    assert client.post(f"/api/v1/plans/{plan_id}/export").status_code == 200
    data = client.get(f"/api/v1/plans/{plan_id}/download").content
    return data, len(re.findall(rb"/Type /Page\b", data))


def test_count_is_respected_per_material(client):
    for material, prompt, count in [("colouring", "a cat", 3), ("flashcards", "farm animals", 4),
                                    ("worksheet", "counting", 2), ("poster", "healthy food", 1)]:
        pid = _make(client, material, prompt, count=count)
        st = client.get(f"/api/v1/plans/{pid}/status").json()
        assert st["total"] == count and st["completed"] == count, material


def test_outline_only_when_colour_mode_is_outline(client):
    pid = _make(client, "colouring", "a cat")           # colouring defaults to outline
    plan = job_runner.store.get(pid)
    assert materials.colour_mode_of(plan) == "outline"
    img = Image.open(io.BytesIO(client.get(f"/api/v1/jobs/{plan.jobs[0].job_id}/asset").content)).convert("RGB")
    assert set(img.getcolors(1_000_000) and [c for _, c in img.getcolors(1_000_000)]) <= {(0, 0, 0), (255, 255, 255)}
    pid2 = _make(client, "poster", "healthy food")
    assert materials.colour_mode_of(job_runner.store.get(pid2)) == "colour"
    pid3 = _make(client, "worksheet", "counting")
    assert materials.colour_mode_of(job_runner.store.get(pid3)) == "colour"


def test_prompt_changes_with_material_and_mode(client):
    a = job_runner.store.get(_make(client, "colouring", "a cat"))
    b = job_runner.store.get(_make(client, "flashcards", "farm animals"))
    assert "line drawing" in materials.build_prompt(a, a.jobs[0])
    assert "line drawing" not in materials.build_prompt(b, b.jobs[0])


def test_library_key_separates_outline_from_colour(client):
    a = job_runner.store.get(_make(client, "colouring", "a cat"))
    assert materials.library_style(a).endswith("/outline")


def test_pdf_per_material_has_resource_page(client):
    for material, prompt, count, sizes in [("colouring", "a cat", 2, (595, 842)), ("flashcards", "farm animals", 3, (216, 360)),
                                           ("worksheet", "counting", 2, (595, 842)), ("poster", "healthy food", 1, (841, 1190))]:
        pid = _make(client, material, prompt, count=count)
        data, pages = _pdf_pages(client, pid)
        assert pages == count + 1, material
        assert data.startswith(b"%PDF")
        widths = [int(float(w)) for w in re.findall(rb"/MediaBox \[ 0 0 ([\d.]+)", data)]
        assert widths[0] == sizes[0] and widths[-1] == 595, material  # first page = material size, last = A4 report
