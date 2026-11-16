"""Regression tests for the PDF-to-Excel crash (NextPDF Pro v1.2.1).

These reproduce the production failure where converting a PDF with no
supported tables crashed the application instead of returning a structured
failure to the GUI.
"""
import os
import tempfile

import pymupdf as fitz
import pytest
from openpyxl import load_workbook
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from src.engine.conversion import export_pdf
from src.workers.ocr_process import ConversionProcess
from src.ui.main_window import MainWindow
from src.ui.ocr_dialog import OCRDialog
from PySide6.QtWidgets import QFileDialog, QPushButton

ARABIC_ERROR = "لم يتم العثور على جداول قابلة للاستخراج من ملف PDF. يمكنك تجربة ملف يحتوي على جداول واضحة أو استخدام طريقة استخراج مختلفة."
ENGLISH_ERROR = "No extractable tables were found in this PDF. Try a document with a clearly structured table or use another extraction method."


def _make_text_only_pdf(tmp_path, text="This is ordinary text, not a table."):
    path = os.path.join(str(tmp_path), "text_only.pdf")
    with fitz.open() as doc:
        doc.new_page(width=400, height=300).insert_text((40, 100), text, fontsize=12)
        doc.save(path)
    return path


def _make_ruled_table_pdf(tmp_path):
    """A single fully-ruled rectangular grid table (supported layout)."""
    path = os.path.join(str(tmp_path), "table.pdf")
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        for x in (40, 180, 320):
            page.draw_line((x, 40), (x, 160))
        for y in (40, 80, 120, 160):
            page.draw_line((40, y), (320, y))
        for row, values in enumerate((("Item", "Amount"), ("INV-2026-105", "15750"), ("Second", "2026"))):
            for col, value in enumerate(values):
                page.insert_text((50 + col * 140, 65 + row * 40), value, fontsize=12)
        doc.save(path)
    return path


# ---------------------------------------------------------------------------
# Test A — PDF without tables: graceful failure, GUI stays alive, no XLSX.
# ---------------------------------------------------------------------------
def test_conversion_no_tables_fails_gracefully(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    source = _make_text_only_pdf(tmp_path)
    target = os.path.join(str(tmp_path), "out.xlsx")

    window = MainWindow()
    window.show()
    assert window._open_file_path(source)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (target, "xlsx"))

    errors, results = [], []
    def configure():
        dialog = window.findChild(OCRDialog)
        assert dialog is not None
        dialog.worker.failed.connect(lambda message: (errors.append(message), dialog.reject()))
        dialog.worker.completed.connect(lambda path: (results.append(path), dialog.accept()))
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_Excel_grid_tables").click()
    timer.stop()

    try:
        assert errors, "expected a structured failure, not a crash"
        assert not results, "no output should be published on failure"
        assert not os.path.exists(target), "no incomplete XLSX may remain after failure"
        assert window.isVisible(), "the GUI must remain operational"
    finally:
        window.close()
        app.processEvents()


