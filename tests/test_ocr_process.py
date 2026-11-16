"""Actual background OCR process, with a responsive Qt event loop."""
import pymupdf as fitz
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from src.workers.ocr_process import OCRProcess
from PySide6.QtWidgets import QFileDialog, QPushButton
from src.ui.main_window import MainWindow
from src.ui.ocr_dialog import OCRDialog


def test_real_background_process_exports_searchable_pdf(tmp_path):
    app = QApplication.instance() or QApplication([])
    with fitz.open() as doc:
        page = doc.new_page(width=500, height=200)
        page.insert_text((40, 100), "BACKGROUND OCR 2026", fontsize=26)
        image = page.get_pixmap(dpi=200).tobytes("png")
    with fitz.open() as doc:
        page = doc.new_page(width=500, height=200)
        page.insert_image(page.rect, stream=image)
        data = doc.tobytes()
    target = tmp_path / "background.pdf"
    worker = OCRProcess()
    loop = QEventLoop()
    results, errors, progress = [], [], []
    worker.completed.connect(lambda path: (results.append(path), loop.quit()))
    worker.failed.connect(lambda text: (errors.append(text), loop.quit()))
    worker.progress.connect(lambda a, b: progress.append((a, b)))
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(30000)
    worker.start(data, str(target), "eng", [1], "pdf")
    loop.exec()
    if worker.is_running():
        worker.cancel()
        raise AssertionError("OCR process timed out")
    assert not errors, errors
    assert results and progress == [(1, 1)]
    with fitz.open(target) as doc:
        assert doc[0].search_for("BACKGROUND")
    app.processEvents()


def test_ribbon_ocr_dialog_start_button_exports_real_pdf(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    source, output = tmp_path / "scan.pdf", tmp_path / "gui_ocr.pdf"
    with fitz.open() as raw:
        page = raw.new_page(width=500, height=200)
        page.insert_text((40, 100), "GUI OCR VERIFIED", fontsize=26)
        image = page.get_pixmap(dpi=200).tobytes("png")
    with fitz.open() as scan:
        page = scan.new_page(width=500, height=200)
        page.insert_image(page.rect, stream=image)
        scan.save(source)
    window = MainWindow()
    assert window._open_file_path(str(source))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), "PDF"))
    observed = []
    def configure():
        dialog = window.findChild(OCRDialog)
        assert dialog is not None
        dialog.language.setCurrentIndex(1)
        dialog.worker.completed.connect(lambda path: (observed.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda message: dialog.reject())
        dialog.start_button.click()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(OCRDialog).reject())
    timer.start(30000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(6)
    window.ribbon.findChild(QPushButton, "tool_OCR").click()
    timer.stop()
    try:
        assert observed
        with fitz.open(output) as saved:
            assert saved[0].search_for("GUI OCR VERIFIED")
    finally:
        window.close()
        app.processEvents()


def test_cancel_process_does_not_publish_output(tmp_path):
    app = QApplication.instance() or QApplication([])
    with fitz.open() as doc:
        doc.new_page()
        data = doc.tobytes()
    worker = OCRProcess()
    loop = QEventLoop()
    cancelled = []
    worker.cancelled.connect(lambda: (cancelled.append(True), loop.quit()))
    worker.failed.connect(lambda text: loop.quit())
    target = tmp_path / "cancelled.pdf"
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(15000)
    worker.start(data, str(target), "eng", [1], "pdf")
    worker.cancel()
    loop.exec()
    timer.stop()
    assert cancelled
    assert not worker.is_running()
    assert not target.exists()
    app.processEvents()


def test_background_txt_export_selects_only_requested_pages(tmp_path):
    app = QApplication.instance() or QApplication([])
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 100), "PAGE ONE")
        doc.new_page().insert_text((40, 100), "PAGE TWO")
        data = doc.tobytes()
    target = tmp_path / "selected.txt"
    worker = OCRProcess()
    loop = QEventLoop()
    errors = []
    worker.completed.connect(loop.quit)
    worker.failed.connect(lambda message: (errors.append(message), loop.quit()))
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(30000)
    worker.start(data, str(target), "eng", [2], "txt")
    loop.exec()
    timer.stop()
    assert not worker.is_running()
    assert not errors
    assert "PAGE TWO" in target.read_text(encoding="utf-8")
    assert "PAGE ONE" not in target.read_text(encoding="utf-8")
    app.processEvents()
