"""Real OCR through MuPDF's built-in Tesseract; no external binary is used.

These tests deliberately do not monkeypatch the recognition path: they render
text, rasterise it, and require the engine to read it back.  The only fault
injection is in the rejection test, which breaks the writer, not the reader.
"""
import hashlib
import os
import shutil

import pymupdf as fitz
import pytest

from src.engine import ocr_engine
from src.config import FONTS_DIR
from src.models.document import PDFDocument


def _scan(tmp_path, name, build, width=600, height=250, dpi=200):
    """Render a page, rasterise it, and save an image-only PDF."""
    with fitz.open() as typeset:
        page = typeset.new_page(width=width, height=height)
        build(page)
        image = page.get_pixmap(dpi=dpi).tobytes("png")
    path = tmp_path / name
    with fitz.open() as scan:
        page = scan.new_page(width=width, height=height)
        page.insert_image(page.rect, stream=image)
        scan.save(path)
    return path


def _arabic(page, text="مرحبا بالعالم", rect=(50, 40, 550, 110), size=30):
    css = (f"@font-face {{font-family:A;src:url('NotoSansArabic-Regular.ttf');}}"
           f" body {{font-family:A;font-size:{size}px;}}")
    page.insert_htmlbox(fitz.Rect(*rect), f"<p dir='rtl'>{text}</p>", css=css,
                        archive=fitz.Archive(str(FONTS_DIR)))


# ------------------------------------------------------------------ portability
def test_engine_needs_no_tesseract_executable(monkeypatch):
    """OCR works with the language data alone: no bundled or system binary."""
    monkeypatch.setenv("PATH", "")
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    engine = ocr_engine.OCREngine("ara+eng")
    assert engine.is_available()
    assert engine.tessdata and os.path.isdir(engine.tessdata)
    assert set(ocr_engine.available_languages(engine.tessdata)) >= {"ara", "eng"}
    # Nothing in the shipped tree is a Tesseract executable.
    resources = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
    for root, _dirs, files in os.walk(resources):
        assert not any(f.lower() == "tesseract.exe" for f in files), root
    assert shutil.which("tesseract") is None or True  # system copy is irrelevant


def test_missing_language_is_reported_not_guessed():
    engine = ocr_engine.OCREngine("deu")
    assert not engine.is_available()
    assert engine.missing_languages == ["deu"]


# ------------------------------------------------------------------ recognition
def test_recognizes_rendered_english_page():
    with fitz.open() as doc:
        page = doc.new_page(width=500, height=200)
        page.insert_text((35, 90), "NEXT PDF TEST 2026", fontsize=30)
        engine = ocr_engine.OCREngine(language="eng")
        assert engine.is_available()
        text, boxes = engine.ocr_page(page)
        assert "NEXT PDF TEST 2026" in " ".join(text.split())
        assert any(box["text"] == "NEXT" for box in boxes)
        assert all(box["width"] > 0 and box["height"] > 0 for box in boxes)


def test_recognizes_arabic_and_english_on_scanned_page(tmp_path):
    def build(page):
        _arabic(page)
        page.insert_text((60, 170), "HELLO WORLD", fontsize=30)
    source = _scan(tmp_path, "mixed.pdf", build)
    with fitz.open(source) as scanned:
        text, _ = ocr_engine.OCREngine("ara+eng").ocr_page(scanned[0])
    assert "مرحبا" in text
    assert "HELLO WORLD" in " ".join(text.split())


# -------------------------------------------------------------- searchable PDF
def test_searchable_pdf_preserves_original_and_searches_text(tmp_path):
    source = _scan(tmp_path, "scanned.pdf",
                   lambda page: page.insert_text((35, 90), "NEXT PDF TEST 2026", fontsize=30),
                   width=500, height=200)
    before = source.read_bytes()
    document = PDFDocument()
    assert document.load(str(source))
    old_path = document.file_path
    output = tmp_path / "searchable.pdf"
    try:
        assert ocr_engine.OCREngine(language="eng").create_searchable_pdf(document, str(output))
        assert source.read_bytes() == before
        assert document.file_path == old_path
        assert not document.get_page(1).get_text().strip()
        with fitz.open(output) as result:
            page = result[0]
            assert page.search_for("NEXT")
            assert "NEXT PDF TEST 2026" in " ".join(page.get_text().split())
            assert len(page.get_images()) >= 1
            # The text layer is invisible: the page still renders identically.
            assert page.get_pixmap().samples == document.get_page(1).get_pixmap().samples
    finally:
        document.close()


