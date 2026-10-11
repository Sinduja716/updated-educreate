"""TRACK 2: history of finished pictures (what the History page shows).

add_history(job, plan) is called when a picture finishes (generated or reused). list_history(limit, material_type)
returns newest first. Stored in MongoDB collection `history` when connected, else in the SQLite file.
A copy of the picture is kept in data/library/history/<creation_id>.png so history survives output clean-ups.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sqlite3

from app.config import settings
from app.estimate import USD_PER_1000_NEURONS
from app.pipeline import db
from app.pipeline.materials import colour_mode_of
from app.schemas import HistoryItem, Job, Plan

_SCHEMA = "CREATE TABLE IF NOT EXISTS history (creation_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)"


def _dir():
    d = settings.library_dir / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _con() -> sqlite3.Connection:
    settings.library_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.library_dir / "library.db", timeout=10)
    con.execute(_SCHEMA)
    return con


def asset_path(creation_id: str):
    return _dir() / f"{creation_id}.png"


def add_history(job: Job, plan: Plan) -> HistoryItem | None:
    src = settings.outputs_dir / plan.plan_id / f"{job.job_id}.png"
    if not src.exists():
        return None
    shutil.copyfile(src, asset_path(job.job_id))
    neurons = job.neurons if job.neurons is not None else 0.0
    age = plan.resolved.get("age_band")
    item = HistoryItem(
        creation_id=job.job_id,
        plan_id=plan.plan_id,
        job_id=job.job_id,
        material_type=plan.material_type.value,
        prompt=plan.original_prompt,
        item_key=job.item_key,
        colour_mode=colour_mode_of(plan),
        age_band=str(age.value) if age is not None else None,
        tier=job.tier,
        neurons=neurons,
        seconds=None if job.latency_ms is None else round(job.latency_ms / 1000.0, 3),
        cost_usd=round(neurons / 1000.0 * USD_PER_1000_NEURONS, 6),
        provider=job.provider,
        cache_hit=job.cache_hit,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    _store(item)
    return item


def add_upload(item: HistoryItem, png: bytes) -> HistoryItem:
    """History row for an uploaded picture (no job, no plan). The picture is kept as history/<creation_id>.png."""
    asset_path(item.creation_id).write_bytes(png)
    _store(item)
    return item


def _store(item: HistoryItem) -> None:
    doc = item.model_dump()
    mdb = db.mongo_db()
    if mdb is not None:
        mdb["history"].replace_one({"_id": item.creation_id}, {"_id": item.creation_id, **doc}, upsert=True)
    else:
        with _con() as con:
            con.execute("INSERT OR REPLACE INTO history VALUES (?,?,?)", (item.creation_id, item.created_at, json.dumps(doc)))


def list_history(limit: int = 20, material_type: str | None = None) -> list[HistoryItem]:
    mdb = db.mongo_db()
    if mdb is not None:
        query = {"material_type": material_type} if material_type else {}
        docs = mdb["history"].find(query).sort("created_at", -1).limit(limit)
        return [HistoryItem(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]
    with _con() as con:
        rows = con.execute("SELECT data FROM history ORDER BY created_at DESC").fetchall()
    items = [HistoryItem(**json.loads(r[0])) for r in rows]
    if material_type:
        items = [i for i in items if i.material_type == material_type]
    return items[:limit]


def delete_history(creation_id: str) -> None:
    if "/" in creation_id or "\\" in creation_id:
        return
    mdb = db.mongo_db()
    if mdb is not None:
        mdb["history"].delete_one({"_id": creation_id})
    else:
        with _con() as con:
            con.execute("DELETE FROM history WHERE creation_id=?", (creation_id,))
    asset_path(creation_id).unlink(missing_ok=True)


def clear_history() -> None:
    for item in list_history(100000):
        delete_history(item.creation_id)
