#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comments on a page: highlights, sticky notes, free text and shapes.

These are real PDF annotations written onto the page, not a layer this
program keeps to itself, so any other reader sees them and an ordinary save
keeps them.  Every function here works on a ``pymupdf`` page and returns
plain data; nothing knows about the user interface.

One honest limitation is enforced here rather than discovered by the user:
a free-text annotation draws its own text with one of the fourteen standard
PDF fonts, none of which can shape Arabic.  PyMuPDF writes something for an
Arabic free text, but what it writes is broken (letters drop out), so that
combination is refused and the caller is told to use a sticky note, whose
text is stored as text and needs no font, or the text editor, which embeds
a real Arabic font.
"""

import logging

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

logger = logging.getLogger("NextPDF")

KIND_HIGHLIGHT = "highlight"
KIND_NOTE = "note"
KIND_FREE_TEXT = "free_text"
KIND_RECTANGLE = "rectangle"
KIND_ELLIPSE = "ellipse"
KIND_LINE = "line"

SHAPE_KINDS = (KIND_RECTANGLE, KIND_ELLIPSE, KIND_LINE)
ALL_KINDS = (KIND_HIGHLIGHT, KIND_NOTE, KIND_FREE_TEXT) + SHAPE_KINDS

HIGHLIGHT_COLOR = (1.0, 0.92, 0.23)
NOTE_COLOR = (1.0, 0.80, 0.0)
SHAPE_COLOR = (0.86, 0.15, 0.15)
TEXT_COLOR = (0.0, 0.0, 0.0)

#: PDF annotation subtypes mapped to the kinds this program offers.
_SUBTYPE_TO_KIND = {
    "Highlight": KIND_HIGHLIGHT,
    "Text": KIND_NOTE,
    "FreeText": KIND_FREE_TEXT,
    "Square": KIND_RECTANGLE,
    "Circle": KIND_ELLIPSE,
    "Line": KIND_LINE,
}

ARABIC_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
                 (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def contains_arabic(text: str) -> bool:
    return any(any(low <= ord(char) <= high for low, high in ARABIC_RANGES)
               for char in text or "")


def _describe(annot, page_number: int) -> dict:
    """One annotation as plain data the rest of the program can hold."""
    info = annot.info or {}
    rect = fitz.Rect(annot.rect)
    try:
        colors = annot.colors or {}
    except Exception:  # pragma: no cover - defensive
        colors = {}
    stroke = colors.get("stroke") or colors.get("fill") or ()
    return {
        "xref": annot.xref,
        "kind": _SUBTYPE_TO_KIND.get(annot.type[1], annot.type[1]),
        "subtype": annot.type[1],
        "page": page_number,
        "rect": (rect.x0, rect.y0, rect.x1, rect.y1),
        "content": info.get("content", ""),
        "author": info.get("title", ""),
        "color": tuple(round(float(value), 4) for value in stroke),
    }


def _finish(annot, page_number, author, content, color=None, fill=None,
            width=None, opacity=None):
    if author or content:
        annot.set_info(title=author or "", content=content or "")
    if color is not None or fill is not None:
        annot.set_colors(stroke=color, fill=fill)
    if width is not None:
        annot.set_border(width=float(width))
    if opacity is not None:
        annot.set_opacity(float(opacity))
    annot.update()
    return _describe(annot, page_number)


def add_highlight(page, rects, color=HIGHLIGHT_COLOR, author="", content=""):
    """Highlight one or more rectangles of the page."""
    quads = [fitz.Rect(rect).quad for rect in rects if fitz.Rect(rect).get_area() > 0]
    if not quads:
        raise ValueError("A highlight needs at least one area")
    annot = page.add_highlight_annot(quads=quads)
    return _finish(annot, page.number + 1, author, content, color=color)


def add_note(page, point, content, author="", color=NOTE_COLOR):
    """A sticky note: an icon on the page carrying text.

    The text is stored as text, so Arabic is kept exactly as written.
    """
    if not (content or "").strip():
        raise ValueError("A note needs some text")
    annot = page.add_text_annot(fitz.Point(point[0], point[1]), content)
    return _finish(annot, page.number + 1, author, content, color=color)


def add_free_text(page, rect, text, size=12, color=TEXT_COLOR, author="",
                  fill=None):
    """Text drawn directly on the page inside *rect*."""
    if not (text or "").strip():
        raise ValueError("A free text needs some text")
    if contains_arabic(text):
        raise ValueError(
            "A free text annotation can only use the standard PDF fonts, "
            "which cannot shape Arabic. Use a note, or add the text with the "
            "text editor.")
    box = fitz.Rect(rect)
    if box.get_area() <= 0:
        raise ValueError("A free text needs an area")
    annot = page.add_freetext_annot(box, text, fontsize=float(size),
                                    text_color=color, fill_color=fill)
    page_number = page.number + 1
    if author:
        annot.set_info(title=author, content=text)
    else:
        annot.set_info(content=text)
    annot.update()
    return _describe(annot, page_number)


def add_shape(page, rect, kind=KIND_RECTANGLE, color=SHAPE_COLOR, width=1.5,
              fill=None, author="", content=""):
    """A rectangle, an ellipse or a line across *rect*."""
    if kind not in SHAPE_KINDS:
        raise ValueError(f"Unknown shape: {kind}")
    box = fitz.Rect(rect)
    if kind == KIND_LINE:
        if box.width <= 0 and box.height <= 0:
            raise ValueError("A line needs a length")
        annot = page.add_line_annot(fitz.Point(box.x0, box.y0),
                                    fitz.Point(box.x1, box.y1))
    else:
        if box.get_area() <= 0:
            raise ValueError("A shape needs an area")
        annot = (page.add_rect_annot(box) if kind == KIND_RECTANGLE
                 else page.add_circle_annot(box))
    return _finish(annot, page.number + 1, author, content, color=color,
                   fill=fill, width=width)


def list_annotations(page) -> list:
    """Every annotation on the page, in the order the page holds them."""
    found = []
    try:
        for annot in page.annots():
            found.append(_describe(annot, page.number + 1))
    except Exception:
        logger.exception("Could not read the annotations of a page")
    return found


def find_at(page, x: float, y: float, kinds=None):
    """The topmost annotation under a point, or None.

    Later annotations are drawn over earlier ones, so the search runs
    backwards and returns what the user sees on top.
    """
    point = fitz.Point(x, y)
    for item in reversed(list_annotations(page)):
        if kinds and item["kind"] not in kinds:
            continue
        if fitz.Rect(item["rect"]).contains(point):
            return item
    return None


def _annot_by_xref(page, xref):
    for annot in page.annots():
        if annot.xref == xref:
            return annot
    return None


def delete_annotation(page, xref: int) -> bool:
    """Remove one annotation by its object number."""
    annot = _annot_by_xref(page, xref)
    if annot is None:
        return False
    page.delete_annot(annot)
    return True


def set_content(page, xref: int, content: str, author=None) -> bool:
    """Change the text an annotation carries."""
    annot = _annot_by_xref(page, xref)
    if annot is None:
        return False
    if annot.type[1] == "FreeText" and contains_arabic(content):
        raise ValueError(
            "A free text annotation can only use the standard PDF fonts, "
            "which cannot shape Arabic. Use a note, or add the text with the "
            "text editor.")
    info = annot.info or {}
    annot.set_info(title=author if author is not None else info.get("title", ""),
                   content=content or "")
    annot.update()
    return True
