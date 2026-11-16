"""Closing tabs must be safe when a later nested event loop drains deletions."""
import pymupdf as fitz
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def test_close_tabs_then_run_another_event_loop(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    for i in range(2):
        path = tmp_path / f"input{i}.pdf"
        with fitz.open() as doc:
            doc.new_page()
            doc.save(path)
        assert window._open_file_path(str(path))
    for context in list(window._contexts):
        window._close_tab(window.tab_widget.indexOf(context.viewer))
    window.close()
    assert not window._contexts
    del context
    del window
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(10)
    loop.exec()
    app.processEvents()
