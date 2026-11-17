#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A scanned page carries no text layer.  Conversion to a text format used to
refuse it; it now recognises the page and says so, and still refuses when
recognition finds nothing.
"""

import json
import os
import sys

import pymupdf as fitz
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.engine import conversion
from src.engine.conversion import export_pdf, recognise_page

SCANNED_TEXT = "NEXT PDF SCAN 2026"


def scanned_pdf(width=600, height=250, dpi=200, text=SCANNED_TEXT):
    """An image-only PDF: the words exist as pixels, not as text."""
    with fitz.open() as typeset:
        page = typeset.new_page(width=width, height=height)
        page.insert_text((60, 140), text, fontsize=30)
        image = page.get_pixmap(dpi=dpi).tobytes("png")
    with fitz.open() as scan:
        page = scan.new_page(width=width, height=height)
        page.insert_image(page.rect, stream=image)
        assert not scan[0].get_text().strip(), "the fixture must have no text"
        return scan.tobytes()


def blank_pdf():
    with fitz.open() as doc:
        doc.new_page(width=200, height=200)
        return doc.tobytes()


@pytest.fixture(scope="module")
def recognition_works():
    from src.engine.ocr_engine import OCREngine

    if not OCREngine("eng").is_available():
        pytest.skip("the bundled recognition engine is unavailable here")
    with fitz.open(stream=scanned_pdf(), filetype="pdf") as doc:
        if SCANNED_TEXT.split()[0] not in recognise_page(doc[0], "eng"):
            pytest.skip("the bundled engine did not read the fixture")
    return True


def test_a_scanned_page_is_read_into_plain_text(tmp_path, recognition_works):
    target = tmp_path / "scan.txt"
    export_pdf(scanned_pdf(), str(target), [1], "txt", language="eng")
    assert "SCAN" in target.read_text(encoding="utf-8")


def test_the_json_export_says_the_text_was_recognised(tmp_path, recognition_works):
    target = tmp_path / "scan.json"
    export_pdf(scanned_pdf(), str(target), [1], "json", language="eng")
    page = json.loads(target.read_text(encoding="utf-8"))["pages"][0]
    assert page["source"] == "recognised"


def test_a_real_text_layer_is_not_marked_as_recognised(tmp_path):
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 80), "TYPED TEXT", fontsize=14)
        data = doc.tobytes()
    target = tmp_path / "typed.json"
    export_pdf(data, str(target), [1], "json")
    page = json.loads(target.read_text(encoding="utf-8"))["pages"][0]
    assert page["source"] == "text layer"
    assert "TYPED TEXT" in page["text"]


def test_the_html_export_carries_the_source_of_each_page(tmp_path, recognition_works):
    target = tmp_path / "scan.html"
    export_pdf(scanned_pdf(), str(target), [1], "html", language="eng")
    assert 'data-source="recognised"' in target.read_text(encoding="utf-8")


def test_markdown_marks_the_recognised_page(tmp_path, recognition_works):
    target = tmp_path / "scan.md"
    export_pdf(scanned_pdf(), str(target), [1], "md", language="eng")
    text = target.read_text(encoding="utf-8")
    assert "SCAN" in text
    assert "read by recognition" in text


def test_a_page_recognition_cannot_read_is_still_refused(tmp_path):
    target = tmp_path / "blank.txt"
    with pytest.raises(ValueError):
        export_pdf(blank_pdf(), str(target), [1], "txt")
    assert not target.exists()


def test_recognition_failure_is_reported_not_written_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(conversion, "recognise_page", lambda page, language: "")
    target = tmp_path / "scan.md"
    with pytest.raises(ValueError):
        export_pdf(scanned_pdf(), str(target), [1], "md", language="eng")
    assert not target.exists()


def test_an_unknown_recognition_language_is_refused(tmp_path):
    with pytest.raises(ValueError):
        export_pdf(blank_pdf(), str(tmp_path / "x.txt"), [1], "txt",
                   language="fra")


def test_recognition_returns_empty_instead_of_raising_when_unavailable(monkeypatch):
    class Unavailable:
        def __init__(self, language):
            pass

        def is_available(self):
            return False

    import src.engine.ocr_engine as ocr_engine
    monkeypatch.setattr(ocr_engine, "OCREngine", Unavailable)
    with fitz.open(stream=blank_pdf(), filetype="pdf") as doc:
        assert recognise_page(doc[0]) == ""
