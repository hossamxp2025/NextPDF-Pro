#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Conversion options: the chosen resolution and exporting several pages as
images.  Every check reads the file that was written, not the arguments.
"""

import os
import sys

import pymupdf as fitz
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.engine.conversion import export_pdf, page_image_path


def two_page_pdf():
    with fitz.open() as doc:
        for number in (1, 2):
            page = doc.new_page(width=300, height=200)
            page.insert_text((40, 100), f"PAGE {number}", fontsize=18)
        return doc.tobytes()


# ------------------------------------------------------------- resolution
@pytest.mark.parametrize("dpi,expected_width", [(72, 300), (150, 625), (300, 1250)])
def test_the_chosen_resolution_decides_the_pixel_size(tmp_path, dpi, expected_width):
    target = tmp_path / "page.png"
    export_pdf(two_page_pdf(), str(target), [1], "png", dpi=dpi)
    with Image.open(target) as image:
        assert abs(image.width - expected_width) <= 2


def test_a_higher_resolution_makes_a_bigger_file(tmp_path):
    low, high = tmp_path / "low.png", tmp_path / "high.png"
    export_pdf(two_page_pdf(), str(low), [1], "png", dpi=72)
    export_pdf(two_page_pdf(), str(high), [1], "png", dpi=300)
    assert high.stat().st_size > low.stat().st_size


def test_the_resolution_reaches_the_word_page_images(tmp_path):
    from docx import Document

    low, high = tmp_path / "low.docx", tmp_path / "high.docx"
    export_pdf(two_page_pdf(), str(low), [1], "docx", dpi=72)
    export_pdf(two_page_pdf(), str(high), [1], "docx", dpi=300)
    assert len(Document(high).inline_shapes) == 1
    assert high.stat().st_size > low.stat().st_size


@pytest.mark.parametrize("dpi", [10, 71, 601, 2000])
def test_an_impossible_resolution_is_refused(tmp_path, dpi):
    target = tmp_path / "page.png"
    with pytest.raises(ValueError):
        export_pdf(two_page_pdf(), str(target), [1], "png", dpi=dpi)
    assert not target.exists()


# -------------------------------------------------- several pages as images
def test_one_page_keeps_the_name_the_user_chose(tmp_path):
    target = tmp_path / "scan.png"
    export_pdf(two_page_pdf(), str(target), [1], "png")
    assert target.is_file()
    assert not (tmp_path / "scan-001.png").exists()


@pytest.mark.parametrize("extension", ["png", "jpg", "webp"])
def test_several_pages_are_written_as_numbered_files(tmp_path, extension):
    target = tmp_path / f"scan.{extension}"
    export_pdf(two_page_pdf(), str(target), [1, 2], extension)
    first = tmp_path / f"scan-001.{extension}"
    second = tmp_path / f"scan-002.{extension}"
    assert first.is_file() and second.is_file()
    assert not target.exists()
    for path in (first, second):
        with Image.open(path) as image:
            image.load()
            assert image.width > 100


def test_the_numbered_files_hold_different_pages(tmp_path):
    target = tmp_path / "scan.png"
    export_pdf(two_page_pdf(), str(target), [1, 2], "png")
    first = (tmp_path / "scan-001.png").read_bytes()
    second = (tmp_path / "scan-002.png").read_bytes()
    assert first != second


def test_tiff_still_holds_every_page_in_one_file(tmp_path):
    target = tmp_path / "scan.tiff"
    export_pdf(two_page_pdf(), str(target), [1, 2], "tiff")
    with Image.open(target) as image:
        assert image.n_frames == 2
    assert not (tmp_path / "scan-001.tiff").exists()


def test_the_numbering_follows_the_selection_not_the_page_number(tmp_path):
    target = tmp_path / "scan.png"
    export_pdf(two_page_pdf(), str(target), [2, 1], "png")
    assert (tmp_path / "scan-001.png").is_file()
    assert (tmp_path / "scan-002.png").is_file()
    assert not (tmp_path / "scan-003.png").exists()


# --------------------------------------------------------------- the dialog
def test_the_resolution_box_is_shown_only_where_it_changes_the_output(tmp_path):
    from PySide6.QtWidgets import QApplication
    from src.ui.main_window import MainWindow
    from src.ui.ocr_dialog import OCRDialog

    QApplication.instance() or QApplication([])
    source = tmp_path / "source.pdf"
    (lambda d: (d.new_page().insert_text((40, 80), "x"), d.save(source)))(fitz.open())
    window = MainWindow()
    assert window._open_file_path(str(source))
    try:
        for fmt, shown in (("png", True), ("docx", True), ("txt", False),
                           ("json", False), ("xlsx", False)):
            dialog = OCRDialog(window.current_context, window, conversion_format=fmt)
            assert dialog.dpi.isHidden() is (not shown), fmt
            dialog.deleteLater()
        ocr = OCRDialog(window.current_context, window)
        assert ocr.dpi.isHidden(), "OCR runs at its own resolution"
        ocr.deleteLater()
    finally:
        window.current_document.is_modified = False
        window.close()


def test_the_dialog_sends_the_chosen_resolution_to_the_worker(tmp_path):
    from PySide6.QtWidgets import QApplication
    from src.ui.main_window import MainWindow
    from src.ui.ocr_dialog import OCRDialog

    QApplication.instance() or QApplication([])
    source = tmp_path / "source.pdf"
    (lambda d: (d.new_page().insert_text((40, 80), "x"), d.save(source)))(fitz.open())
    window = MainWindow()
    assert window._open_file_path(str(source))
    dialog = OCRDialog(window.current_context, window, conversion_format="png")
    recorded = {}
    dialog.worker.start = lambda *args: recorded.setdefault("args", args)
    dialog.dpi.setValue(300)
    try:
        dialog.start_export(str(tmp_path / "out.png"))
        assert recorded["args"][-1] == 300
    finally:
        dialog.deleteLater()
        window.current_document.is_modified = False
        window.close()


def test_the_worker_refuses_an_impossible_resolution(tmp_path):
    from PySide6.QtWidgets import QApplication
    from src.workers.ocr_process import ConversionProcess

    QApplication.instance() or QApplication([])
    worker = ConversionProcess()
    with pytest.raises(ValueError):
        worker.start(two_page_pdf(), str(tmp_path / "out.png"), "ara+eng",
                     [1], "png", 5000)


def test_the_name_of_each_page_file_is_predictable():
    assert page_image_path("/tmp/a.png", 1, 1) == os.path.normpath("/tmp/a.png")
    assert page_image_path("/tmp/a.png", 2, 5).endswith("a-002.png")
    assert page_image_path("/tmp/a.png", 12, 20).endswith("a-012.png")
