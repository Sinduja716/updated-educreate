import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.pipeline import db
from app.store import store


@pytest.fixture(autouse=True)
def _no_gemini(monkeypatch):
    # Tests never call Gemini, whatever .env says. test_gemini_and_images.py switches it on with a fake answer.
    monkeypatch.setattr(settings, "gemini_api_key", "")


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # Tests never call the real image service (it costs neurons) and never touch the real data folders or database.
    monkeypatch.setattr(settings, "image_provider", "mock")
    monkeypatch.setattr(settings, "library_dir", tmp_path / "lib")
    monkeypatch.setattr(settings, "outputs_dir", tmp_path / "out")
    monkeypatch.setattr(settings, "mongodb_uri", "")
    db.reset()
    store.clear()
    return TestClient(app)
