"""Create PDF must build real, inspectable PDFs from every supported source."""
import io
from pathlib import Path

import pymupdf as fitz
import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton

from src.engine.pdf_creation import create_pdf
from src.ui.create_pdf_dialog import CreatePDFDialog
from src.ui.main_window import MainWindow
from src.workers.creation_process import CreationProcess


def _pdf(path, pages=1, text="SOURCE PAGE"):
    with fitz.open() as doc:
        for index in range(pages):
            doc.new_page(width=300, height=300).insert_text(
                (30, 60), f"{text} {index + 1}", fontsize=14)
        doc.save(path)
    return path


def _png(path, color=(255, 0, 0), size=(120, 90)):
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, *size))
    pix.set_rect(pix.irect, color)
    pix.save(path)
    return path


def _docx(path):
    from docx import Document
    document = Document()
    document.add_heading("Heading One", 0)
    document.add_paragraph("Arabic paragraph")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.cell(1, 0).text = "1"
    table.cell(1, 1).text = "2"
    document.save(path)
    return path


def _xlsx(path):
    from openpyxl import Workbook
    book = Workbook()
    book.active.append(["Name", "Amount"])
    book.active.append(["INV-1", 15750])
    book.create_sheet("Second").append(["x"])
    book.save(path)
    return path


def _pptx(path):
    from pptx import Presentation
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    slide.shapes.title.text = "Slide Title"
    presentation.save(path)
    return path


def _reject_encrypted(path):
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 60), "SECRET")
        doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256,
                 owner_pw="owner", user_pw="user")
    return path


@pytest.mark.parametrize("kind", ["pdf", "png", "txt", "md", "html", "csv",
                                  "docx", "xlsx", "pptx"])
def test_creates_pdf_from_each_supported_source(tmp_path, kind):
    source = tmp_path / ("source." + kind)
    if kind == "pdf":
        _pdf(source, pages=2)
    elif kind == "png":
        _png(source)
    elif kind in {"txt", "md"}:
        source.write_text("Arabic line\nEnglish line\n", encoding="utf-8")
    elif kind == "html":
        source.write_text("<html><body><h1>Title</h1><p>Hello</p></body></html>", encoding="utf-8")
    elif kind == "csv":
        source.write_text("Name,Amount\nINV-1,15750\n", encoding="utf-8")
    else:
        {"docx": _docx, "xlsx": _xlsx, "pptx": _pptx}[kind](source)
    before = source.read_bytes()
    target = tmp_path / "created.pdf"
    accepted = create_pdf([str(source)], str(target))
    assert accepted == [str(source)]
    assert source.read_bytes() == before
    with fitz.open(target) as doc:
        assert doc.page_count >= 1
        text = "".join(page.get_text() for page in doc)
    if kind == "pdf":
        assert "SOURCE PAGE 1" in text and "SOURCE PAGE 2" in text
    if kind == "png":
        assert sum(len(page.get_images()) for page in fitz.open(target)) >= 1
    if kind in {"txt", "md", "html", "csv", "docx", "xlsx", "pptx"}:
        assert text.strip()


def test_multiframe_tiff_keeps_every_frame(tmp_path):
    from PIL import Image
    source = tmp_path / "frames.tiff"
    images = [Image.new("RGB", (100, 80), color)
              for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    images[0].save(source, save_all=True, append_images=images[1:])
    target = tmp_path / "frames.pdf"
    create_pdf([str(source)], str(target))
    with fitz.open(target) as doc:
        assert doc.page_count == 3
        assert sum(len(page.get_images()) for page in doc) == 3


def test_merge_order_is_preserved(tmp_path):
    first = _pdf(tmp_path / "first.pdf", text="FIRST")
    second = _pdf(tmp_path / "second.pdf", text="SECOND")
    target = tmp_path / "merged.pdf"
    create_pdf([str(second), str(first)], str(target))
    with fitz.open(target) as doc:
        assert "SECOND" in doc[0].get_text()
        assert "FIRST" in doc[1].get_text()


def test_refusals_leave_no_output(tmp_path):
    unsupported = tmp_path / "note.xyz"
    unsupported.write_text("x", encoding="utf-8")
    target = tmp_path / "never.pdf"
    with pytest.raises(ValueError):
        create_pdf([str(unsupported)], str(target))
    assert not target.exists()
    with pytest.raises(ValueError):
        create_pdf([], str(target))
    assert not target.exists()
    encrypted = _reject_encrypted(tmp_path / "locked.pdf")
    with pytest.raises(ValueError):
        create_pdf([str(encrypted)], str(target))
    assert not target.exists()


def test_failure_keeps_existing_target_intact(tmp_path):
    target = tmp_path / "existing.pdf"
    target.write_bytes(b"%PDF-1.4 previous content")
    unsupported = tmp_path / "note.xyz"
    unsupported.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        create_pdf([str(unsupported)], str(target))
    assert target.read_bytes() == b"%PDF-1.4 previous content"


def test_worker_publishes_verified_pdf_in_child_process(tmp_path):
    app = QApplication.instance() or QApplication([])
    source = _pdf(tmp_path / "source.pdf", text="CHILD PROCESS")
    target = tmp_path / "worker.pdf"
    worker = CreationProcess()
    loop = QEventLoop()
    results, errors, progress = [], [], []
    worker.completed.connect(lambda path: (results.append(path), loop.quit()))
    worker.failed.connect(lambda message: (errors.append(message), loop.quit()))
    worker.progress.connect(lambda a, b: progress.append((a, b)))
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(60000)
    worker.start([str(source)], str(target))
    loop.exec()
    timer.stop()
    if worker.is_running():
        worker.cancel()
        raise AssertionError("PDF creation timed out")
    assert not errors, errors
    assert results == [str(target)]
    assert progress and progress[-1] == (1, 1)
    with fitz.open(target) as doc:
        assert "CHILD PROCESS" in doc[0].get_text()
    app.processEvents()


def test_ribbon_create_button_runs_real_job(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    source = _pdf(tmp_path / "source.pdf", text="RIBBON CREATE")
    target = tmp_path / "ribbon.pdf"
    window = MainWindow()
    monkeypatch.setattr(QFileDialog, "getOpenFileNames",
                        lambda *args, **kwargs: ([str(source)], ""))
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *args, **kwargs: (str(target), "PDF"))
    observed = []

    def configure():
        dialog = window.findChild(CreatePDFDialog)
        assert dialog is not None, "Create PDF dialog did not open"
        dialog.worker.completed.connect(lambda path: (observed.append(path), dialog.accept()))
        dialog.worker.failed.connect(lambda message: dialog.reject())
        dialog._add_files()
        dialog._choose_output()

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: window.findChild(CreatePDFDialog).reject())
    timer.start(60000)
    QTimer.singleShot(0, configure)
    window.ribbon.tab_bar.setCurrentIndex(5)
    window.ribbon.findChild(QPushButton, "tool_Create_from_files").click()
    timer.stop()
    try:
        assert observed == [str(target)]
        with fitz.open(target) as doc:
            assert "RIBBON CREATE" in doc[0].get_text()
    finally:
        window.close()
        app.processEvents()


def test_create_dialog_refuses_target_equal_to_source(tmp_path):
    app = QApplication.instance() or QApplication([])
    source = _pdf(tmp_path / "same.pdf")
    dialog = CreatePDFDialog()
    dialog.add_source(str(source))
    dialog.start_creation(str(source))
    assert not dialog.worker.is_running()
    assert dialog.status.text()
    dialog.close()
    app.processEvents()
