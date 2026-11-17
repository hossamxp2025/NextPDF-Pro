"""Validate actual exported files, not just their existence."""
import json
import xml.etree.ElementTree as ET
import pymupdf as fitz
import pytest
from PIL import Image
from src.engine.conversion import export_pdf
from src.engine.ocr_engine import OCREngine
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton
from src.ui.main_window import MainWindow
from src.ui.ocr_dialog import OCRDialog


@pytest.mark.parametrize("output_format", ["png", "jpg", "tiff", "webp", "txt", "html", "md", "svg", "json"])
def test_exports_arabic_and_english_with_source_unchanged(tmp_path, output_format):
    text = "مرحبا بالعالم INV-2026-105"
    with fitz.open() as doc:
        page = doc.new_page(width=500, height=200)
        page.insert_text((30, 120), "EXPORT VERIFIED", fontsize=20)
        OCREngine._insert_word_layer(page, [{"text": text, "left": 50, "top": 40,
                                           "width": 350, "height": 30}], 1, 1)
        data = doc.tobytes()
    before = bytes(data)
    target = tmp_path / ("output." + output_format)
    export_pdf(data, str(target), [1], output_format)
    assert data == before
    if output_format in {"png", "jpg", "tiff", "webp"}:
        with Image.open(target) as image:
            image.load()
            assert image.width >= 1000 and image.height >= 400
    elif output_format == "svg":
        assert ET.parse(target).getroot().tag.endswith("svg")
    elif output_format == "json":
        result = json.loads(target.read_text(encoding="utf-8"))
        assert text in result["pages"][0]["text"]
    else:
        result = target.read_text(encoding="utf-8")
        assert text in result
        if output_format == "html":
            assert 'dir="rtl"' in result


def test_rejects_multiple_pages_for_svg_without_writing(tmp_path):
    with fitz.open() as doc:
        doc.new_page()
        doc.new_page()
        data = doc.tobytes()
    target = tmp_path / "image.svg"
    with pytest.raises(ValueError):
        export_pdf(data, str(target), [1, 2], "svg")
    assert not target.exists()


@pytest.mark.parametrize("label,extension", [("PNG", "png"), ("JPEG", "jpg"), ("TIFF", "tiff"),
                                          ("WEBP", "webp"), ("TXT", "txt"), ("HTML", "html"),
                                          ("Markdown", "md"), ("SVG", "svg"), ("JSON", "json")])
def test_ribbon_conversion_button_produces_valid_output(tmp_path, monkeypatch, label, extension):
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "source.pdf"
    target = tmp_path / ("converted." + extension)
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 100), "CONVERSION BUTTON VERIFIED", fontsize=20)
        doc.save(source)
    before = source.read_bytes()
    window = MainWindow()
    assert window._open_file_path(str(source))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), extension))
    finished = []
    def configure():
        dialog = window.findChild(OCRDialog)
        assert dialog is not None
        dialog.worker.completed.connect(lambda path: (finished.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda text: dialog.reject())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_" + label).click()
    timer.stop()
    try:
        assert finished
        assert source.read_bytes() == before
        if extension in {"png", "jpg", "tiff", "webp"}:
            with Image.open(target) as image:
                image.load()
                assert image.width > 500 and image.height > 800
        elif extension == "svg":
            assert ET.parse(target).getroot().tag.endswith("svg")
        elif extension == "json":
            assert "CONVERSION BUTTON VERIFIED" in json.loads(target.read_text(encoding="utf-8"))["pages"][0]["text"]
        else:
            assert "CONVERSION BUTTON VERIFIED" in target.read_text(encoding="utf-8")
    finally:
        window.close()
        app.processEvents()


@pytest.mark.parametrize("label,extension", [("Word page images", "docx"), ("PowerPoint page images", "pptx"),
                                          ("Excel grid tables", "xlsx"), ("CSV grid tables", "csv")])
def test_office_ribbon_buttons_export_inspectable_content(tmp_path, monkeypatch, label, extension):
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "table.pdf"
    target = tmp_path / ("office." + extension)
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        for x in (40, 180, 320):
            page.draw_line((x, 40), (x, 120))
        for y in (40, 80, 120):
            page.draw_line((40, y), (320, y))
        for r, values in enumerate((("Item", "Amount"), ("INV-2026-105", "15750"))):
            for c, text in enumerate(values):
                page.insert_text((50+c*140,65+r*40),text,fontsize=12)
        doc.save(source)
    before = source.read_bytes()
    window = MainWindow()
    assert window._open_file_path(str(source))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), extension))
    completed = []
    def configure():
        dialog = window.findChild(OCRDialog)
        dialog.worker.completed.connect(lambda path: (completed.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda message: dialog.reject())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_"+label.replace(" ", "_")).click()
    timer.stop()
    try:
        assert completed
        assert source.read_bytes() == before
        if extension == "docx":
            from docx import Document
            assert len(Document(target).inline_shapes) == 1
        elif extension == "pptx":
            from pptx import Presentation
            presentation = Presentation(target)
            assert len(presentation.slides) == 1
            assert presentation.slides[0].shapes[0].image.blob
        elif extension == "xlsx":
            from openpyxl import load_workbook
            book = load_workbook(target)
            assert book.active.cell(2,1).value == "INV-2026-105"
            assert book.active.cell(2,2).value == 15750
            book.close()
        else:
            import csv
            with target.open(encoding="utf-8-sig", newline="") as stream:
                assert list(csv.reader(stream))[1] == ["INV-2026-105", "15750"]
    finally:
        window.close()
        app.processEvents()


@pytest.mark.parametrize("label,extension", [("Editable Word", "docx"), ("Editable slides", "pptx")])
def test_editable_office_ribbon_buttons_write_real_text(tmp_path, monkeypatch, label, extension):
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "text.pdf"
    target = tmp_path / ("editable." + extension)
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=250)
        page.insert_text((40, 110), "EDITABLE TEXT 2026", fontsize=18)
        doc.save(source)
    before = source.read_bytes()
    window = MainWindow()
    assert window._open_file_path(str(source))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), extension))
    completed = []
    def configure():
        dialog = window.findChild(OCRDialog)
        dialog.worker.completed.connect(lambda path: (completed.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda message: dialog.reject())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_" + label.replace(" ", "_")).click()
    timer.stop()
    try:
        assert completed
        assert source.read_bytes() == before
        if extension == "docx":
            from docx import Document
            assert "EDITABLE TEXT 2026" in [p.text for p in Document(target).paragraphs]
        else:
            from pptx import Presentation
            slide = Presentation(target).slides[0]
            assert "EDITABLE TEXT 2026" in [s.text_frame.text for s in slide.shapes if s.has_text_frame]
    finally:
        window.close()
        app.processEvents()
