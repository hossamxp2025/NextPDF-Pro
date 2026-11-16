#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Real PDF text editing (document-level API used by the UI and the commands).

All layout, shaping and text-layer work is delegated to
:mod:`src.engine.text_engine`:

  * insertion goes through MuPDF's Story (HarfBuzz shaping, bidi) using the
    bundled OFL fonts, and the ToUnicode map of every embedded font is rebuilt
    so the inserted Arabic is searchable, extractable and exportable as
    logical Unicode;
  * replacement removes the old glyphs with a text-only redaction (images and
    vector graphics are preserved) and lays the new text out in the same box,
    grown towards the free side of the line when the new text is longer;
  * anything that cannot be done safely (rotated/vertical text) is refused
    instead of being faked with an overlay.

Text runs handed out by :class:`PDFDocument` are whole visual lines (MuPDF's
bidi segments are merged), so editing an Arabic line that contains numbers
or Latin words replaces the complete line and leaves no stale fragments.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from src.models.document import PDFDocument, TextRun, contains_rtl_text
from src.engine.text_engine import TextEngine, TextStyle, get_text_engine
from src.engine.fonts import get_font_registry, DEFAULT_ARABIC_FAMILY, DEFAULT_LATIN_FAMILY

logger = logging.getLogger("NextPDF")

DEFAULT_FONT = "Default"
ARABIC_FONT = DEFAULT_ARABIC_FAMILY
LATIN_FONT = DEFAULT_LATIN_FAMILY


def _display_fonts() -> List[str]:
    """Default entry followed by the bundled families, then system fonts."""
    try:
        names = get_font_registry().family_names()
    except Exception:  # pragma: no cover - registry failure must not kill the UI
        logger.exception("font registry unavailable")
        names = []
    return [DEFAULT_FONT] + names


_DISPLAY_FONTS = _display_fonts()


@dataclass
class TextEditResult:
    success: bool
    message: str
    run_id: Optional[str] = None
    warning: Optional[str] = None
    bbox: Optional[tuple] = None


def _has_arabic(text: str) -> bool:
    return contains_rtl_text(text)


