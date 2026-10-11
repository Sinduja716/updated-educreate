"""Fails if app/schemas.py changes. Only the integrator may update the snapshot (python tests/make_snapshot.py)."""
import json
from pathlib import Path

from app import schemas

SNAPSHOT = Path(__file__).parent / "contract_snapshot.json"
MODELS = ["Overrides", "GenerationRequest", "ResolvedField", "ResourceEstimate", "Job", "Plan", "StatusResponse",
          "GenerateResponse", "ExportResponse", "MetricsResponse", "ErrorResponse", "ConfigResponse", "HistoryItem",
          "HistoryResponse", "UploadOutlineRequest", "UploadOutlineResponse"]


def current() -> dict:
    return {name: getattr(schemas, name).model_json_schema() for name in MODELS}


def test_contract_unchanged():
    expected = json.loads(SNAPSHOT.read_text())
    assert current() == expected, (
        "app/schemas.py changed. The shared data contract is frozen. "
        "Ask the integrator before changing it."
    )
