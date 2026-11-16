#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبارات انحدار لواجهة NextPDF Pro
يختبر استيراد جميع الوحدات وإنشاء النافذة والتبديل بين الثيمات واللغات.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication

# Ensure QApplication exists
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestImports:
    """اختبارات استيراد جميع الوحدات."""

    def test_import_config(self):
        """استيراد وحدة الإعدادات."""
        from src.config import (
            settings, APP_NAME, APP_VERSION, APP_ORGANIZATION,
            LOG_FILE, DATA_DIR, LOG_DIR, resource_path, BUILD_ID,
        )
        from src.version import APP_VERSION as CANONICAL_VERSION
        assert APP_NAME == "NextPDF Pro"
        # src.version is the single source of truth; config must not drift.
        assert APP_VERSION == CANONICAL_VERSION
        assert BUILD_ID is not None

    def test_import_theme_manager(self):
        """استيراد مدير الثيم."""
        from src.ui.theme_manager import (
            ThemeManager, THEME_COLORS, DARK_THEME_COLORS, LIGHT_THEME_COLORS,
        )
        assert ThemeManager is not None
        assert THEME_COLORS is not None
        assert DARK_THEME_COLORS is not None
        assert LIGHT_THEME_COLORS is not None

    def test_import_main_window(self):
        """استيراد النافذة الرئيسية."""
        from src.ui.main_window import MainWindow
        assert MainWindow is not None

    def test_import_pdf_viewer(self):
        """استيراد عارض PDF."""
        from src.ui.pdf_viewer import PDFViewer
        assert PDFViewer is not None

    def test_import_components(self):
        """استيراد المكونات."""
        from src.ui.components import (
            ModernButton, ModernIconButton, Card, RibbonGroup,
            EmptyState, PropertiesPanel, ThumbnailPanel, ThumbnailItem,
        )
        assert ModernButton is not None
        assert Card is not None
        assert RibbonGroup is not None

    def test_import_engine_modules(self):
        """استيراد محركات المعالجة."""
        from src.engine.text_editor import TextEditor
        from src.engine.page_manager import PageManager
        from src.engine.image_editor import ImageEditor
        from src.engine.ocr_engine import OCREngine
        assert TextEditor is not None
        assert PageManager is not None
        assert ImageEditor is not None
        assert OCREngine is not None

    def test_import_document_model(self):
        """استيراد نموذج البيانات."""
        from src.models.document import PDFDocument, TextRun
        assert PDFDocument is not None
        assert TextRun is not None

    def test_import_command_stack(self):
        """استيراد نظام الأوامر."""
        from src.commands.command import CommandStack
        assert CommandStack is not None


class TestThemeManager:
    """اختبارات مدير الثيم."""

    def test_theme_manager_creation(self):
        """إنشاء مدير الثيم."""
        from src.ui.theme_manager import ThemeManager
        tm = ThemeManager(app)
        assert tm is not None
        assert tm.theme_name == "dark"

    def test_theme_colors_accessible(self):
        """الوصول إلى ألوان الثيم."""
        from src.ui.theme_manager import THEME_COLORS, DARK_THEME_COLORS, LIGHT_THEME_COLORS
        assert THEME_COLORS["primary"] == "#2563EB"
        assert DARK_THEME_COLORS["bg_window"] == "#0F172A"
        assert LIGHT_THEME_COLORS["bg_window"] == "#F8FAFC"

    def test_get_color(self):
        """دالة get_color."""
        from src.ui.theme_manager import ThemeManager
        color = ThemeManager.get_color("primary", "dark")
        assert color == "#2563EB"
        color = ThemeManager.get_color("primary", "light")
        assert color == "#2563EB"

    def test_switch_theme(self):
        """التبديل بين الثيمات."""
        from src.ui.theme_manager import ThemeManager
        tm = ThemeManager(app)
        assert tm.theme_name == "dark"
        tm.set_theme("light")
        assert tm.theme_name == "light"
        tm.set_theme("dark")
        assert tm.theme_name == "dark"

    def test_is_dark(self):
        """التحقق من الثيم الداكن."""
        from src.ui.theme_manager import ThemeManager
        tm = ThemeManager(app)
        assert tm.is_dark() is True
        tm.set_theme("light")
        assert tm.is_dark() is False


class TestMainWindow:
    """اختبارات النافذة الرئيسية."""

    def test_window_creation(self):
        """إنشاء النافذة الرئيسية."""
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window is not None
        from src.version import APP_VERSION
        assert window.windowTitle().startswith(f"NextPDF Pro {APP_VERSION}")
        window.close()

    def test_ribbon_exists(self):
        """وجود الشريط العلوي."""
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window.ribbon is not None
        assert window.ribbon.current_tab_id is not None
        window.close()

    def test_sidebar_panels(self):
        """وجود اللوحات الجانبية."""
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window.thumbnail_panel is not None
        assert window.properties_panel is not None
        window.close()

    def test_pdf_viewer_tab(self):
        """وجود عارض PDF."""
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window.tab_widget is not None
        assert window.tab_widget.count() >= 1  # empty state tab
        window.close()

    def test_status_bar(self):
        """وجود شريط الحالة."""
        from src.ui.main_window import MainWindow
        window = MainWindow()
        assert window.status_bar is not None
        assert window.page_label is not None
        assert window.zoom_label is not None
        assert window.status_label is not None
        window.close()

    def test_language_switch(self):
        """تبديل اللغة."""
        from src.ui.main_window import MainWindow
        from src.config import get_translator
        window = MainWindow()
        translator = get_translator()
        translator.set_language("en")
        window._retranslate_ui()
        assert "Professional PDF Editor" in window.windowTitle()
        translator.set_language("ar")
        window._retranslate_ui()
        assert "محرر PDF" in window.windowTitle()
        window.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