class TextEditor:
    """Text selection, insertion, replacement and deletion on a PDFDocument."""

    def __init__(self, document: PDFDocument, engine: Optional[TextEngine] = None):
        self.doc = document
        self.engine = engine or get_text_engine()
        self._edit_history: List[dict] = []

    # ------------------------------------------------------------- selection
    def select_text_at_position(self, page_number: int, x: float, y: float) -> Optional[TextRun]:
        """Return the run at (x, y) in PDF points, or a nearby run (<= 4 pt)."""
        runs = self.doc.get_text_runs_for_page(page_number)
        if not runs:
            return None
        for run in runs:
            if run.contains(x, y):
                return run
        best = None
        best_distance = 4.0
        for run in runs:
            x0, y0, x1, y1 = run.bbox
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            distance = (dx * dx + dy * dy) ** 0.5
            if distance < best_distance:
                best_distance = distance
                best = run
        return best

    # --------------------------------------------------------------- support
    @staticmethod
    def can_edit_run(run: TextRun) -> Tuple[bool, str]:
        """Return (supported, reason)."""
        if not run or not run.text.strip():
            return False, "The selected text is not editable."
        dx, dy = run.line_dir
        if abs(dy) > 0.02 or dx <= 0.9:
            return False, "Only horizontal text can be edited safely."
        x0, y0, x1, y1 = run.bbox
        if x1 - x0 <= 0.5 or y1 - y0 <= 0.5:
            return False, "The selected text is not editable."
        return True, ""

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _style(font_family: Optional[str], font_size: float, color, direction: Optional[str],
               bold: bool, italic: bool, underline: bool = False) -> TextStyle:
        family = "" if font_family in (None, "", DEFAULT_FONT) else str(font_family)
        d = (direction or "auto").lower()
        if d not in ("rtl", "ltr"):
            d = "auto"
        r, g, b = (float(c) for c in (tuple(color) if color is not None else (0, 0, 0))[:3])
        return TextStyle(family=family, size=float(font_size), color=(r, g, b), bold=bool(bold),
                         italic=bool(italic), underline=bool(underline), direction=d)

    def _find_run(self, run_id: str) -> Tuple[Optional[TextRun], Optional[int]]:
        for pno, runs in self.doc.text_runs.items():
            for run in runs:
                if run.run_id == run_id:
                    return run, pno
        return None, None

    def _find_run_in_rect(self, page_number: int, rect: fitz.Rect) -> Optional[TextRun]:
        best = None
        best_overlap = 0.0
        for run in self.doc.get_text_runs_for_page(page_number):
            x0, y0, x1, y1 = run.bbox
            ox = max(0.0, min(x1, rect.x1) - max(x0, rect.x0))
            oy = max(0.0, min(y1, rect.y1) - max(y0, rect.y0))
            overlap = ox * oy
            if overlap > best_overlap:
                best_overlap = overlap
                best = run
        return best

    def _build_layout(self, page: fitz.Page, x: float, y: float, text: str,
                      style: TextStyle, direction: str) -> fitz.Rect:
        """Box for new text, anchored at the click point.

        The clicked point is the corner of the text itself: its left edge for
        LTR, its right edge for RTL, and its top in both cases.  The box is
        just wide enough that a single line never wraps, and is shifted up by
        the glyph overflow of the first line so the ink starts at ``y``.
        """
        page_rect = page.rect
        margin = 18.0
        width, layout_h, top = self.engine.measure_box(text, style, width=10000)
        needed = max(20.0, width + 1.0)
        height = max(layout_h, style.size * 1.3) + 2.0
        y = max(margin, min(float(y), page_rect.height - margin - height))
        y0 = max(2.0, min(y - top, page_rect.height - height - 2.0))
        if direction == "rtl":
            x = max(margin + needed, min(x, page_rect.width - margin))
            return fitz.Rect(max(margin, x - needed), y0, min(page_rect.width - margin, x), y0 + height)
        x = max(margin, min(x, page_rect.width - margin - needed))
        return fitz.Rect(x, y0, min(page_rect.width - margin, x + needed), y0 + height)

    # -------------------------------------------------------------- insertion
    def add_text(self, page_number: int, x: float, y: float, text: str,
                 font_family: str = DEFAULT_FONT, font_size: float = 14.0,
                 color: Tuple[float, float, float] = (0, 0, 0),
                 direction: Optional[str] = None, bold: bool = False,
                 italic: bool = False) -> TextEditResult:
        """Insert real, shaped text into the PDF page at (x, y)."""
        if not text or not text.strip():
            return TextEditResult(False, "Text is empty")
        page = self.doc.get_page(page_number)
        if page is None:
            return TextEditResult(False, "Page not found")
        if direction in (None, "", "auto", "AUTO"):
            direction = "rtl" if _has_arabic(text) else "ltr"
        direction = direction.lower()
        style = self._style(font_family, font_size, color, direction, bold, italic)
        style = style.copy(align="right" if direction == "rtl" else "left")
        try:
            rect = self._build_layout(page, float(x), float(y), text, style, direction)
            res = self.engine.insert_text(page, rect, text, style, shrink_to_fit=True, scale_low=0.9)
            if not res.success:
                return TextEditResult(False, f"Failed to add text: {res.message}", bbox=tuple(rect))
            if not res.fitted:
                return TextEditResult(
                    False, "The text did not fit on the page. Try a smaller font size.",
                    bbox=tuple(rect))
            self.doc.refresh()
            self.doc.is_modified = True
            new_run = self._find_run_in_rect(page_number, rect)
            run_id = new_run.run_id if new_run else None
            self._edit_history.append({
                "type": "add_text", "page_number": page_number,
                "rect": tuple(rect), "text": text, "run_id": run_id,
            })
            warning = "; ".join(res.warnings) if res.warnings else None
            return TextEditResult(True, "Text added successfully", run_id=run_id,
                                  warning=warning, bbox=tuple(res.rect or rect))
        except Exception as exc:
            logger.exception("Failed to add text on page %d", page_number)
            return TextEditResult(False, f"Failed to add text: {exc}")

    # Compatibility wrapper used by the command layer and older tests.
    def add_text_box(self, page_number: int, x: float, y: float, text: str,
                     font_name: str = DEFAULT_FONT, font_size: float = 12.0,
                     color: Tuple[float, float, float] = (0, 0, 0),
                     direction: str = "LTR", width: float = 200.0,
                     height: float = 30.0) -> TextEditResult:
        return self.add_text(page_number, x, y, text, font_name, font_size, color, direction)

    # ------------------------------------------------------------- replacement
    def replace_text_run(self, run_id: str, new_text: str,
                         font_family: Optional[str] = None,
                         font_size: Optional[float] = None,
                         color: Optional[Tuple[float, float, float]] = None,
                         bold: Optional[bool] = None,
                         italic: Optional[bool] = None,
                         direction: Optional[str] = None) -> TextEditResult:
        """Remove the old glyphs of the whole line and insert *new_text* in its box."""
        target_run, page_number = self._find_run(run_id)
        if target_run is None:
            return TextEditResult(False, "Text run not found")
        supported, reason = self.can_edit_run(target_run)
        if not supported:
            return TextEditResult(False, reason)
        page = self.doc.get_page(page_number)
        if page is None:
            return TextEditResult(False, "Page not found")

        new_size = float(font_size or target_run.font_size or 12.0)
        new_color = tuple(color) if color is not None else tuple(target_run.color)
        new_direction = (direction or target_run.direction or "auto").lower()
        if new_direction not in ("rtl", "ltr"):
            new_direction = "rtl" if _has_arabic(new_text) else "ltr"
        new_bold = bool(bold if bold is not None else target_run.bold)
        new_italic = bool(italic if italic is not None else target_run.italic)
        style = self._style(font_family, new_size, new_color, new_direction, new_bold, new_italic)
        style = style.copy(align="right" if new_direction == "rtl" else "left")
        old_rect = fitz.Rect(*target_run.bbox)
        old_text = target_run.text

        try:
            res = self.engine.replace_text(page, [old_rect], new_text, style)
            if not res.success:
                return TextEditResult(False, f"Failed to update text: {res.message}", bbox=tuple(old_rect))
            if new_text.strip() and not res.fitted:
                return TextEditResult(
                    False, "The new text did not fit in the page. Try a smaller font size.",
                    bbox=tuple(old_rect))
            self.doc.refresh()
            self.doc.is_modified = True
            new_rect = fitz.Rect(*res.rect) if res.rect else old_rect
            new_run = self._find_run_in_rect(page_number, new_rect) if new_text.strip() else None
            self._edit_history.append({
                "type": "replace_text", "run_id": run_id,
                "page_number": page_number, "old_text": old_text,
                "new_text": new_text, "bbox": tuple(old_rect),
            })
            warning = "; ".join(res.warnings) if res.warnings else None
            return TextEditResult(True, "Text updated successfully",
                                  run_id=new_run.run_id if new_run else run_id,
                                  warning=warning, bbox=tuple(new_rect))
        except Exception as exc:
            logger.exception("Failed to replace text run %s", run_id)
            return TextEditResult(False, f"Failed to update text: {exc}")

    # Compatibility wrapper: edits the model-level run and then the PDF.
    def edit_text_run(self, run_id: str, new_text: str,
                      font_name: Optional[str] = None,
                      font_size: Optional[float] = None,
                      color: Optional[Tuple[float, float, float]] = None,
                      bold: Optional[bool] = None,
                      italic: Optional[bool] = None,
                      underline: Optional[bool] = None,
                      alignment: Optional[str] = None,
                      direction: Optional[str] = None) -> TextEditResult:
        return self.replace_text_run(
            run_id, new_text, font_family=font_name, font_size=font_size,
            color=color, bold=bold, italic=italic, direction=direction,
        )

    # -------------------------------------------------------------- deletion
    def delete_text_run(self, run_id: str) -> bool:
        """Delete a run by redacting its glyph band.  Returns True on success."""
        target, page_number = self._find_run(run_id)
        if target is None:
            return False
        page = self.doc.get_page(page_number)
        if page is None:
            return False
        try:
            ok = self.engine.delete_text(page, [fitz.Rect(*target.bbox)])
            if not ok:
                return False
            self.doc.refresh()
            self.doc.is_modified = True
            self._edit_history.append({"type": "delete_text", "run_id": run_id})
            return True
        except Exception:
            logger.exception("Failed to delete text run %s", run_id)
            return False

    def commit_changes_to_pdf(self, page_number: int = 0) -> bool:
        """Compatibility: mutations already write to the file; refresh indexes."""
        try:
            self.doc.refresh()
            return True
        except Exception:
            logger.exception("Failed to refresh after text changes")
            return False

    # ------------------------------------------------------------------ misc
    def move_text_run(self, run_id: str, new_x: float, new_y: float) -> bool:
        """Moving existing PDF glyphs safely is not implemented."""
        return False

    @staticmethod
    def display_fonts() -> List[str]:
        return _display_fonts()
