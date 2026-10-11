"""TRACK 2: small document store for the web app's own data: sessions (the user's creation sessions) and preferences.

Same rule as library/history: MongoDB collection when MONGODB_URI works, else the local SQLite file.
Kinds: "sessions" (many documents, newest first) and "preferences" (one document with id "default").
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

from app.config import settings
from app.pipeline import db

_SCHEMA = "CREATE TABLE IF NOT EXISTS app_docs (kind TEXT NOT NULL, doc_id TEXT NOT NULL, updated_at TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY (kind, doc_id))"


def _con() -> sqlite3.Connection:
    settings.library_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.library_dir / "library.db", timeout=10)
    con.execute(_SCHEMA)
    return con


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def put(kind: str, doc_id: str, doc: dict) -> None:
    mdb = db.mongo_db()
    if mdb is not None:
        mdb[kind].replace_one({"_id": doc_id}, {"_id": doc_id, "updated_at": _now(), "doc": doc}, upsert=True)
        return
    with _con() as con:
        con.execute("INSERT OR REPLACE INTO app_docs VALUES (?,?,?,?)", (kind, doc_id, _now(), json.dumps(doc)))


def get(kind: str, doc_id: str) -> dict | None:
    mdb = db.mongo_db()
    if mdb is not None:
        row = mdb[kind].find_one({"_id": doc_id})
        return None if row is None else row["doc"]
    with _con() as con:
        row = con.execute("SELECT data FROM app_docs WHERE kind=? AND doc_id=?", (kind, doc_id)).fetchone()
    return None if row is None else json.loads(row[0])


def list_all(kind: str) -> list[dict]:
    mdb = db.mongo_db()
    if mdb is not None:
        return [r["doc"] for r in mdb[kind].find().sort("updated_at", -1)]
    with _con() as con:
        rows = con.execute("SELECT data FROM app_docs WHERE kind=? ORDER BY updated_at DESC", (kind,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def delete(kind: str, doc_id: str) -> None:
    mdb = db.mongo_db()
    if mdb is not None:
        mdb[kind].delete_one({"_id": doc_id})
        return
    with _con() as con:
        con.execute("DELETE FROM app_docs WHERE kind=? AND doc_id=?", (kind, doc_id))


def clear(kind: str) -> None:
    mdb = db.mongo_db()
    if mdb is not None:
        mdb[kind].delete_many({})
        return
    with _con() as con:
        con.execute("DELETE FROM app_docs WHERE kind=?", (kind,))
