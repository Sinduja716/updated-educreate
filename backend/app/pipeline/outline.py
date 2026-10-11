"""TRACK 2: turn an uploaded picture into grayscale or black-and-white outline (OpenCV, Pillow fallback).

to_outline(image_bytes, threshold=None) -> PNG bytes   black lines on white
to_grayscale(image_bytes)               -> PNG bytes
to_line_art(image_bytes, preset)        -> same as to_outline (kept for the old contract name)
"""
from __future__ import annotations

import io

from PIL import Image, ImageOps


def _open(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        img = bg
    return img.convert("RGB")


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def to_grayscale(image_bytes: bytes) -> bytes:
    return _png(_open(image_bytes).convert("L").convert("RGB"))


def to_outline(image_bytes: bytes, threshold: int | None = None) -> bytes:
    img = _open(image_bytes)
    try:
        import cv2
        import numpy as np

        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        if threshold is None:
            lines = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 4)
        else:  # user set a strength: Canny edges, thickened a little, drawn black on white
            edges = cv2.Canny(blur, max(1, threshold // 2), max(2, threshold))
            edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
            lines = 255 - edges
        lines = cv2.medianBlur(lines, 3)
        return _png(Image.fromarray(lines).convert("RGB"))
    except Exception:  # OpenCV missing or failed: simple Pillow version
        from app.pipeline.lineart import to_line_art as pil_line_art

        return _png(pil_line_art(img, 170 if threshold is None else int(threshold)))


def to_line_art(image_bytes: bytes, preset: str = "adaptive") -> bytes:
    return to_outline(image_bytes)
