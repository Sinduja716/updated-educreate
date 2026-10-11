"""TRACK 2 owns the providers package. Contract for every image provider."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderResult:
    image_bytes: bytes
    mime: str
    model: str
    steps: int
    latency_ms: int
    neurons: float | None = None  # real usage if known, otherwise None


class ProviderError(Exception):
    """Normalised error. code examples: timeout, quota, bad_request, server_error."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class ImageProvider(Protocol):
    name: str

    def generate(self, prompt: str, steps: int) -> ProviderResult: ...