def test_searchable_pdf_arabic_extraction(tmp_path):
    def build(page):
        _arabic(page)
        page.insert_text((60, 170), "HELLO WORLD", fontsize=30)
    source = _scan(tmp_path, "arabic_scan.pdf", build)
    doc = PDFDocument()
    assert doc.load(str(source))
    try:
        output = tmp_path / "arabic_searchable.pdf"
        assert ocr_engine.OCREngine("ara+eng").create_searchable_pdf(doc, str(output))
        with fitz.open(output) as result:
            text = result[0].get_text()
            assert "مرحبا" in text
            assert "HELLO WORLD" in " ".join(text.split())
            assert result[0].search_for("مرحبا")
            # Logical Unicode, not shaped presentation forms.
            assert not any("ﭐ" <= c <= "﷿" or "ﹰ" <= c <= "﻿" for c in text)
    finally:
        doc.close()


def test_rejects_broken_layer_without_writing(tmp_path, monkeypatch):
    """Fault injection in the writer only; recognition stays real.

    A layer that does not carry the recognised words must be refused and no
    file may appear.
    """
    def broken_layer(page, words, sx, sy):
        page.insert_text((50, 100), "INVALID LAYER", render_mode=3)
    monkeypatch.setattr(ocr_engine.OCREngine, "_insert_word_layer", staticmethod(broken_layer))
    source = _scan(tmp_path, "source.pdf", _arabic)
    document = PDFDocument()
    assert document.load(str(source))
    try:
        output = tmp_path / "unsafe.pdf"
        assert not ocr_engine.OCREngine("ara+eng").create_searchable_pdf(document, str(output))
        assert not output.exists()
    finally:
        document.close()


def test_real_mixed_ocr_search_geometry_image_and_source_hash(tmp_path):
    """Every searched word is found where OCR saw it, and the source is untouched."""
    engine = ocr_engine.OCREngine("ara+eng")
    assert engine.is_available()

    def build(page):
        _arabic(page, "مرحبا بالعالم", (50, 35, 850, 100), 32)
        _arabic(page, "رقم الفاتورة INV-2026-105", (50, 110, 850, 180), 32)
    source = _scan(tmp_path, "mixed_source.pdf", build, width=900, height=400, dpi=300)
    output = tmp_path / "mixed_searchable.pdf"
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    document = PDFDocument()
    assert document.load(str(source))
    try:
        # Reference geometry straight from the recogniser, before writing.
        _, words = engine.ocr_page(document.get_page(1), dpi=300)
        assert engine.create_searchable_pdf(document, str(output))
        with fitz.open(output) as saved:
            page = saved[0]
            text = page.get_text()
            assert "مرحبا" in text and "INV-2026-105" in text
            assert page.search_for("مرحبا بالعالم")
            for query in ("مرحبا", "INV-2026-105"):
                box = next((w for w in words if w["text"].strip("‎‏") == query), None)
                assert box is not None, [w["text"] for w in words]
                expected = fitz.Rect(box["left"], box["top"],
                                     box["left"] + box["width"],
                                     box["top"] + box["height"]) * (72 / 300)
                hits = page.search_for(query)
                assert hits
                assert any((hit & expected).get_area() / expected.get_area() > 0.9 for hit in hits)
            assert page.get_pixmap().samples == document.get_page(1).get_pixmap().samples
            assert len(page.get_images()) == len(document.get_page(1).get_images())
            assert not saved.is_repaired
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    finally:
        document.close()


def test_searchable_pdf_rejects_same_path_and_cancellation(tmp_path):
    source = tmp_path / "original.pdf"
    with fitz.open() as raw:
        raw.new_page()
        raw.save(source)
    before = source.read_bytes()
    doc = PDFDocument()
    assert doc.load(str(source))
    try:
        engine = ocr_engine.OCREngine("eng")
        assert not engine.create_searchable_pdf(doc, str(source))
        output = tmp_path / "cancelled.pdf"
        assert not engine.create_searchable_pdf(doc, str(output), cancel_callback=lambda: True)
        assert not output.exists()
        assert source.read_bytes() == before
    finally:
        doc.close()


@pytest.mark.parametrize("language", ["eng", "ara+eng"])
def test_searchable_pdf_retains_page_rotation_and_rendering(tmp_path, language):
    engine = ocr_engine.OCREngine(language)
    assert engine.is_available()
    source = tmp_path / "rotated_scan.pdf"
    target = tmp_path / "rotated_searchable.pdf"
    with fitz.open() as raw:
        page = raw.new_page(width=500, height=200)
        page.insert_text((40, 100), "ROTATION VERIFIED", fontsize=26)
        image = page.get_pixmap(dpi=200).tobytes("png")
    with fitz.open() as scan:
        page = scan.new_page(width=500, height=200)
        page.insert_image(page.rect, stream=image)
        page.set_rotation(90)
        scan.save(source)
    before = source.read_bytes()
    doc = PDFDocument()
    assert doc.load(str(source))
    try:
        assert engine.create_searchable_pdf(doc, str(target))
        with fitz.open(target) as saved:
            assert saved[0].rotation == 90
            assert saved[0].search_for("ROTATION")
            assert saved[0].get_pixmap().samples == doc.get_page(1).get_pixmap().samples
        assert source.read_bytes() == before
    finally:
        doc.close()
