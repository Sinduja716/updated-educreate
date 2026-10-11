"""TRACK 2 owns this file: GET /api/v1/config (what the app is running with)."""
from fastapi import APIRouter

from app.config import settings
from app.pipeline import db
from app.planner import gemini
from app.schemas import ConfigResponse

router = APIRouter(prefix="/api/v1")


def _provider_configured() -> bool:
    if settings.image_provider == "cloudflare_flux":
        return bool(settings.cloudflare_account_id and settings.cloudflare_api_token)
    return True  # mock needs nothing


@router.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    return ConfigResponse(
        image_provider=settings.image_provider,
        provider_configured=_provider_configured(),
        demo_mode=settings.image_provider == "mock",
        database_connected=db.connected(),
        online_search=settings.online_search,
        planner="gemini+rules" if gemini.configured() else "rules",
    )
