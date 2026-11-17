"""Ribbon, panels and icon coverage in both languages and themes."""
import os
import struct

import pymupdf as fitz
from PySide6.QtWidgets import QApplication, QPushButton

from src.config import resource_path
from src.i18n import TRANSLATIONS
from src.ui.main_window import MainWindow
from src.ui.ribbon import RibbonButton

EXPECTED_TABS = [
    ("home", "Home", "الرئيسية"),
    ("edit", "Edit PDF", "تحرير PDF"),
    ("insert", "Insert", "إدراج"),
    ("pages", "Organize Pages", "تنظيم الصفحات"),
    ("convert", "Convert PDF", "تحويل PDF"),
    ("create", "Create PDF", "إنشاء PDF"),
    ("ocr", "OCR", "التعرف الضوئي (OCR)"),
    ("forms", "Forms", "النماذج"),
    ("review", "Review", "مراجعة"),
    ("protect", "Protect and Sign", "حماية وتوقيع"),
    ("view", "View", "عرض"),
    ("settings", "Settings", "الإعدادات"),
]


def test_tabs_follow_spec_in_both_languages():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window.apply_preferences(language="en")
        app.processEvents()
        assert window.ribbon._ids == [row[0] for row in EXPECTED_TABS]
        for index, (_, english, _) in enumerate(EXPECTED_TABS):
            assert window.ribbon.tab_bar.tabText(index) == english
        window.apply_preferences(language="ar")
        app.processEvents()
        for index, (_, _, arabic) in enumerate(EXPECTED_TABS):
            assert window.ribbon.tab_bar.tabText(index) == arabic
    finally:
        window.close()
        app.processEvents()


def test_every_visible_caption_is_translated_and_unmixed():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        for language in ("en", "ar"):
            window.apply_preferences(language=language)
            app.processEvents()
            for button in window.ribbon.findChildren(RibbonButton):
                key = button.objectName()[len("tool_"):].replace("_", " ")
                expected = key if language == "en" else TRANSLATIONS["ar"].get(key, key)
                assert button.text() == expected, (language, key, button.text())
                assert "/" not in button.text(), (language, button.text())
                assert button.toolTip(), (language, key)
                if language == "en":
                    assert not any("\u0600" <= char <= "\u06ff" for char in button.text())
                else:
                    leftover = button.text()
                    for token in ("PDF", "OCR", "CSV", "PNG", "JPEG", "TIFF", "WEBP",
                                  "TXT", "HTML", "Markdown", "SVG", "JSON"):
                        leftover = leftover.replace(token, "")
                    assert not any("A" <= char <= "Z" or "a" <= char <= "z"
                                   for char in leftover), (key, button.text())
    finally:
        window.close()
        app.processEvents()


def test_every_tool_icon_exists_and_renders():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        buttons = window.ribbon.findChildren(RibbonButton)
        assert len(buttons) >= 25
        for button in buttons:
            name = button.property("iconName")
            assert name, button.objectName()
            path = resource_path(f"resources/icons/{name}.svg")
            assert os.path.isfile(path), path
            assert not button.icon().isNull(), name
            assert not button.icon().pixmap(28, 28).isNull(), name
    finally:
        window.close()
        app.processEvents()


def test_application_icon_has_every_required_size():
    path = resource_path("resources/icons/NextPDF-Pro.ico")
    with open(path, "rb") as handle:
        header = handle.read(6)
        reserved, kind, count = struct.unpack("<HHH", header)
        assert (reserved, kind) == (0, 1)
        sizes = []
        for _ in range(count):
            entry = handle.read(16)
            width, height = entry[0] or 256, entry[1] or 256
            sizes.append((width, height))
            offset = struct.unpack("<I", entry[12:16])[0]
            end = os.path.getsize(path)
            assert 0 < offset < end
    assert set(sizes) >= {(16, 16), (24, 24), (32, 32), (48, 48),
                          (64, 64), (128, 128), (256, 256)}
    for size in (16, 24, 32, 48, 64, 128, 256):
        png = resource_path(f"resources/icons/NextPDF-Pro-{size}.png")
        assert os.path.isfile(png)
        with open(png, "rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n"
        data = open(png, "rb").read(24)
        width, height = struct.unpack(">II", data[16:24])
        assert (width, height) == (size, size)


def test_panel_toggles_and_zoom_slider_are_real(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "view.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.save(path)
    window = MainWindow()
    window.show()
    assert window._open_file_path(str(path))
    try:
        pages_button = window.ribbon.findChild(QPushButton, "tool_Pages_panel")
        properties_button = window.ribbon.findChild(QPushButton, "tool_Properties_panel")
        assert pages_button and properties_button
        before = window.thumbnail_panel.isHidden()
        pages_button.click()
        app.processEvents()
        assert window.thumbnail_panel.isHidden() != before
        pages_button.click()
        app.processEvents()
        assert window.thumbnail_panel.isHidden() == before
        before = window.properties_panel.isHidden()
        properties_button.click()
        app.processEvents()
        assert window.properties_panel.isHidden() != before
        properties_button.click()
        app.processEvents()
        assert window.properties_panel.isHidden() == before
        assert (window.zoom_slider.minimum(), window.zoom_slider.maximum()) == (10, 800)
        viewer = window.tab_widget.currentWidget()
        window.zoom_slider.setValue(150)
        app.processEvents()
        assert viewer.zoom_level == 150
        window.zoom_slider.setValue(25)
        app.processEvents()
        assert viewer.zoom_level == 25
    finally:
        window.close()
        app.processEvents()
