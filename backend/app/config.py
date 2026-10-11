"""Settings read from environment variables (and a local .env file). OWNER: integrator. Do not edit."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float_or_none(name: str):
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


class Settings:
    image_provider: str = os.environ.get("IMAGE_PROVIDER", "mock")
    cloudflare_account_id: str = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    cloudflare_api_token: str = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    gemini_model: str = os.environ.get("GEMINI_MODEL", "")
    daily_neuron_budget: int = _int("DAILY_NEURON_BUDGET", 8000)
    max_concurrent_jobs: int = _int("MAX_CONCURRENT_IMAGE_JOBS", 2)
    max_retries: int = _int("MAX_IMAGE_RETRIES", 2)
    request_timeout: int = _int("REQUEST_TIMEOUT_SECONDS", 60)
    # Optional, illustrative: watt-hours per 1,000 neurons. Leave empty to show relative compute only.
    energy_wh_per_1000_neurons = _float_or_none("ENERGY_WH_PER_1000_NEURONS")
    # Database. Empty MONGODB_URI = use the local SQLite file (tests and verify need no database server).
    mongodb_uri: str = os.environ.get("MONGODB_URI", "")
    mongodb_db: str = os.environ.get("MONGODB_DB", "educreate")
    online_search: bool = os.environ.get("ONLINE_SEARCH", "false").strip().lower() == "true"
    outputs_dir: Path = ROOT / "outputs"
    library_dir: Path = ROOT / "data" / "library"
    data_dir: Path = ROOT / "data"


settings = Settings()
