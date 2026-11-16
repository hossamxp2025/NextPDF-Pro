# -*- coding: utf-8 -*-
"""Capture real UI screenshots of the About and Terms windows (AR and EN).

Runs the actual MainWindow and its actual dialogs, grabs the rendered widget,
and writes PNGs to docs/screenshots/. No mock-ups are drawn.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])
app.setQuitOnLastWindowClosed(False)

from src.i18n import get_translator
from src.main import setup_fonts
from src.ui.main_window import MainWindow

setup_fonts(app)

OUT = os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)


def capture_modal(path, trigger, label):
    grabbed = {"ok": False}

    def grab():
        window = app.activeModalWidget() or app.activeWindow()
        if window is None:
            print("No modal window for", label)
            return
        pixmap = window.grab()
        ok = pixmap.save(path)
        grabbed["ok"] = bool(ok)
        print(f"{label}: {pixmap.width()}x{pixmap.height()} -> {path} ({ok})")
        window.reject()

    QTimer.singleShot(700, grab)
    trigger()
    leftover = app.activeModalWidget()
    if leftover is not None:
        leftover.reject()
    return grabbed["ok"]


for language in ("ar", "en"):
    get_translator().set_language(language)
    app.setLayoutDirection(Qt.RightToLeft if language == "ar" else Qt.LeftToRight)
    window = MainWindow()
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    app.processEvents()

    capture_modal(os.path.join(OUT, f"about-{language}.png"),
                  window._show_about, f"about {language}")
    capture_modal(os.path.join(OUT, f"terms-{language}.png"),
                  window._show_terms, f"terms {language}")
    window.close()
    window.deleteLater()
    app.processEvents()

print("done")
