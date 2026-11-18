"""Visible stamps: an image or typed text placed on the page.

A visible stamp is **page content**, not an annotation.  Every reader and every
printer shows it, no reader can switch it off, and an ordinary save keeps it.

What a visible stamp is **not**: it is not a digital signature.  It carries no
identity, proves nothing about who placed it, and cannot detect a later change
to the file; anyone can copy the picture out of one file and into another.
Digital signing (PKCS#12, with verification) is a separate feature and is not
implemented.  Nothing here may be presented to the user as signing.

Typed text goes through the project's own text engine, which embeds a font that
shapes Arabic, so an Arabic name is drawn correctly and stays searchable - the
standard PDF fonts used by FreeText annotations cannot do either.
"""
import logging
import os
from typing import Optional, Tuple, Union

import pymupdf as fitz

logger = logging.getLogger("NextPDF")

KIND_IMAGE = "image"
KIND_TEXT = "text"

# Below this a drag is a stray click, not an area to stamp into.
MIN_SIDE = 8.0

# A pixel at or above this in every channel counts as background when the
# caller asks for the white background of a scanned signature to be dropped.
WHITE_THRESHOLD = 235

DEFAULT_TEXT_SIZE = 18.0
DEFAULT_TEXT_COLOR = (0.05, 0.1, 0.45)

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
                  ".gif", ".pnm", ".pgm", ".ppm", ".jpx", ".jp2")


def _checked_rect(rect) -> fitz.Rect:
    box = fitz.Rect(rect)
    box.normalize()
    if box.width < MIN_SIDE or box.height < MIN_SIDE:
        raise ValueError("The stamp area is too small")
    return box


def _pixmap(image: Union[str, bytes, bytearray, os.PathLike]) -> fitz.Pixmap:
    """Read *image* from a path or from bytes, or say why it could not be read."""
    try:
        if isinstance(image, (bytes, bytearray)):
            pixmap = fitz.Pixmap(bytes(image))
        else:
            path = os.fspath(image)
            if not os.path.isfile(path):
                raise ValueError("The image file was not found")
            pixmap = fitz.Pixmap(path)
    except ValueError:
        raise
    except Exception as exc:
        logger.warning("Stamp image could not be read: %s", exc)
        raise ValueError("The image could not be read") from exc
    if pixmap.width < 1 or pixmap.height < 1:
        raise ValueError("The image could not be read")
    return pixmap


def _without_white_background(pixmap: fitz.Pixmap,
                              threshold: int = WHITE_THRESHOLD) -> fitz.Pixmap:
    """Make the near-white pixels transparent, keeping the strokes as they are.

    This is for a signature scanned on white paper.  Only the alpha channel is
    touched, so no stroke is thinned, lightened or redrawn.
    """
    if pixmap.colorspace is None:
        return pixmap
    if pixmap.colorspace.n > 3:
        pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
    source = pixmap if not pixmap.alpha else fitz.Pixmap(pixmap, 0)
    target = fitz.Pixmap(source, 1)
    samples = source.samples
    stride = source.n
    alpha = bytearray(len(samples) // stride)
    for index in range(len(alpha)):
        base = index * stride
        darkest = min(samples[base:base + min(stride, 3)])
        alpha[index] = 0 if darkest >= threshold else 255
    target.set_alpha(bytes(alpha))
    return target


def _fitted(box: fitz.Rect, width: int, height: int) -> fitz.Rect:
    """The part of *box* the image fills when its proportions are kept."""
    scale = min(box.width / width, box.height / height)
    drawn_width = width * scale
    drawn_height = height * scale
    left = box.x0 + (box.width - drawn_width) / 2.0
    top = box.y0 + (box.height - drawn_height) / 2.0
    return fitz.Rect(left, top, left + drawn_width, top + drawn_height)


def add_image_stamp(page, rect, image, keep_ratio: bool = True,
                    drop_white_background: bool = False) -> dict:
    """Draw *image* on the page inside *rect* as page content.

    With *keep_ratio* the image is centred in the area and its proportions are
    kept, and the returned rectangle is the area actually drawn into, not the
    area that was asked for.
    """
    box = _checked_rect(rect)
    pixmap = _pixmap(image)
    if drop_white_background:
        pixmap = _without_white_background(pixmap)
    drawn = _fitted(box, pixmap.width, pixmap.height) if keep_ratio else box
    page.insert_image(drawn, pixmap=pixmap, keep_proportion=False, overlay=True)
    return {"kind": KIND_IMAGE, "page": page.number + 1,
            "rect": tuple(drawn), "requested_rect": tuple(box),
            "transparent": bool(pixmap.alpha)}


def add_text_stamp(page, rect, text: str, size: float = DEFAULT_TEXT_SIZE,
                   color: Tuple[float, float, float] = DEFAULT_TEXT_COLOR,
                   family: str = "", italic: bool = True,
                   engine=None) -> dict:
    """Draw *text* on the page inside *rect* through the project's text engine.

    Arabic is shaped and the font is embedded, so the result is real text: it
    renders correctly in any reader and stays searchable.
    """
    from src.engine.text_engine import TextEngine, TextStyle

    if not str(text).strip():
        raise ValueError("The stamp needs its text")
    box = _checked_rect(rect)
    engine = engine or TextEngine()
    style = TextStyle(family=family, size=float(size), color=color,
                      italic=bool(italic), align="center", direction="auto")
    result = engine.insert_text(page, box, str(text), style)
    if not getattr(result, "success", False):
        raise ValueError(getattr(result, "message", "")
                         or "The text could not be drawn")
    return {"kind": KIND_TEXT, "page": page.number + 1,
            "rect": tuple(result.rect) if result.rect else tuple(box),
            "requested_rect": tuple(box), "text": str(text),
            "fitted": bool(getattr(result, "fitted", True)),
            "warnings": list(getattr(result, "warnings", []) or [])}


def is_image_file(path: Optional[str]) -> bool:
    """Whether *path* looks like an image this module can read."""
    if not path:
        return False
    return os.path.splitext(str(path))[1].lower() in IMAGE_SUFFIXES
