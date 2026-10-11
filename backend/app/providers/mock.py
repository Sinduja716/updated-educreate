"""Mock provider: instant fake picture so the whole app runs with no network and no cost."""
from __future__ import annotations

import io
import time

from PIL import Image, ImageDraw

from app.estimate import neurons_for_steps
from app.providers.base import ProviderResult


class MockProvider:
    name = "mock"

    def generate(self, prompt: str, steps: int) -> ProviderResult:
        start = time.perf_counter()
        img = Image.new("RGB", (768, 1024), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 747, 1003], outline="black", width=6)
        draw.text((40, 40), prompt[:80], fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return ProviderResult(
            image_bytes=buf.getvalue(),
            mime="image/png",
            model="mock",
            steps=steps,
            latency_ms=int((time.perf_counter() - start) * 1000),
            neurons=neurons_for_steps(steps),
        )
