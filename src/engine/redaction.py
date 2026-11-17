#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User-facing redaction.

Redaction here means removal, not covering: the text, the line art and the
image pixels under the marked rectangle are taken out of the page's content
stream, so nothing is left to recover by selecting or extracting.  A black
box is painted in their place.

This is deliberately separate from the redaction primitive the text editor
uses in ``text_engine``, which removes only text and keeps the artwork, as an
editing step rather than a privacy one.
"""

import logging
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import pymupdf
except ImportError:  # pragma: no cover - older environments
    import fitz as pymupdf

logger = logging.getLogger("NextPDF")

#: Default fill painted over a redacted area.
BLACK = (0.0, 0.0, 0.0)

Rect = Tuple[float, float, float, float]


def find_text_rects(page, needle: str, ignore_case: bool = True) -> List[Rect]:
    """Every rectangle on *page* holding *needle*."""
    if not needle:
        return []
    flags = pymupdf.TEXT_DEHYPHENATE
    try:
        hits = page.search_for(needle, flags=flags, quads=False)
    except TypeError:  # pragma: no cover - older PyMuPDF
        hits = page.search_for(needle)
    if not hits and ignore_case:
        return []
    return [tuple(r) for r in hits]


def _apply(page, images_mode) -> None:
    try:
        page.apply_redactions(
            images=images_mode,
            graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
    except (TypeError, AttributeError):  # pragma: no cover - older PyMuPDF
        page.apply_redactions(images=images_mode)


def redact_page(page, rects: Sequence[Rect], fill=BLACK,
                remove_images: bool = True) -> int:
    """Remove everything under *rects* on *page*.  Returns how many were applied."""
    marked = 0
    for r in rects:
        rect = pymupdf.Rect(r)
        if rect.is_empty or rect.is_infinite:
            continue
        page.add_redact_annot(rect, fill=fill if fill else False)
        marked += 1
    if not marked:
        return 0
    images_mode = (
        pymupdf.PDF_REDACT_IMAGE_PIXELS if remove_images
        else pymupdf.PDF_REDACT_IMAGE_NONE
    )
    _apply(page, images_mode)
    return marked


def redact_areas(doc, areas: Dict[int, Iterable[Rect]], fill=BLACK,
                 remove_images: bool = True) -> int:
    """Apply ``{page_number: [rect, ...]}`` to an open PyMuPDF document.

    Page numbers are 1-based, matching what the viewer shows.
    """
    total = 0
    for page_number, rects in sorted(areas.items()):
        index = int(page_number) - 1
        if index < 0 or index >= doc.page_count:
            logger.warning("Redaction skipped, page %s is out of range", page_number)
            continue
        total += redact_page(doc[index], list(rects), fill=fill,
                             remove_images=remove_images)
    return total


def redact_matches(doc, needle: str, fill=BLACK, pages: Iterable[int] = None,
                   remove_images: bool = True) -> int:
    """Remove every occurrence of *needle* in the document."""
    if not needle:
        return 0
    wanted = set(int(p) for p in pages) if pages else None
    total = 0
    for index in range(doc.page_count):
        if wanted is not None and (index + 1) not in wanted:
            continue
        page = doc[index]
        hits = find_text_rects(page, needle)
        if hits:
            total += redact_page(page, hits, fill=fill, remove_images=remove_images)
    return total
