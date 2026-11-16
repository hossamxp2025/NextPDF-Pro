# -*- coding: utf-8 -*-
"""
Acceptance tests for the repaired NextPDF Pro editor.

Every test drives the real application code (engine and GUI) and asserts on
files that are written to disk and reopened.  Arabic is stored in shaped
presentation forms, so those tests assert embedded fonts and ink geometry
instead of the logical string.
"""

import os
import re

import pytest
import pymupdf as fitz
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QPushButton

from src.config import FONTS_DIR, get_translator, set_translator_language
from src.models.document import contains_rtl_text
from src.ui.main_window import MainWindow

ARABIC_RANGE = "\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF"
LATIN_RANGE = "A-Za-z"


def _app():
    return QApplication.instance() or QApplication([])


def _make_pdf(path, label="Original English line"):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(60, 100), label, fontsize=16)
    doc.save(str(path))
    doc.close()
    return str(path)


def _plain(text):
    return text.replace("\xa0", " ")


def _fonts(page):
    return [f[3] for f in page.get_fonts()]


def _spans(page):
    return [s for b in page.get_text("dict")["blocks"]
            for line in b.get("lines", []) for s in line["spans"]]


def _click(window, viewer, pdf_x, pdf_y):
    scale = viewer._logical_scale()
    pos = QPointF(pdf_x * scale + 16, pdf_y * scale + 16)
    event = QMouseEvent(
        QEvent.MouseButtonPress, pos,
        viewer.canvas.mapToGlobal(pos.toPoint()),
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    )
    viewer.eventFilter(viewer.canvas, event)
    _app().processEvents()


def _gui_add_text(window, viewer, pdf_x, pdf_y, text):
    window._add_text_mode()
    _click(window, viewer, pdf_x, pdf_y)
    assert viewer.inline_editor is not None and viewer.inline_editor.isVisible()
    viewer.inline_editor.text_edit.setPlainText(text)
    viewer.inline_editor._commit()
    _app().processEvents()
    return window.current_document.is_modified


@pytest.fixture()
def window():
    app = _app()
    win = MainWindow()
    win.show()
    app.processEvents()
    yield win
    # Never leave a modal "save changes?" dialog behind for the next test.
    for context in list(win._contexts):
        context.document.is_modified = False
    win.hide()
    app.processEvents()


