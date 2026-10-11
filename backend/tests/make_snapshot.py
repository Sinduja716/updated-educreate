"""INTEGRATOR ONLY. Run from backend/: python tests/make_snapshot.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_contract_snapshot import SNAPSHOT, current  # noqa: E402

SNAPSHOT.write_text(json.dumps(current(), indent=1, sort_keys=True))
print("snapshot written")
