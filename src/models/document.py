#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Document model for NextPDF Pro.

The model wraps a PyMuPDF document and keeps an index of text/image elements
used by the UI.  Editing operations in this repair write to the real PDF
content stream immediately; the element index is refreshed from the file so
the UI never shows stale geometry.
"""

import copy
import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

try:  # PyMuPDF >= 1.24 exposes the package as pymupdf
    import pymupdf as fitz
except ImportError:  # pragma: no cover - older environments
    import fitz

logger = logging.getLogger("NextPDF")

# Arabic block, supplement, and the presentation forms MuPDF returns when it
# extracts shaped glyphs (the app's own inserted text is stored shaped).
_RTL_RANGES = (
    ("\u0600", "\u06FF"),
    ("\u0750", "\u077F"),
    ("\uFB50", "\uFDFF"),
    ("\uFE70", "\uFEFF"),
)


def contains_rtl_text(text: str) -> bool:
    """True when the string has Arabic letters in logical or shaped form."""
    return any(lo <= ch <= hi for ch in text for lo, hi in _RTL_RANGES)


@dataclass
class TextRun:
    """A span of text with its PDF geometry and formatting."""

    text: str
    x: float
    y: float
    font_name: str = "Helvetica"
    font_size: float = 12.0
    color: tuple = (0, 0, 0)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    alignment: str = "left"
    direction: str = "LTR"
    line_spacing: float = 1.2
    char_spacing: float = 0.0
    rotation: float = 0.0
    opacity: float = 1.0
    width: float = 0.0
    height: float = 0.0
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = 0
    bbox: tuple = (0.0, 0.0, 0.0, 0.0)   # x0, y0, x1, y1 in PDF points
    origin: tuple = (0.0, 0.0)            # baseline start
    line_dir: tuple = (1.0, 0.0)          # writing direction vector

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": list(self.color),
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "alignment": self.alignment,
            "direction": self.direction,
            "line_spacing": self.line_spacing,
            "char_spacing": self.char_spacing,
            "rotation": self.rotation,
            "opacity": self.opacity,
            "width": self.width,
            "height": self.height,
            "run_id": self.run_id,
            "page_number": self.page_number,
            "bbox": list(self.bbox),
            "origin": list(self.origin),
            "line_dir": list(self.line_dir),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextRun":
        data = dict(data)
        for key in ("bbox", "origin", "line_dir", "color"):
            if key in data and isinstance(data[key], list):
                data[key] = tuple(data[key])
        return cls(**data)

    def contains(self, x: float, y: float) -> bool:
        x0, y0, x1, y1 = self.bbox
        if x1 <= x0 or y1 <= y0:
            x0, y0, x1, y1 = self.x, self.y - self.height, self.x + self.width, self.y
        return x0 <= x <= x1 and y0 <= y <= y1


@dataclass
class ImageElement:
    xref: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0
    opacity: float = 1.0
    z_order: int = 0
    image_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = 0
    source_path: Optional[str] = None
    bbox: tuple = (0.0, 0.0, 0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "xref": self.xref,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "opacity": self.opacity,
            "z_order": self.z_order,
            "image_id": self.image_id,
            "page_number": self.page_number,
            "source_path": self.source_path,
            "bbox": list(self.bbox),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageElement":
        data = dict(data)
        if "bbox" in data and isinstance(data["bbox"], list):
            data["bbox"] = tuple(data["bbox"])
        return cls(**data)


@dataclass
class ShapeElement:
    shape_type: str = "rect"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0
    stroke_color: tuple = (0, 0, 0)
    fill_color: Optional[tuple] = None
    stroke_width: float = 1.0
    opacity: float = 1.0
    z_order: int = 0
    shape_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shape_type": self.shape_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "stroke_color": list(self.stroke_color),
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_width": self.stroke_width,
            "opacity": self.opacity,
            "z_order": self.z_order,
            "shape_id": self.shape_id,
            "page_number": self.page_number,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShapeElement":
        return cls(**data)


@dataclass
class PageInfo:
    page_number: int
    width: float
    height: float
    rotation: int = 0
    thumb_pixmap: Optional[Any] = None
    has_content: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "has_content": self.has_content,
        }


@dataclass
class Annotation:
    annotation_type: str = "text"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    color: tuple = (1, 1, 0)
    content: str = ""
    author: str = ""
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    annotation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_type": self.annotation_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "color": list(self.color),
            "content": self.content,
            "author": self.author,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "annotation_id": self.annotation_id,
            "page_number": self.page_number,
        }


class PDFDocument:
    """A loaded PDF with element indexes and safe save/restore primitives."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path: Optional[str] = file_path
        self.original_path: Optional[str] = file_path
        self.doc: Optional[fitz.Document] = None
        self.pages: List[PageInfo] = []
        self.text_runs: Dict[int, List[TextRun]] = {}
        self.images: Dict[int, List[ImageElement]] = {}
        self.shapes: Dict[int, List[ShapeElement]] = {}
        self.annotations: Dict[int, List[Annotation]] = {}
        self.is_modified: bool = False
        self.metadata: Dict[str, str] = {}
        self.page_count: int = 0
        self._backup_path: Optional[str] = None
        self.last_error: Optional[str] = None
        self.needs_password: bool = False

    # ------------------------------------------------------------------ load
    def load(self, file_path: str) -> bool:
        """Open *file_path*.  Never raises for user input errors."""
        self.last_error = None
        self.needs_password = False
        try:
            if self.doc is not None:
                self.close()

            if not os.path.exists(file_path):
                self.last_error = "File does not exist"
                logger.error("PDF does not exist: %s", file_path)
                return False
            if os.path.getsize(file_path) == 0:
                self.last_error = "File is empty"
                logger.error("Empty PDF: %s", file_path)
                return False

            self.doc = fitz.open(file_path)
            if getattr(self.doc, "needs_pass", False):
                self.needs_password = True
                self.last_error = "Document is encrypted"
                logger.warning("Encrypted PDF requires a password: %s", file_path)
                self.doc.close()
                self.doc = None
                return False
            if not self.doc.is_pdf:
                self.last_error = "Unsupported file"
                self.doc.close()
                self.doc = None
                return False

            self.file_path = file_path
            self.original_path = file_path
            self._refresh_models()
            self.is_modified = False
            logger.info("Loaded PDF: %s (%d pages)", file_path, self.page_count)
            return True
        except Exception as exc:  # corrupt files must not crash the app
            self.last_error = f"Failed to open file: {exc}"
            logger.exception("Failed to load PDF %s", file_path)
            try:
                if self.doc is not None:
                    self.doc.close()
            except Exception:
                pass
            self.doc = None
            return False

    def _refresh_models(self) -> None:
        if self.doc is None:
            self.page_count = 0
            self.pages = []
            self.text_runs = {}
            self.images = {}
            return
        self.page_count = self.doc.page_count
        try:
            self.metadata = dict(self.doc.metadata or {})
        except Exception:
            self.metadata = {}
        self.pages = []
        for i in range(self.page_count):
            page = self.doc[i]
            rect = page.rect
            self.pages.append(
                PageInfo(
                    page_number=i + 1,
                    width=rect.width,
                    height=rect.height,
                    rotation=page.rotation,
                    has_content=bool(page.get_contents()),
                )
            )
        self._extract_text_runs()
        self._extract_images()

    def refresh(self) -> None:
        """Re-read page and element data after a content change."""
        self._refresh_models()

    def close(self) -> None:
        if self.doc is not None:
            try:
                self.doc.close()
            except Exception:
                logger.warning("Failed to close document cleanly", exc_info=True)
            self.doc = None
        self.pages = []
        self.text_runs = {}
        self.images = {}
        self.shapes = {}
        self.annotations = {}
        self.page_count = 0
        self.is_modified = False
        self.file_path = None

    # ------------------------------------------------------------ extraction
    def _extract_text_runs(self) -> None:
        """Index one TextRun per visual line.

        MuPDF reports a bidi line as several 'lines' (one per direction
        segment).  The text engine merges them back into one visual line with
        logical, normalised text, so the UI selects, shows and replaces whole
        lines; editing a fragment of an Arabic line would leave stale glyphs.
        """
        from src.engine.text_engine import get_text_engine

        engine = get_text_engine()
        self.text_runs = {}
        for page_num in range(self.page_count):
            page = self.doc[page_num]
            runs: List[TextRun] = []
            try:
                for line in engine.extract_lines(page):
                    if not line.text.strip():
                        continue
                    lead = max(line.spans, key=lambda s: (s.bbox[2] - s.bbox[0]) * len(s.text))
                    bbox = tuple(float(v) for v in line.bbox)
                    run = TextRun(
                        text=line.text,
                        x=bbox[0],
                        y=bbox[3],
                        font_name=lead.font or "Helvetica",
                        font_size=float(lead.size or 12),
                        color=tuple(lead.color),
                        bold=bool(lead.bold),
                        italic=bool(lead.italic),
                        width=bbox[2] - bbox[0],
                        height=bbox[3] - bbox[1],
                        page_number=page_num + 1,
                        bbox=bbox,
                        origin=tuple(float(v) for v in (lead.origin or (bbox[0], bbox[3]))),
                        line_dir=tuple(line.dir),
                        direction="RTL" if line.direction == "rtl" else "LTR",
                    )
                    runs.append(run)
            except Exception:
                logger.warning("Failed to extract text from page %d", page_num + 1, exc_info=True)
            self.text_runs[page_num + 1] = runs

    def _extract_images(self) -> None:
        self.images = {}
        for page_num in range(self.page_count):
            page = self.doc[page_num]
            imgs: List[ImageElement] = []
            try:
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    for rect in page.get_image_rects(xref):
                        imgs.append(
                            ImageElement(
                                xref=xref,
                                x=rect.x0,
                                y=rect.y0,
                                width=rect.width,
                                height=rect.height,
                                page_number=page_num + 1,
                                bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                            )
                        )
            except Exception:
                logger.warning("Failed to extract images from page %d", page_num + 1, exc_info=True)
            self.images[page_num + 1] = imgs

    # --------------------------------------------------------------- geometry
    def get_page(self, page_number: int) -> Optional[fitz.Page]:
        if self.doc is None or not (1 <= page_number <= self.page_count):
            return None
        return self.doc[page_number - 1]

    def get_text_runs_for_page(self, page_number: int) -> List[TextRun]:
        return self.text_runs.get(page_number, [])

    def get_images_for_page(self, page_number: int) -> List[ImageElement]:
        return self.images.get(page_number, [])

    def get_shapes_for_page(self, page_number: int) -> List[ShapeElement]:
        return self.shapes.get(page_number, [])

    def get_annotations_for_page(self, page_number: int) -> List[Annotation]:
        return self.annotations.get(page_number, [])

    # ------------------------------------------------------------- mutations
    def add_text_run(self, page_number: int, text_run: TextRun) -> None:
        self.text_runs.setdefault(page_number, []).append(text_run)
        self.is_modified = True

    def update_text_run(self, run_id: str, updates: Dict[str, Any]) -> bool:
        for runs in self.text_runs.values():
            for run in runs:
                if run.run_id == run_id:
                    for key, value in updates.items():
                        if hasattr(run, key):
                            setattr(run, key, value)
                    self.is_modified = True
                    return True
        return False

    def delete_text_run(self, run_id: str) -> bool:
        for page_num in list(self.text_runs.keys()):
            remaining = [r for r in self.text_runs[page_num] if r.run_id != run_id]
            if len(remaining) != len(self.text_runs[page_num]):
                self.text_runs[page_num] = remaining
                self.is_modified = True
                return True
        return False

    def add_image(self, page_number: int, image: ImageElement) -> None:
        self.images.setdefault(page_number, []).append(image)
        self.is_modified = True

    def add_shape(self, page_number: int, shape: ShapeElement) -> None:
        self.shapes.setdefault(page_number, []).append(shape)
        self.is_modified = True

    def add_annotation(self, page_number: int, annotation: Annotation) -> None:
        self.annotations.setdefault(page_number, []).append(annotation)
        self.is_modified = True

    # ------------------------------------------------------------------ save
    def _metadata_for_save(self) -> Dict[str, str]:
        meta = {k: v for k, v in (self.metadata or {}).items() if isinstance(v, str)}
        meta.setdefault("creator", "NextPDF Pro")
        meta.setdefault("producer", "NextPDF Pro (PyMuPDF)")
        return meta

    def save(self, output_path: Optional[str] = None, incremental: bool = False) -> bool:
        """
        Save the document.

        A full save is always used.  It is written to a temporary file in the
        destination directory and atomically moved into place, which avoids
        PyMuPDF's restriction that incremental saves cannot garbage-collect.
        """
        self.last_error = None
        if self.doc is None:
            self.last_error = "No document to save"
            return False
        output_path = output_path or self.file_path
        if not output_path:
            self.last_error = "No output path specified"
            return False
        output_path = os.path.abspath(output_path)
        out_dir = os.path.dirname(output_path) or "."
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as exc:
            self.last_error = f"Cannot create output directory: {exc}"
            logger.error(self.last_error)
            return False

        backup_requested = bool(self.original_path and os.path.abspath(self.original_path) == output_path)
        tmp_fd, tmp_path = tempfile.mkstemp(prefix=".nextpdf_", suffix=".pdf", dir=out_dir)
        os.close(tmp_fd)
        try:
            try:
                self.doc.set_metadata(self._metadata_for_save())
            except Exception:
                logger.debug("Could not update metadata", exc_info=True)
            self._subset_fonts()
            self.doc.save(tmp_path, garbage=4, deflate=True, clean=True)
            if self.doc is not None:
                self.doc.close()
                self.doc = None
            if backup_requested:
                self._backup_path = output_path + ".bak"
                try:
                    shutil.copy2(output_path, self._backup_path)
                except Exception:
                    logger.warning("Could not create backup %s", self._backup_path, exc_info=True)
            os.replace(tmp_path, output_path)
            self.doc = fitz.open(output_path)
            self.file_path = output_path
            self.original_path = output_path
            self.is_modified = False
            self._refresh_models()
            logger.info("Saved PDF to %s", output_path)
            return True
        except Exception as exc:
            self.last_error = f"Failed to save file: {exc}"
            logger.exception("Failed to save PDF to %s", output_path)
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
            # Try to keep the in-memory document usable.
            if self.doc is None and self.original_path and os.path.exists(self.original_path):
                try:
                    self.doc = fitz.open(self.original_path)
                    self._refresh_models()
                except Exception:
                    pass
            return False

    def _subset_fonts(self) -> None:
        """Collapse the full font copies MuPDF's Story embeds on every text
        insertion into one subset per font.  Verified to keep the rebuilt
        ToUnicode maps (search/extraction identical before and after); on any
        failure the document is saved with the full fonts instead."""
        if self.doc is None:
            return
        try:
            story_fonts = 0
            for pno in range(self.doc.page_count):
                for f in self.doc[pno].get_fonts(full=True):
                    if len(f) > 5 and f[2] == "Type0" and f[5] == "Identity-H":
                        story_fonts += 1
            if story_fonts:
                self.doc.subset_fonts()
        except Exception:
            logger.warning("Font subsetting skipped", exc_info=True)

    def save_as(self, output_path: str) -> bool:
        return self.save(output_path=output_path, incremental=False)

    def to_bytes(self) -> Optional[bytes]:
        """Serialise the current in-memory state for undo snapshots."""
        if self.doc is None:
            return None
        try:
            return self.doc.tobytes(garbage=4, deflate=True)
        except Exception:
            logger.exception("Failed to serialise document")
            return None

    def restore_from_bytes(self, data: bytes) -> bool:
        if not data:
            return False
        try:
            old_path = self.file_path or self.original_path
            if self.doc is not None:
                self.doc.close()
            self.doc = fitz.open(stream=data, filetype="pdf")
            self.file_path = old_path
            self.original_path = old_path
            self._refresh_models()
            self.is_modified = True
            return True
        except Exception:
            logger.exception("Failed to restore document snapshot")
            return False

    # ------------------------------------------------------------- rendering
    def render_page(self, page_number: int, dpi: int = 150) -> Optional[fitz.Pixmap]:
        page = self.get_page(page_number)
        if page is None:
            return None
        scale = dpi / 72.0
        return page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

    def get_page_thumb(self, page_number: int, size: tuple = (100, 130)) -> Optional[fitz.Pixmap]:
        page = self.get_page(page_number)
        if page is None:
            return None
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            return None
        scale = min(size[0] / rect.width, size[1] / rect.height)
        return page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

    # ---------------------------------------------------------- page editing
    def insert_page(self, page_number: int, source_doc: "PDFDocument", source_page: int) -> bool:
        try:
            if self.doc is None or source_doc.doc is None:
                return False
            self.doc.insert_pdf(
                source_doc.doc,
                from_page=source_page - 1,
                to_page=source_page - 1,
                start_at=page_number - 1,
            )
            self._refresh_models()
            self.is_modified = True
            return True
        except Exception as exc:
            logger.error("Failed to insert page: %s", exc)
            return False

    def delete_page(self, page_number: int) -> bool:
        try:
            if self.doc is None or self.page_count <= 1:
                return False
            if not (1 <= page_number <= self.page_count):
                return False
            self.doc.delete_page(page_number - 1)
            self._refresh_models()
            self.is_modified = True
            return True
        except Exception as exc:
            logger.error("Failed to delete page: %s", exc)
            return False

    def move_page(self, from_pos: int, to_pos: int) -> bool:
        try:
            if self.doc is None:
                return False
            if not (1 <= from_pos <= self.page_count and 1 <= to_pos <= self.page_count):
                return False
            self.doc.move_page(from_pos - 1, to_pos - 1)
            self._refresh_models()
            self.is_modified = True
            return True
        except Exception as exc:
            logger.error("Failed to move page: %s", exc)
            return False

    def rotate_page(self, page_number: int, degrees: int) -> bool:
        try:
            page = self.get_page(page_number)
            if page is None:
                return False
            page.set_rotation((page.rotation + int(degrees)) % 360)
            self.is_modified = True
            return True
        except Exception as exc:
            logger.error("Failed to rotate page: %s", exc)
            return False

    def search(self, query: str, case_sensitive: bool = False) -> List[Tuple[int, TextRun, tuple]]:
        """Return (page_number, run, hit_bbox) for text runs containing query."""
        results: List[Tuple[int, TextRun, tuple]] = []
        if not query:
            return results
        needle = (query if case_sensitive else query.casefold()).replace("\xa0", " ")
        for page_num in sorted(self.text_runs):
            for run in self.text_runs[page_num]:
                haystack = (run.text if case_sensitive else run.text.casefold()).replace("\xa0", " ")
                if needle in haystack:
                    results.append((page_num, run, run.bbox))
        return results
