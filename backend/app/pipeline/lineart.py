from PIL import Image, ImageOps


def to_line_art(img: Image.Image, threshold: int = 170) -> Image.Image:
    """Turn any picture into clean black outlines on white (colouring-book style)."""
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    bw = gray.point(lambda p: 255 if p > threshold else 0, mode="1")
    return bw.convert("RGB")