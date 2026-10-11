"""TRACK 2: the one place that knows about MongoDB.

MONGODB_URI empty  -> mongo_db() returns None and library/history use the local SQLite file (tests, verify).
MONGODB_URI set    -> database `MONGODB_DB` (default "educreate"), collections `library` and `history`.
If the server cannot be reached the app does NOT crash: it falls back to SQLite and connected() is False,
so the UI banner can say so. Images always stay as PNG files on disk, never inside the database.
"""
from __future__ import annotations

import threading

from app.config import settings

_lock = threading.Lock()
_state: dict = {"uri": None, "db": None, "failed": False}


def _client_factory(uri: str):
    from pymongo import MongoClient

    return MongoClient(uri, serverSelectionTimeoutMS=2000)


def reset() -> None:
    with _lock:
        _state.update(uri=None, db=None, failed=False)


def mongo_db():
    uri = settings.mongodb_uri.strip()
    if not uri:
        return None
    with _lock:
        if _state["uri"] == uri:
            return _state["db"]
        _state.update(uri=uri, db=None, failed=False)
        try:
            client = _client_factory(uri)
            client.admin.command("ping")
            _state["db"] = client[settings.mongodb_db]
        except Exception:
            _state["failed"] = True
        return _state["db"]


def connected() -> bool:
    """True only when MongoDB is configured AND answering."""
    return mongo_db() is not None


def backend_name() -> str:
    return "mongodb" if connected() else "sqlite"
