"""Capture the actual Qt window at common resolutions in both UI languages.

Run with the Windows platform plugin for native-window captures. Offscreen
captures, when explicitly requested through QT_QPA_PLATFORM, are labelled so.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtWidgets import QApplication
import pymupdf as fitz
from src.config import set_translator_language
from src.ui.main_window import MainWindow


def main():
    destination = ROOT / "docs/evidence/ribbon_reconstruction"
    destination.mkdir(parents=True, exist_ok=True)
    pdf_path = destination / "visual_fixture.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((60, 100), "NextPDF Pro - Ribbon visual fixture", fontsize=20)
        doc.save(pdf_path)
    app = QApplication([])
    window = MainWindow()
    records = []
    try:
        assert window._open_file_path(str(pdf_path))
        for language in ("en", "ar"):
            set_translator_language(language)
            window._retranslate_ui()
            for width, height in ((1366, 768), (1920, 1080), (2560, 1440)):
                window.resize(width, height)
                window.show()
                app.processEvents()
                path = destination / f"ribbon_{language}_{width}x{height}.png"
                assert window.grab().save(str(path))
                records.append({"file": path.name, "language": language,
                                "actual_size": [window.width(), window.height()],
                                "platform": app.platformName(),
                                "device_pixel_ratio": window.devicePixelRatioF()})
            window.resize(1366, 768)
            window.ribbon.tab_bar.setCurrentIndex(4)
            app.processEvents()
            assert window.grab().save(str(destination / f"conversion_{language}_1366x768.png"))
            window.ribbon.tab_bar.setCurrentIndex(0)
    finally:
        window.close()
        app.processEvents()
    (destination / "captures.json").write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
