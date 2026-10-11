"""Track 2: upload -> grayscale / outline, history row, limits."""
import base64
import io

from PIL import Image


def _photo(w=120, h=90) -> str:
    img = Image.new("RGB", (w, h), (30, 120, 200))
    for x in range(30, 90):
        for y in range(20, 70):
            img.putpixel((x, y), (250, 220, 40))
    b = io.BytesIO()
    img.save(b, format="PNG")
    return base64.b64encode(b.getvalue()).decode()


def _post(client, **kw):
    body = {"filename": "pic.png", "image_base64": _photo(), "mode": "outline"}
    body.update(kw)
    return client.post("/api/v1/uploads/outline", json=body)


def test_outline_upload_makes_black_and_white_and_history(client):
    r = _post(client)
    assert r.status_code == 200
    out = r.json()
    assert out["provider"] == "upload" and out["neurons"] == 0 and out["cost_usd"] == 0
    png = client.get(out["asset_uri"])
    assert png.status_code == 200
    img = Image.open(io.BytesIO(png.content)).convert("RGB")
    colours = {c for _, c in img.getcolors(1_000_000)}
    assert colours <= {(0, 0, 0), (255, 255, 255)} and (0, 0, 0) in colours
    items = client.get("/api/v1/history").json()["items"]
    assert items[0]["provider"] == "upload" and items[0]["creation_id"] == out["creation_id"]


def test_grayscale_and_threshold_modes(client):
    g = _post(client, mode="grayscale").json()
    img = Image.open(io.BytesIO(client.get(g["asset_uri"]).content)).convert("RGB")
    assert all(r == g_ == b for r, g_, b in list(img.getdata())[:500])
    assert _post(client, threshold=120).status_code == 200


def test_rejects_non_image_bad_base64_and_large_file(client):
    assert _post(client, image_base64=base64.b64encode(b"hello world").decode()).status_code == 400
    assert _post(client, image_base64="@@@not-base64@@@").status_code == 400
    big = base64.b64encode(b"x" * (5 * 1024 * 1024 + 10)).decode()
    assert _post(client, image_base64=big).status_code == 413
