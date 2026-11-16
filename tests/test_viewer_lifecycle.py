"""Qt can deliver filter events after Python attributes have been cleared."""
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication

from src.ui.pdf_viewer import PDFViewer


def test_event_filter_without_canvas_during_lifecycle():
    app = QApplication.instance() or QApplication([])
    viewer = PDFViewer(None, None, None, None)
    canvas = viewer.canvas
    del viewer.canvas
    try:
        assert viewer.eventFilter(QObject(), QEvent(QEvent.Type.User)) is False
    finally:
        viewer.canvas = canvas
        viewer.close()
        app.processEvents()
