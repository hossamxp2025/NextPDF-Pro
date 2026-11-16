#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR engine for NextPDF Pro.

Recognition runs on the Tesseract that is linked into MuPDF itself
(``Pixmap.pdfocr_tobytes``), so the application ships only the language data
(``resources/tessdata``) and no Tesseract executable or its dependency DLLs.
Verified on PyMuPDF 2.1 / MuPDF 1.28.6 (2026-11-16): Arabic and English are
recognised and the recognised text is logical Unicode.

The searchable-PDF path is unchanged in kind: the recognised words are written
as invisible marked text whose ``ActualText`` carries the logical string at the
word's own geometry, and it is fail-closed, so every recognised word must be
extractable and findable in the saved file or nothing is written.
"""

import logging
import os
import tempfile
from typing import List, Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - older environments
    import fitz

from src.config import resource_path

logger = logging.getLogger("NextPDF")

SUPPORTED_LANGUAGES = ("ara", "eng")
_TESSDATA_CANDIDATES = ("resources/tessdata",)


def find_tessdata() -> Optional[str]:
    """Directory holding the bundled ``*.traineddata`` files, or None."""
    for relative in _TESSDATA_CANDIDATES:
        candidate = resource_path(relative)
        if os.path.isdir(candidate) and any(
            name.endswith(".traineddata") for name in os.listdir(candidate)
        ):
            return candidate
    env = os.environ.get("TESSDATA_PREFIX")
    if env and os.path.isdir(env):
        return env
    return None


def available_languages(tessdata: Optional[str] = None) -> List[str]:
    directory = tessdata or find_tessdata()
    if not directory:
        return []
    return sorted(name[:-len(".traineddata")] for name in os.listdir(directory)
                  if name.endswith(".traineddata"))


def _is_arabic(text: str) -> bool:
    return any("؀" <= char <= "ۿ" for char in text)


class OCREngine:
    """OCR operations for PDF documents, backed by MuPDF's Tesseract."""

    _engine_checked = False
    _engine_works = False

    def __init__(self, language: str = "ara+eng"):
        self.language = language
        self.tessdata = find_tessdata()
        installed = set(available_languages(self.tessdata))
        requested = [part for part in language.split("+") if part]
        self.missing_languages = [part for part in requested if part not in installed]
        self.available = bool(self.tessdata) and not self.missing_languages
        self.tesseract_available = self.available and self._probe()
        logger.info("OCR engine=MuPDF built-in tessdata=%s languages=%s available=%s",
                    self.tessdata, sorted(installed), self.tesseract_available)

    # ------------------------------------------------------------- availability
    @classmethod
    def _probe(cls) -> bool:
        """One-off check that this MuPDF build really has Tesseract linked in."""
        if cls._engine_checked:
            return cls._engine_works
        cls._engine_checked = True
        try:
            tessdata = find_tessdata()
            pix = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 8, 8), False)
            pix.clear_with(255)
            pix.pdfocr_tobytes(language="eng", tessdata=tessdata)
            cls._engine_works = True
        except Exception as exc:
            cls._engine_works = False
            logger.warning("MuPDF OCR is unavailable: %s", exc)
        return cls._engine_works

    def is_available(self) -> bool:
        return bool(self.available and self.tesseract_available)

    # ------------------------------------------------------------- recognition
    def _recognise(self, page: fitz.Page, dpi: int) -> Tuple[str, List[dict], int, int]:
        """Return (text, word boxes in image pixels, image width, image height)."""
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        blob = pix.pdfocr_tobytes(language=self.language, tessdata=self.tessdata)
        with fitz.open("pdf", blob) as ocr_doc:
            ocr_page = ocr_doc[0]
            text = ocr_page.get_text()
            scale_x = pix.width / ocr_page.rect.width if ocr_page.rect.width else 1.0
            scale_y = pix.height / ocr_page.rect.height if ocr_page.rect.height else 1.0
            boxes = []
            for x0, y0, x1, y1, word, *_ in ocr_page.get_text("words"):
                if not word.strip():
                    continue
                boxes.append({
                    "text": word,
                    "left": x0 * scale_x,
                    "top": y0 * scale_y,
                    "width": (x1 - x0) * scale_x,
                    "height": (y1 - y0) * scale_y,
                    "conf": -1,
                })
        return text, boxes, pix.width, pix.height

    def ocr_page(self, page: fitz.Page, dpi: int = 300) -> Tuple[str, List[dict]]:
        """Recognise one page.

        Returns ``(text, word_boxes)``; each box carries pixel geometry in the
        rendered image's coordinate space.  ``conf`` is -1 because MuPDF does
        not expose per-word confidence.
        """
        if not self.is_available():
            return "", []
        try:
            text, boxes, _, _ = self._recognise(page, dpi)
            return text, boxes
        except Exception as exc:
            logger.error("OCR failed for page: %s", exc)
            return "", []

    def ocr_document(self, document, progress_callback=None) -> List[Tuple[int, str]]:
        """Recognise every page; returns ``[(page_number, text)]``."""
        results: List[Tuple[int, str]] = []
        if not self.is_available():
            logger.warning("OCR not available")
            return results
        try:
            total = document.page_count
            for number in range(1, total + 1):
                page = document.get_page(number)
                if page is None:
                    continue
                text, _ = self.ocr_page(page)
                results.append((number, text))
                if progress_callback:
                    progress_callback(number, total)
        except Exception as exc:
            logger.error("OCR document failed: %s", exc)
        return results

    # --------------------------------------------------------- searchable PDF
    @staticmethod
    def _insert_word_layer(page, words, scale_x, scale_y):
        """Add invisible marked text with logical Unicode and OCR geometry.

        Uses documented Document xref/stream APIs, not a nonexistent Page API.
        Each marked-content span substitutes a single word through ActualText.
        Recognition ordering is retained; Unicode strings are never reversed.
        """
        if page.rotation:
            raise ValueError("OCR on rotated pages is not supported yet")
        doc = page.parent
        font = fitz.Font("helv")
        page.insert_font(fontname="helv")
        parts = ["q", "BT", "3 Tr"]
        for word in words:
            text = word["text"].strip()
            if not text:
                continue
            x = word["left"] * scale_x
            y = word["top"] * scale_y
            width = word["width"] * scale_x
            height = word["height"] * scale_y
            if width <= 0 or height <= 0:
                raise ValueError("Invalid OCR word geometry")
            size = height / (font.ascender - font.descender)
            baseline = y + font.ascender * size
            origin = fitz.Point(x, baseline) * ~page.transformation_matrix
            count = max(1, len(text))
            natural = font.text_length("x" * count, fontsize=size)
            horizontal = width / natural * 100
            actual = ("﻿" + text).encode("utf-16-be").hex()
            parts.extend([f"/helv {size:.6f} Tf", f"{horizontal:.6f} Tz",
                          f"1 0 0 1 {origin.x:.6f} {origin.y:.6f} Tm",
                          f"/Span << /ActualText <{actual}> >> BDC",
                          "(" + "x" * count + ") Tj", "EMC"])
        parts.extend(["ET", "Q"])
        page.wrap_contents()
        existing = page.get_contents()
        xref = doc.get_new_xref()
        doc.update_object(xref, "<<>>")
        doc.update_stream(xref, "\n".join(parts).encode("ascii"))
        refs = " ".join(f"{item} 0 R" for item in existing + [xref])
        doc.xref_set_key(page.xref, "Contents", f"[{refs}]")

    def create_searchable_pdf(self, document, output_path: str,
                              progress_callback=None, pages=None,
                              force=False, cancel_callback=None) -> bool:
        """Write ``output_path`` with an invisible OCR text layer added.

        The source document is never modified.  Returns False (and writes
        nothing) if any recognised word cannot be found in the saved file.
        """
        if not self.is_available():
            return False

        temp_output = None
        try:
            output_path = os.path.abspath(output_path)
            if document.file_path and os.path.normcase(os.path.realpath(output_path)) == \
                    os.path.normcase(os.path.realpath(document.file_path)):
                raise ValueError("Searchable PDF must use a different output path")
            selected = list(pages) if pages is not None else list(range(1, document.page_count + 1))
            if not selected or len(set(selected)) != len(selected) or any(
                not isinstance(n, int) or n < 1 or n > document.page_count for n in selected
            ):
                raise ValueError("Invalid page selection")
            source_bytes = document.to_bytes()
            if not source_bytes:
                raise ValueError("Could not copy the source PDF")

            expected_words = {}
            with fitz.open(stream=source_bytes, filetype="pdf") as result:
                for index, page_num in enumerate(selected, 1):
                    if cancel_callback and cancel_callback():
                        raise RuntimeError("OCR cancelled")
                    page = result[page_num - 1]
                    rotation = page.rotation
                    # Work in unrotated coordinates on the private copy, then
                    # restore the page's display rotation.
                    if rotation:
                        page.set_rotation(0)
                    if force or not page.get_text().strip():
                        _, words, pix_w, pix_h = self._recognise(page, 300)
                        if not words:
                            raise ValueError("OCR produced no words on selected page")
                        self._insert_word_layer(page, words,
                                                page.rect.width / pix_w,
                                                page.rect.height / pix_h)
                        # Validate on the live page before accepting it.
                        checked = [word["text"].strip() for word in words if word["text"].strip()]
                        text = page.get_text()
                        if any(word not in text or not page.search_for(word) for word in checked):
                            raise ValueError("OCR layer failed logical Unicode/search validation")
                        expected_words[page_num] = checked
                    page.set_rotation(rotation)
                    if progress_callback:
                        progress_callback(index, len(selected))
                if cancel_callback and cancel_callback():
                    raise RuntimeError("OCR cancelled")
                fd, temp_output = tempfile.mkstemp(prefix=".nextpdf_ocr_", suffix=".pdf",
                                                   dir=os.path.dirname(output_path))
                os.close(fd)
                result.save(temp_output, garbage=4, deflate=True)

            with fitz.open(temp_output) as verified:
                if verified.is_repaired:
                    raise ValueError("Generated OCR PDF required repair")
                for number, words in expected_words.items():
                    page = verified[number - 1]
                    text = page.get_text()
                    if any(word not in text or not page.search_for(word) for word in words):
                        raise ValueError("Saved OCR PDF failed logical Unicode/search validation")
            os.replace(temp_output, output_path)
            temp_output = None
            return True
        except Exception:
            logger.exception("Failed to create searchable PDF")
            return False
        finally:
            if temp_output and os.path.exists(temp_output):
                try:
                    os.unlink(temp_output)
                except OSError:
                    logger.warning("Could not remove temporary OCR output", exc_info=True)
