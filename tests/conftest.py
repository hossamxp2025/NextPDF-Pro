# -*- coding: utf-8 -*-
"""Headless Qt for every test module (set before Qt is imported)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qt_application_session():
    """Keep one application alive for all tests, including nested event loops.

    Individual window-close tests must not post an application-wide Quit event
    that stops a later QProcess test before its finished signal is delivered.
    """
    app = QApplication.instance() or QApplication([])
    original = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    yield app
    app.processEvents()
    app.setQuitOnLastWindowClosed(original)


@pytest.fixture(autouse=True)
def dispose_main_windows():
    """Destroy windows after each test so theme changes do not repolish
    hundreds of abandoned widgets (a test-session artefact, not app behaviour)."""
    yield
    app = QApplication.instance()
    if app is None:
        return
    from src.ui.main_window import MainWindow
    for widget in list(app.topLevelWidgets()):
        if isinstance(widget, MainWindow):
            for context in getattr(widget, "_contexts", []):
                context.document.is_modified = False
            widget.close()
            widget.deleteLater()
    app.processEvents()

