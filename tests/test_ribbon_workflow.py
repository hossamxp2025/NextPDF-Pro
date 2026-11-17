"""Real Qt tab selection must change the visible tool page."""
from PySide6.QtWidgets import QApplication, QTabBar, QStackedWidget, QPushButton
import pymupdf as fitz
from tests.test_acceptance import _click
from src.ui.main_window import MainWindow


def test_ribbon_selects_real_tool_pages():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        tabs = window.ribbon.findChild(QTabBar)
        stack = window.ribbon.findChild(QStackedWidget)
        assert tabs is not None and stack is not None
        assert tabs.count() == stack.count() == 12
        tabs.setCurrentIndex(3)
        app.processEvents()
        assert stack.currentIndex() == 3
        assert window.ribbon.current_tab_id == "pages"
        tabs.setCurrentIndex(1)
        app.processEvents()
        assert stack.currentIndex() == 1
        assert window.ribbon.current_tab_id == "edit"
    finally:
        window.close()
        app.processEvents()


def test_ribbon_add_text_and_save_buttons_write_active_pdf(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "ribbon_edit.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.save(path)
    window = MainWindow()
    window.show()
    try:
        assert window._open_file_path(str(path))
        window.ribbon.tab_bar.setCurrentIndex(1)
        window.ribbon.findChild(QPushButton, "tool_Add_Text").click()
        viewer = window.current_context.viewer
        _click(window, viewer, 200, 200)
        assert viewer.inline_editor is not None
        viewer.inline_editor.text_edit.setPlainText("RIBBON VERIFIED 2026")
        viewer.inline_editor.apply_btn.click()
        app.processEvents()
        assert window.current_document.is_modified
        window.ribbon.tab_bar.setCurrentIndex(0)
        window.ribbon.findChild(QPushButton, "tool_Save").click()
        assert not window.current_document.is_modified
        with fitz.open(path) as saved:
            assert "RIBBON VERIFIED 2026" in saved[0].get_text()
    finally:
        for context in window._contexts:
            context.document.is_modified = False
        window.close()
        app.processEvents()
