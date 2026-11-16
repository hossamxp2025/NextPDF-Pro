"""Appearance must change Qt UI, never the rendered PDF content."""
import pymupdf as fitz
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette
from src.ui.main_window import MainWindow
from src.config import settings


def test_light_dark_preferences_preserve_two_modified_documents(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    saved = {}
    monkeypatch.setattr(settings, "set", lambda key, value: saved.update({key: value}))
    window = MainWindow()
    try:
        for index in range(2):
            path = tmp_path / f"input{index}.pdf"
            with fitz.open() as doc:
                doc.new_page()
                doc.save(path)
            assert window._open_file_path(str(path))
            assert window.current_context.text_editor.add_text(1,200,200,f"DOCUMENT {index}").success
        contexts = list(window._contexts)
        before = [(c.document.get_page(1).get_text(),c.document.get_page(1).get_pixmap().samples) for c in contexts]
        for theme, language in (("light", "en"), ("dark", "ar"), ("system", "en")):
            window.apply_preferences(theme, language)
            app.processEvents()
            assert saved["theme"] == theme and saved["language"] == language
            if theme != "system":
                lightness = app.palette().color(QPalette.Window).lightness()
                assert (lightness > 128) == (theme == "light")
            assert all(c.document.is_modified for c in contexts)
            assert [(c.document.get_page(1).get_text(),c.document.get_page(1).get_pixmap().samples) for c in contexts] == before
    finally:
        for c in window._contexts:
            c.document.is_modified = False
        window.close()
        app.processEvents()
