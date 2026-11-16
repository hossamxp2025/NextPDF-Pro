"""Document tabs must not close or redirect each other's PDF state."""
import pymupdf as fitz
from PySide6.QtWidgets import QApplication, QMessageBox
from src.ui.main_window import MainWindow
from src.config import set_translator_language


def test_two_document_contexts_survive_tab_switch_and_close(tmp_path):
    app = QApplication.instance() or QApplication([])
    paths = []
    for name in ("first", "second"):
        path = tmp_path / (name + ".pdf")
        doc = fitz.open()
        doc.new_page().insert_text((50, 100), name)
        doc.save(path)
        doc.close()
        paths.append(str(path))
    window = MainWindow()
    try:
        assert window._open_file_path(paths[0])
        first = window.current_context
        assert window._open_file_path(paths[1])
        second = window.current_context
        assert first is not second
        assert first.document.get_page(1).get_text().strip() == "first"
        assert second.document.get_page(1).get_text().strip() == "second"
        assert first.command_stack is not second.command_stack
        window.tab_widget.setCurrentWidget(first.viewer)
        assert window.current_context is first
        window._close_tab(window.tab_widget.indexOf(second.viewer))
        assert window.current_context is first
        assert first.document.get_page(1).get_text().strip() == "first"
    finally:
        for context in list(window._contexts):
            context.document.is_modified = False
            window._close_tab(window.tab_widget.indexOf(context.viewer))
        window.close()
        app.processEvents()


def test_window_close_releases_all_document_contexts(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    for name in ("first", "second"):
        path = tmp_path / (name + ".pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(path)
        doc.close()
        assert window._open_file_path(str(path))
    contexts = list(window._contexts)
    assert window.close()
    app.processEvents()
    assert not window._contexts
    assert all(context.document.doc is None for context in contexts)


def test_modified_tab_cancel_then_save_reopens_with_changes(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "modified.pdf"
    raw = fitz.open()
    raw.new_page().insert_text((50, 80), "original")
    raw.save(source)
    raw.close()
    window = MainWindow()
    assert window._open_file_path(str(source))
    context = window.current_context
    result = context.text_editor.add_text(1, 200, 200, "SAVED CHANGE")
    assert result.success and context.document.is_modified
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    window._close_tab(window.tab_widget.indexOf(context.viewer))
    assert context in window._contexts
    assert "SAVED CHANGE" in context.document.get_page(1).get_text()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    window._close_tab(window.tab_widget.indexOf(context.viewer))
    assert context not in window._contexts
    with fitz.open(source) as reopened:
        assert "SAVED CHANGE" in reopened[0].get_text()
    window.close()
    app.processEvents()


def test_language_switch_keeps_two_open_documents_and_unsaved_changes(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        for name in ("first", "second"):
            path = tmp_path / (name + ".pdf")
            raw = fitz.open()
            raw.new_page()
            raw.save(path)
            raw.close()
            assert window._open_file_path(str(path))
            assert window.current_context.text_editor.add_text(1, 200, 200, name).success
        contexts = list(window._contexts)
        before = [(c.document.get_page(1).get_text(),
                   c.document.get_page(1).get_pixmap().samples) for c in contexts]
        for language in ("ar", "en"):
            set_translator_language(language)
            window._retranslate_ui()
            app.processEvents()
            assert list(window._contexts) == contexts
            assert [(c.document.get_page(1).get_text(),
                     c.document.get_page(1).get_pixmap().samples) for c in contexts] == before
            assert all(c.document.is_modified for c in contexts)
    finally:
        for context in list(window._contexts):
            context.document.is_modified = False
        window.close()
        app.processEvents()


def test_window_title_tracks_active_document_and_language(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        for name in ("first", "second"):
            path = tmp_path / (name + ".pdf")
            doc = fitz.open()
            doc.new_page()
            doc.save(path)
            doc.close()
            assert window._open_file_path(str(path))
        first, second = window._contexts
        assert "second.pdf" in window.windowTitle()
        window.tab_widget.setCurrentWidget(first.viewer)
        assert "first.pdf" in window.windowTitle()
        set_translator_language("en")
        window._retranslate_ui()
        assert "first.pdf" in window.windowTitle()
        assert "Professional PDF Editor" in window.windowTitle()
    finally:
        for context in window._contexts:
            context.document.is_modified = False
        window.close()
        app.processEvents()


def test_application_close_save_then_cancel_then_discard(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    paths = []
    for name in ("first", "second"):
        path = tmp_path / (name + ".pdf")
        raw = fitz.open()
        raw.new_page().insert_text((50, 80), name)
        raw.save(path)
        raw.close()
        assert window._open_file_path(str(path))
        paths.append(path)
    first, second = window._contexts
    before_second = paths[1].read_bytes()
    assert first.text_editor.add_text(1, 200, 200, "SAVE FIRST").success
    assert second.text_editor.add_text(1, 200, 200, "DISCARD SECOND").success
    replies = iter([QMessageBox.Yes, QMessageBox.Cancel])
    monkeypatch.setattr(QMessageBox, "question", lambda *args: next(replies))
    assert not window.close()
    assert first not in window._contexts
    assert second in window._contexts and second.document.is_modified
    assert "DISCARD SECOND" in second.document.get_page(1).get_text()
    with fitz.open(paths[0]) as saved:
        assert "SAVE FIRST" in saved[0].get_text()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
    assert window.close()
    app.processEvents()
    assert not window._contexts
    assert paths[1].read_bytes() == before_second
    with fitz.open(paths[1]) as saved:
        assert "DISCARD SECOND" not in saved[0].get_text()