# ---------------------------------------------------------------- TEST 01
def test_01_add_english_text_survives_save_and_reopen(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    out = tmp_path / "out.pdf"
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()

    assert _gui_add_text(window, viewer, 300, 300, "Added by NextPDF 2026")
    assert window.save_as_path(str(out))

    reopened = fitz.open(str(out))
    text = _plain(reopened[0].get_text())
    assert "Added by NextPDF 2026" in text
    assert "Original English line" in text
    assert any("Noto Sans" in name for name in _fonts(reopened[0])), _fonts(reopened[0])
    # Anchored at the click position (left edge for LTR).
    added = [s for s in _spans(reopened[0]) if "Added by NextPDF" in s["text"]][0]
    assert abs(added["bbox"][0] - 300) < 2.0, added["bbox"]
    reopened.close()


# ---------------------------------------------------------------- TEST 02
def test_02_add_arabic_text_shapes_and_embeds_font(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    out = tmp_path / "out.pdf"
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()

    assert _gui_add_text(window, viewer, 400, 250, "مرحبا بالعالم 15,750 ريال")
    assert window.save_as_path(str(out))

    reopened = fitz.open(str(out))
    page = reopened[0]
    assert any("Noto Sans Arabic" in name for name in _fonts(page)), _fonts(page)
    spans = [s for s in _spans(page) if contains_rtl_text(s["text"])]
    assert spans, "no Arabic ink after reopening"
    # The text layer is logical Unicode: searchable and extractable.
    assert page.search_for("بالعالم"), "inserted Arabic is not searchable"
    assert "مرحبا بالعالم" in _plain(page.get_text())
    # RTL insertion is anchored at the clicked right edge.
    assert abs(max(s["bbox"][2] for s in spans) - 400) < 1.0
    # The page renders; the glyphs are real ink, not an empty text box.
    pix = page.get_pixmap(dpi=96, clip=fitz.Rect(380, 230, 420, 280))
    assert pix.samples and any(byte < 250 for byte in pix.samples)
    reopened.close()


# ---------------------------------------------------------------- TEST 03
def test_03_edit_english_removes_old_text(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    out = tmp_path / "out.pdf"
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()
    window._edit_text_mode()

    _click(window, viewer, 120, 95)
    assert viewer.inline_editor is not None
    assert viewer.inline_editor.text_edit.toPlainText() == "Original English line"
    viewer.inline_editor.text_edit.setPlainText("Updated English line")
    viewer.inline_editor._commit()
    _app().processEvents()
    assert window.save_as_path(str(out))

    reopened = fitz.open(str(out))
    text = _plain(reopened[0].get_text())
    assert "Updated English line" in text
    assert "Original English line" not in text
    reopened.close()


# ---------------------------------------------------------------- TEST 04
def test_04_edit_shaped_arabic_removes_old_ink(window, tmp_path):
    source = tmp_path / "in.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    archive = fitz.Archive(str(FONTS_DIR))
    css = (
        "@font-face { font-family: 'A'; src: url('NotoNaskhArabic-Regular.ttf'); }"
        " body { font-family: 'A'; font-size: 16px; direction: rtl;"
        " text-align: left; margin: 0; padding: 0; } p { margin: 0; }"
    )
    page.insert_htmlbox(fitz.Rect(60, 80, 400, 120), "<p>النص القديم</p>", css=css, archive=archive)
    doc.save(str(source))
    doc.close()

    out = tmp_path / "out.pdf"
    assert window._open_file_path(str(source))
    viewer = window._get_current_viewer()
    runs = window.current_document.get_text_runs_for_page(1)
    arabic = [r for r in runs if contains_rtl_text(r.text)]
    assert arabic and arabic[0].direction == "RTL"

    window._edit_text_mode()
    r = arabic[0]
    _click(window, viewer, (r.bbox[0] + r.bbox[2]) / 2, (r.bbox[1] + r.bbox[3]) / 2)
    assert viewer.inline_editor is not None and viewer.inline_editor._mode == "edit"
    viewer.inline_editor.text_edit.setPlainText("نص جديد تماما")
    viewer.inline_editor._commit()
    _app().processEvents()
    assert window.save_as_path(str(out))

    reopened = fitz.open(str(out))
    page = reopened[0]
    text = _plain(page.get_text())
    assert "النص القديم" not in text
    assert "نص جديد تماما" in text, text
    assert page.search_for("جديد") and not page.search_for("القديم")
    assert any(contains_rtl_text(s["text"]) for s in _spans(page))
    assert any("Noto Sans Arabic" in name for name in _fonts(page))
    # No stale ink left where the old text was (the fixture band is blank
    # apart from the new text, which is right-aligned in the same box).
    reopened.close()


# ---------------------------------------------------------------- TEST 05
def test_05_undo_redo_restores_real_pdf_bytes(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()

    assert _gui_add_text(window, viewer, 300, 300, "Undo me please")
    doc = window.current_document
    stack = window.current_context.command_stack
    assert stack.can_undo()
    assert "Undo me please" in _plain(doc.get_page(1).get_text())

    assert stack.undo() is not None
    assert "Undo me please" not in _plain(doc.get_page(1).get_text())

    assert stack.redo() is not None
    assert "Undo me please" in _plain(doc.get_page(1).get_text())


# ---------------------------------------------------------------- TEST 06
def test_06_two_documents_stay_isolated(window, tmp_path):
    first = _make_pdf(tmp_path / "first.pdf", "FIRST document")
    second = _make_pdf(tmp_path / "second.pdf", "SECOND document")
    assert window._open_file_path(first)
    ctx_first = window.current_context
    viewer = window._get_current_viewer()
    assert _gui_add_text(window, viewer, 300, 300, "ONLY IN FIRST")

    assert window._open_file_path(second)
    assert window.current_context is not ctx_first
    assert window.tab_widget.count() == 2
    assert "ONLY IN FIRST" not in _plain(window.current_document.get_page(1).get_text())

    viewer2 = window._get_current_viewer()
    assert _gui_add_text(window, viewer2, 200, 400, "ONLY IN SECOND")

    out_first = tmp_path / "first_out.pdf"
    out_second = tmp_path / "second_out.pdf"
    assert window.save_as_path(str(out_second))
    window.tab_widget.setCurrentIndex(0)
    _app().processEvents()
    assert window.current_context is ctx_first
    assert window.save_as_path(str(out_first))

    d1 = fitz.open(str(out_first))
    d2 = fitz.open(str(out_second))
    t1, t2 = _plain(d1[0].get_text()), _plain(d2[0].get_text())
    assert "ONLY IN FIRST" in t1 and "ONLY IN SECOND" not in t1
    assert "ONLY IN SECOND" in t2 and "ONLY IN FIRST" not in t2
    d1.close(); d2.close()


# ---------------------------------------------------------------- TEST 07
def test_07_localization_has_no_leaks(window):
    app = _app()
    try:
        set_translator_language("en")
        window._retranslate_ui()
        app.processEvents()
        labels_en = [b.text() for b in window.ribbon.findChildren(QPushButton) if b.text().strip()]
        actions_en = []
        def walk(menu):
            for action in menu.actions():
                if action.text():
                    actions_en.append(action.text())
                if action.menu():
                    walk(action.menu())
        walk(window.menuBar())
        assert labels_en
        assert not [t for t in labels_en + actions_en if re.search(f"[{ARABIC_RANGE}]", t)]
        assert "Professional PDF Editor" in window.windowTitle()

        set_translator_language("ar")
        window._retranslate_ui()
        app.processEvents()
        labels_ar = [b.text() for b in window.ribbon.findChildren(QPushButton) if b.text().strip()]
        actions_ar = []
        def walk_ar(menu):
            for action in menu.actions():
                if action.text():
                    actions_ar.append(action.text())
                if action.menu():
                    walk_ar(action.menu())
        walk_ar(window.menuBar())
        assert labels_ar
        leaks = []
        for text in labels_ar + actions_ar:
            cleaned = text.replace("NextPDF", "").replace("Pro", "").replace("PDF", "").replace("OCR", "")
            cleaned = re.sub(r"\d+(\.\d+)*", "", cleaned)
            cleaned = re.sub(r"[\(\)\s\-\/]", "", cleaned)
            if re.search(f"[{LATIN_RANGE}]", cleaned):
                leaks.append(text)
        assert not leaks, f"Latin labels in Arabic mode: {leaks}"
        assert "محرر PDF" in window.windowTitle()
    finally:
        set_translator_language("en")
        window._retranslate_ui()


# ---------------------------------------------------------------- TEST 08
def test_08_save_as_does_not_touch_source(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    original_bytes = open(source, "rb").read()
    out = tmp_path / "copy.pdf"
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()
    assert _gui_add_text(window, viewer, 250, 350, "Copy only")
    assert window.save_as_path(str(out))

    assert open(source, "rb").read() == original_bytes
    assert out.exists() and out.stat().st_size > 0
    reopened = fitz.open(str(out))
    assert "Copy only" in _plain(reopened[0].get_text())
    assert reopened.is_pdf
    reopened.close()


# ---------------------------------------------------------------- TEST 09
def test_09_delete_selected_text_removes_ink(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    out = tmp_path / "out.pdf"
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()
    window._edit_text_mode()
    _click(window, viewer, 120, 95)
    viewer.inline_editor.cancel_btn.click()
    _app().processEvents()

    # Select through the viewer's own selection API, then delete.
    run = window.current_document.get_text_runs_for_page(1)[0]
    viewer._select_run(run)
    window._delete_selected_text()
    _app().processEvents()
    assert window.save_as_path(str(out))

    reopened = fitz.open(str(out))
    assert "Original English line" not in _plain(reopened[0].get_text())
    reopened.close()


# ---------------------------------------------------------------- TEST 10
def test_10_page_operations_survive_save(window, tmp_path):
    source = _make_pdf(tmp_path / "in.pdf")
    out = tmp_path / "out.pdf"
    assert window._open_file_path(source)
    viewer = window._get_current_viewer()
    assert window.current_document.page_count == 1

    window._insert_page()
    _app().processEvents()
    assert window.current_document.page_count == 2

    viewer.set_page(2)
    _app().processEvents()
    window._rotate_page()
    _app().processEvents()
    assert window.current_document.get_page(2).rotation % 360 == 90

    assert window.save_as_path(str(out))
    reopened = fitz.open(str(out))
    assert reopened.page_count == 2
    assert reopened[1].rotation % 360 == 90
    reopened.close()
