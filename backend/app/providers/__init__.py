"""Provider registry. Everything outside this package calls get_provider() and nothing else."""
from __future__ import annotations

from app.config import settings
from app.providers.base import ImageProvider
from app.providers.cloudflare_flux import CloudflareFluxProvider
from app.providers.mock import MockProvider


def get_provider(name: str | None = None) -> ImageProvider:
    chosen = name or settings.image_provider
    if chosen == "cloudflare_flux":
        return CloudflareFluxProvider()
    return MockProvider()
