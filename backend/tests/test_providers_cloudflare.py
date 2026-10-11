import base64
import io

import httpx
import pytest
from PIL import Image

from app.config import settings
from app.providers.base import ProviderError
from app.providers.cloudflare_flux import CloudflareFluxProvider


def _jpeg() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(b, format="JPEG")
    return b.getvalue()


def _provider(handler):
    return CloudflareFluxProvider(client=httpx.Client(transport=httpx.MockTransport(handler)))


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_account_id", "acc")
    monkeypatch.setattr(settings, "cloudflare_api_token", "tok")


def test_ok_json_base64():
    seen = {}

    def h(req):
        seen["body"] = req.read()
        return httpx.Response(200, json={"result": {"image": base64.b64encode(_jpeg()).decode()}, "success": True})

    r = _provider(h).generate("cat", 4)
    assert r.mime == "image/jpeg" and r.steps == 4 and b'"steps":4' in seen["body"].replace(b" ", b"")


def test_steps_clamped():
    r = _provider(lambda q: httpx.Response(200, content=_jpeg(), headers={"content-type": "image/jpeg"})).generate("x", 99)
    assert r.steps == 8


def test_quota_and_auth_and_server():
    for status, code in [(429, "quota"), (401, "auth"), (500, "server_error")]:
        with pytest.raises(ProviderError) as e:
            _provider(lambda q, s=status: httpx.Response(s, json={})).generate("x", 2)
        assert e.value.code == code


def test_timeout():
    def h(req):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(ProviderError) as e:
        _provider(h).generate("x", 2)
    assert e.value.code == "timeout"


def test_missing_keys(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_api_token", "")
    with pytest.raises(ProviderError):
        CloudflareFluxProvider().generate("x", 2)


def test_nsfw_false_positive_is_classified_filtered():
    body = {"errors": [{"message": "AiError: Input prompt contains NSFW content.", "code": 8007}], "success": False, "result": {}}
    with pytest.raises(ProviderError) as e:
        _provider(lambda q: httpx.Response(400, json=body)).generate("a cat", 2)
    assert e.value.code == "filtered"
