"""TRACK 2: daily neuron budget guard. Cloudflare's free allowance resets at 00:00 UTC, so usage is counted
per UTC day and kept in data/budget.json (survives restarts). allow(neurons) -> bool, record(neurons)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

from app.config import settings

_lock = threading.Lock()


def _path():
    return settings.data_dir / "budget.json"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def used_today() -> float:
    try:
        raw = json.loads(_path().read_text())
        return float(raw["used"]) if raw.get("date") == _today() else 0.0
    except Exception:
        return 0.0


def remaining() -> float:
    return max(0.0, settings.daily_neuron_budget - used_today())


def allow(estimated_neurons: float = 0.0) -> bool:
    with _lock:
        return used_today() + estimated_neurons <= settings.daily_neuron_budget


def record(neurons: float) -> None:
    with _lock:
        total = used_today() + float(neurons)
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _path().write_text(json.dumps({"date": _today(), "used": round(total, 3)}))


def reserve(estimated_neurons: float) -> bool:
    """Atomic check-and-add, so two jobs running at the same time can never both pass the guard.
    Pair it with settle() (after a real answer) or release() (when the call failed)."""
    with _lock:
        if used_today() + estimated_neurons > settings.daily_neuron_budget:
            return False
        _write(used_today() + float(estimated_neurons))
        return True


def settle(reserved: float, actual: float) -> None:
    """Replace the reserved amount with what the provider really used."""
    with _lock:
        _write(max(0.0, used_today() - float(reserved) + float(actual)))


def release(reserved: float) -> None:
    with _lock:
        _write(max(0.0, used_today() - float(reserved)))


def _write(total: float) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _path().write_text(json.dumps({"date": _today(), "used": round(total, 3)}))