# ---------------------------------------------------------------------------
# Test B — PDF with valid tables: reopen XLSX and verify cells.
# ---------------------------------------------------------------------------
def test_conversion_valid_table_exports_editable_xlsx(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    source = _make_ruled_table_pdf(tmp_path)
    target = os.path.join(str(tmp_path), "table.xlsx")

    window = MainWindow()
    window.show()
    assert window._open_file_path(source)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (target, "xlsx"))

    results = []
    def configure():
        dialog = window.findChild(OCRDialog)
        dialog.worker.completed.connect(lambda path: (results.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda message: dialog.reject())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_Excel_grid_tables").click()
    timer.stop()

    try:
        assert results, "supported table conversion should succeed"
        book = load_workbook(target)
        try:
            rows = list(book.active.values)
            assert rows[1] == ("INV-2026-105", 15750), rows
            assert rows[0][0] == "Item"
        finally:
            book.close()
        assert os.path.exists(target)
    finally:
        window.close()
        app.processEvents()


# ---------------------------------------------------------------------------
# Test C — Unsupported layout: controlled failure without termination.
# ---------------------------------------------------------------------------
def test_conversion_unsupported_layout_controlled_failure(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    source = _make_text_only_pdf(tmp_path, text="Just a paragraph of text here.")
    target = os.path.join(str(tmp_path), "unsupported.xlsx")

    worker = ConversionProcess()
    loop = QEventLoop()
    errors, results = [], []
    worker.failed.connect(lambda message: (errors.append(message), loop.quit()))
    worker.completed.connect(lambda path: (results.append(path), loop.quit()))
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(30000)

    with open(source, "rb") as handle:
        data = handle.read()
    worker.start(data, target, "ara+eng", [1], "xlsx")
    loop.exec()
    timer.stop()

    assert errors, "expected controlled failure"
    assert not results
    assert not os.path.exists(target)
    assert not worker.is_running()
    app.processEvents()


# ---------------------------------------------------------------------------
# Test D — Worker failure: parent receives failure, logs it, stays alive.
# ---------------------------------------------------------------------------
def test_conversion_worker_failure_parent_alive(tmp_path, monkeypatch, caplog):
    app = QApplication.instance() or QApplication([])
    source = _make_text_only_pdf(tmp_path)
    target = os.path.join(str(tmp_path), "worker.xlsx")

    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (target, "xlsx"))

    window = MainWindow()
    window.show()
    assert window._open_file_path(source)
    errors = []
    def configure():
        dialog = window.findChild(OCRDialog)
        dialog.worker.failed.connect(lambda message: (errors.append(message), dialog.reject()))
        dialog.worker.completed.connect(lambda path: dialog.accept())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_Excel_grid_tables").click()
    timer.stop()

    try:
        assert errors
        assert window.isVisible(), "parent process must not terminate"
        assert not os.path.exists(target)
    finally:
        window.close()
        app.processEvents()


# ---------------------------------------------------------------------------
# Test E — Multiple conversions: failed then successful.
# ---------------------------------------------------------------------------
def test_conversion_failed_then_succeeds(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    bad_source = _make_text_only_pdf(tmp_path, text="No tables here.")
    good_source = _make_ruled_table_pdf(tmp_path)
    bad_target = os.path.join(str(tmp_path), "bad.xlsx")
    good_target = os.path.join(str(tmp_path), "good.xlsx")

    window = MainWindow()
    assert window._open_file_path(bad_source)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (bad_target, "xlsx"))

    errors = []
    def configure_bad():
        dialog = window.findChild(OCRDialog)
        dialog.worker.failed.connect(lambda message: (errors.append(message), dialog.reject()))
        dialog.worker.completed.connect(lambda path: dialog.accept())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure_bad)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_Excel_grid_tables").click()
    timer.stop()
    assert errors
    assert not os.path.exists(bad_target)

    # Immediately retry with a valid table PDF.
    assert window._open_file_path(good_source)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (good_target, "xlsx"))
    results = []
    def configure_good():
        dialog = QApplication.activeModalWidget()
        dialog.worker.completed.connect(lambda path: (results.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda message: dialog.reject())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure_good)
    window.ribbon.tab_bar.setCurrentIndex(4)
    window.ribbon.findChild(QPushButton, "tool_Excel_grid_tables").click()
    timer.stop()

    try:
        assert results, "second conversion must succeed after a failed one"
        book = load_workbook(good_target)
        try:
            rows = list(book.active.values)
            assert rows[1] == ("INV-2026-105", 15750)
        finally:
            book.close()
    finally:
        window.close()
        app.processEvents()


# ---------------------------------------------------------------------------
# Engine-level tests for localized error messages.
# ---------------------------------------------------------------------------
def test_engine_raises_localized_table_error(tmp_path):
    source = _make_text_only_pdf(tmp_path)
    with open(source, "rb") as handle:
        data = handle.read()
    target = os.path.join(str(tmp_path), "out.xlsx")
    with pytest.raises(ValueError, match="No supported tables were found"):
        export_pdf(data, target, [1], "xlsx")
    assert not os.path.exists(target)
