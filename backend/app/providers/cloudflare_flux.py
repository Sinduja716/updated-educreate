"""TRACK 2: Cloudflare Workers AI FLUX.1 schnell provider (REST, httpx).

Endpoint: POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell
Body: {"prompt": str, "steps": int (1-8)}.  Normal JSON reply: {"result": {"image": "<base64 JPEG>"}, "success": true, ...}.
The parser also accepts a few other shapes (raw image bytes, "image" at top level) so a small API change
does not break the demo. Cloudflare does not report neurons in the reply, so `neurons` stays None and the
estimate comes from data/library/neurons.json (measure it from the dashboard) or the placeholder table.
"""
from __future__ import annotations

import base64
import time

import httpx

from app.config import settings
from app.providers.base import ProviderError, ProviderResult

MODEL = "@cf/black-forest-labs/flux-1-schnell"
BASE = "https://api.cloudflare.com/client/v4/accounts"


def _sniff_mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _extract_image(resp: httpx.Response) -> bytes:
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return resp.content
    try:
        body = resp.json()
    except ValueError as exc:
        raise ProviderError("server_error", "reply was not JSON or an image") from exc
    if isinstance(body, dict) and body.get("success") is False:
        errors = body.get("errors") or []
        msg = "; ".join(str(e.get("message", e)) if isinstance(e, dict) else str(e) for e in errors)
        low = msg.lower()
        if "nsfw" in low or any(isinstance(e, dict) and e.get("code") == 8007 for e in errors):
            raise ProviderError("filtered", msg or "prompt rejected by Cloudflare's content filter")
        code = "quota" if ("limit" in low or "quota" in low or "neuron" in low) else "bad_request"
        raise ProviderError(code, msg or "Cloudflare reported failure")
    result = body.get("result", body) if isinstance(body, dict) else body
    b64 = result.get("image") if isinstance(result, dict) else None
    if not b64 and isinstance(body, dict):
        b64 = body.get("image")
    if not b64 or not isinstance(b64, str):
        raise ProviderError("server_error", "no image field in reply")
    if "," in b64[:64]:  # data URL prefix
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError("server_error", "image was not valid base64") from exc


class CloudflareFluxProvider:
    name = "cloudflare_flux"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def generate(self, prompt: str, steps: int) -> ProviderResult:
        if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
            raise ProviderError("bad_request", "CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN not set in .env")
        steps = max(1, min(8, int(steps)))
        url = f"{BASE}/{settings.cloudflare_account_id}/ai/run/{MODEL}"
        headers = {"Authorization": f"Bearer {settings.cloudflare_api_token}"}
        start = time.perf_counter()
        try:
            if self._client is not None:
                resp = self._client.post(url, headers=headers, json={"prompt": prompt[:2000], "steps": steps})
            else:
                with httpx.Client(timeout=settings.request_timeout) as c:
                    resp = c.post(url, headers=headers, json={"prompt": prompt[:2000], "steps": steps})
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout", "Cloudflare request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("server_error", f"network error: {type(exc).__name__}") from exc

        if resp.status_code in (401, 403):
            raise ProviderError("auth", "Cloudflare rejected the token (check account id / token permissions)")
        if resp.status_code == 429:
            raise ProviderError("quota", "Cloudflare rate or daily limit reached")
        if resp.status_code >= 500:
            raise ProviderError("server_error", f"Cloudflare error {resp.status_code}")
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text[:200]
            text = str(detail).lower()
            if "nsfw" in text or "'code': 8007" in text:  # flaky false positives on harmless prompts
                raise ProviderError("filtered", f"{resp.status_code}: {detail}")
            raise ProviderError("bad_request", f"{resp.status_code}: {detail}")

        data = _extract_image(resp)
        return ProviderResult(
            image_bytes=data,
            mime=_sniff_mime(data),
            model="flux-1-schnell",
            steps=steps,
            latency_ms=int((time.perf_counter() - start) * 1000),
            neurons=None,
        )
