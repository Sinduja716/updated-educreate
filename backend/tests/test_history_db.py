"""Track 2: history + library, on SQLite (default) and on MongoDB (mongomock stands in for the server)."""
import io

import pytest
from PIL import Image

from app.config import settings
from app.pipeline import db, history, library
from app.pipeline import jobs as job_runner


def _png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(b, format="PNG")
    return b.getvalue()


def _run(client, material="flashcards", prompt="farm animals", count=2):
    plan = client.post("/api/v1/plans", json={"material_type": material, "prompt": prompt, "overrides": {"count": count}}).json()
    job_runner.run_plan(plan["plan_id"])
    return plan["plan_id"]


def test_history_written_and_listed_sqlite(client):
    _run(client)
    items = client.get("/api/v1/history").json()["items"]
    assert len(items) == 2
    one = items[0]
    assert one["material_type"] == "flashcards" and one["provider"] == "mock" and one["neurons"] > 0
    assert one["cost_usd"] > 0 and one["colour_mode"] == "colour" and one["cache_hit"] is False
    assert client.get(f"/api/v1/history/{one['creation_id']}/asset").status_code == 200
    assert client.get("/api/v1/history/nope/asset").status_code == 404


def test_history_filter_limit_and_order(client):
    _run(client, "flashcards", "farm animals", 2)
    _run(client, "colouring", "a cat", 1)
    assert len(client.get("/api/v1/history?material_type=colouring").json()["items"]) == 1
    assert len(client.get("/api/v1/history?limit=2").json()["items"]) == 2
    times = [i["created_at"] for i in client.get("/api/v1/history").json()["items"]]
    assert times == sorted(times, reverse=True)


def test_config_reports_database(client, monkeypatch):
    cfg = client.get("/api/v1/config").json()
    assert cfg["database_connected"] is False and cfg["demo_mode"] is True


@pytest.fixture()
def mongo(monkeypatch, client):
    mongomock = pytest.importorskip("mongomock")  # pip install mongomock; skipped when missing
    fake = mongomock.MongoClient()
    monkeypatch.setattr(db, "_client_factory", lambda uri: fake)
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://fake")
    db.reset()
    return fake


def test_library_and_history_on_mongodb(client, mongo):
    assert db.connected() and db.backend_name() == "mongodb"
    library.save("animals:bear", "flashcards", "s/colour", "6-8", _png(), {"steps": 4})
    assert library.count() == 1
    assert library.find("animals:bear", "flashcards", "s/colour", "6-8", min_steps=4) is not None
    assert library.find("animals:bear", "flashcards", "s/colour", "6-8", min_steps=8) is None
    _run(client)
    assert mongo["educreate"]["history"].count_documents({}) == 2
    assert len(client.get("/api/v1/history").json()["items"]) == 2
    assert client.get("/api/v1/config").json()["database_connected"] is True


def test_unreachable_mongodb_falls_back_to_sqlite(client, monkeypatch):
    def boom(uri):
        raise RuntimeError("no server")

    monkeypatch.setattr(db, "_client_factory", boom)
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://nowhere")
    db.reset()
    assert db.connected() is False
    _run(client, count=1)
    assert len(client.get("/api/v1/history").json()["items"]) == 1
