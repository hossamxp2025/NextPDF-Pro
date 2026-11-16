#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Theme Manager for NextPDF Pro 1.1.0
نظام الثيم الاحترافي مع دعم Light/Dark Mode وRTL/LTR
"""

import os
import re
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, QLocale, Qt, QObject, QEvent
from PySide6.QtGui import QPalette, QColor


# =============================================================================
# ألوان الثيم الداكن (Modern Dark Theme)
# =============================================================================
DARK_THEME_COLORS = {
    # ألوان أساسية
    "primary": "#2563EB",           # أزرق أساسي
    "primary_hover": "#1D4ED8",
    "primary_pressed": "#1E40AF",
    "primary_light": "#DBEAFE",
    "primary_disabled": "#94A3B8",
    
    # خلفيات النوافذ
    "bg_window": "#0F172A",         # خلفية النافذة الرئيسية (داكن عميق)
    "bg_panel": "#1E293B",          # خلفية اللوحات الجانبية
    "bg_card": "#334155",           # خلفية البطاقات
    "bg_hover": "#475569",          # خلفية عند تمرير الماوس
    "bg_input": "#0F172A",          # خلفية حقول الإدخال
    "bg_selected": "#2563EB",       # خلفية العنصر المحدد
    
    # ألوان النصوص
    "text_primary": "#F8FAFC",      # نص أساسي (أبيض تقريبًا)
    "text_secondary": "#CBD5E1",    # نص ثانوي (رمادي فاتح)
    "text_muted": "#94A3B8",        # نص مكتوم (رمادي)
    "text_on_primary": "#FFFFFF",   # نص على اللون الأساسي
    "text_disabled": "#64748B",     # نص معطل
    
    # حدود
    "border_light": "#334155",      # حدود خفيفة
    "border_focus": "#2563EB",      # حدود عند التحديد
    "border_disabled": "#475569",   # حدود للمعطل
    
    # ألوان الحالة
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#3B82F6",
    
    # ألوان مميزة
    "accent": "#06B6D4",            # أزرق سماوي
    "accent_light": "#22D3EE",
    
    # الظلال
    "shadow": "rgba(0, 0, 0, 0.5)",
}


# =============================================================================
# ألوان الثيم الفاتح (Modern Light Theme)
# =============================================================================
LIGHT_THEME_COLORS = {
    # ألوان أساسية
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "primary_pressed": "#1E40AF",
    "primary_light": "#EFF6FF",
    "primary_disabled": "#94A3B8",
    
    # خلفيات النوافذ
    "bg_window": "#F8FAFC",
    "bg_panel": "#F1F5F9",
    "bg_card": "#FFFFFF",
    "bg_hover": "#E2E8F0",
    "bg_input": "#FFFFFF",
    "bg_selected": "#2563EB",
    
    # ألوان النصوص
    "text_primary": "#0F172A",
    "text_secondary": "#334155",
    "text_muted": "#64748B",
    "text_on_primary": "#FFFFFF",
    "text_disabled": "#94A3B8",
    
    # حدود
    "border_light": "#CBD5E1",
    "border_focus": "#2563EB",
    "border_disabled": "#E2E8F0",
    
    # ألوان الحالة
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#3B82F6",
    
    # ألوان مميزة
    "accent": "#06B6D4",
    "accent_light": "#CCFEFC",
    
    # الظلال
    "shadow": "rgba(0, 0, 0, 0.1)",
}

# backward compatibility
THEME_COLORS = DARK_THEME_COLORS


class ThemeManager(QObject):
    """مدير الثيم للتطبيق مع دعم Light/Dark Mode وRTL/LTR."""
    
    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self.theme_name = "dark"  # "dark" أو "light"
        self.language = "ar"      # "ar" أو "en"
        self.qss_file = None
        self._load_theme()
        self.app.installEventFilter(self)
        if hasattr(self.app.styleHints(), "colorSchemeChanged"):
            self.app.styleHints().colorSchemeChanged.connect(self._system_changed)

    @property
    def effective_theme(self):
        if self.theme_name != "system":
            return self.theme_name
        hints = self.app.styleHints()
        return "dark" if hints.colorScheme() == Qt.ColorScheme.Dark else "light"

    def _system_changed(self, *_):
        if self.theme_name == "system":
            self.apply_theme()

    @staticmethod
    def adapt_widget(widget):
        if not hasattr(widget, "styleSheet") or widget.property("documentColorControl"):
            return
        css = widget.styleSheet()
        # Replace legacy UI colour literals with palette roles. Never change
        # PDF pixmaps, document colours or the text-colour picker swatch.
        roles = {"#0f172a": "palette(window)", "#1e293b": "palette(alternate-base)",
                 "#334155": "palette(mid)", "#475569": "palette(midlight)",
                 "#f8fafc": "palette(text)", "#cbd5e1": "palette(window-text)",
                 "#94a3b8": "palette(placeholder-text)", "#64748b": "palette(placeholder-text)"}
        adapted = re.sub(r"#[0-9a-fA-F]{6}", lambda m: roles.get(m.group().lower(), m.group()), css)
        if adapted != css:
            widget.setStyleSheet(adapted)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Polish:
            self.adapt_widget(obj)
        return False
    
    def _load_theme(self):
        """تحميل ملف QSS للثيم الحالي."""
        from src.config import resource_path
        theme_dir = Path(resource_path("resources/theme"))
        if self.effective_theme == "light":
            self.qss_file = theme_dir / "modern_light.qss"
        else:
            self.qss_file = theme_dir / "modern_dark.qss"
    
    def apply_theme(self):
        """تطبيق الثيم الحالي على التطبيق."""
        self._load_theme()
        # Re-applying an identical theme is expensive: a global stylesheet
        # change repolishes every live widget.  Skip when nothing changed.
        signature = (self.effective_theme, self.language)
        if self.app.property("nextpdfThemeSignature") == signature:
            return
        self.app.setProperty("nextpdfThemeSignature", signature)
        self._applied = signature
        # تطبيق ألوان QPalette أولاً
        self._set_palette()
        
        # تطبيق QSS إذا وجد الملف
        self.app.setStyleSheet("""
            QWidget {color:palette(text); font-family:'Segoe UI'; font-size:13px;}
            QMainWindow, QDialog {background:palette(window);}
            QPushButton, QToolButton {background:palette(button);border:1px solid palette(midlight);border-radius:5px;padding:6px;}
            QPushButton:hover, QToolButton:hover {border-color:#2563eb;}
            QPushButton:pressed, QToolButton:checked {background:#2563eb;color:white;}
            QPushButton:disabled, QToolButton:disabled {color:palette(placeholder-text);}
            QLineEdit,QTextEdit,QComboBox,QSpinBox,QDoubleSpinBox {background:palette(base);color:palette(text);border:1px solid palette(midlight);border-radius:4px;padding:4px;}
            QMenuBar,QMenu {background:palette(alternate-base);color:palette(text);}
            QMenu::item:selected {background:#2563eb;color:white;}
            QTabBar::tab {padding:7px 12px;background:palette(alternate-base);}
            QTabBar::tab:selected {border-bottom:3px solid #2563eb;}
            QToolTip {background:palette(base);color:palette(text);border:1px solid palette(midlight);}
            QProgressBar {border:1px solid palette(midlight);border-radius:4px;text-align:center;}
            QProgressBar::chunk {background:#2563eb;}
        """)
        for widget in self.app.allWidgets():
            self.adapt_widget(widget)
        
        # تحديد اتجاه التخطيط بناءً على اللغة
        if self.language == "ar":
            self.app.setLayoutDirection(Qt.RightToLeft)
        else:
            self.app.setLayoutDirection(Qt.LeftToRight)
    
    def _inject_colors(self, qss: str, colors: dict) -> str:
        """استبدال متغيرات الألوان في QSS بالقيم الفعلية."""
        for key, value in colors.items():
            qss = qss.replace(f"{{{key}}}", value)
        return qss
    
    def _set_palette(self):
        """تعيين QPalette للألوان الموحدة."""
        colors = DARK_THEME_COLORS if self.effective_theme == "dark" else LIGHT_THEME_COLORS
        palette = QPalette()
        
        bg = QColor(colors["bg_window"])
        panel = QColor(colors["bg_panel"])
        text = QColor(colors["text_primary"])
        
        palette.setColor(QPalette.Window, bg)
        palette.setColor(QPalette.WindowText, text)
        palette.setColor(QPalette.PlaceholderText, QColor(colors["text_muted"]))
        palette.setColor(QPalette.Mid, QColor(colors["bg_card"]))
        palette.setColor(QPalette.Midlight, QColor(colors["border_light"]))
        palette.setColor(QPalette.Base, QColor(colors["bg_card"]))
        palette.setColor(QPalette.AlternateBase, QColor(colors["bg_panel"]))
        palette.setColor(QPalette.ToolTipBase, QColor(colors["bg_card"]))
        palette.setColor(QPalette.ToolTipText, text)
        palette.setColor(QPalette.Text, text)
        palette.setColor(QPalette.Button, QColor(colors["bg_panel"]))
        palette.setColor(QPalette.ButtonText, text)
        palette.setColor(QPalette.BrightText, QColor(colors["text_on_primary"]))
        palette.setColor(QPalette.Highlight, QColor(colors["primary"]))
        palette.setColor(QPalette.HighlightedText, QColor(colors["text_on_primary"]))
        
        self.app.setPalette(palette)
    
    def set_language(self, language: str):
        """تعيين لغة التطبيق وتحديث اتجاه التخطيط."""
        self.language = language
        self.apply_theme()
    
    def set_theme(self, theme_name: str):
        """تعيين الثيم (dark أو light)."""
        if theme_name not in {"light", "dark", "system"}:
            raise ValueError("Unknown theme")
        self.theme_name = theme_name
        self._load_theme()
        self.apply_theme()
    
    @staticmethod
    def get_color(key: str, theme: str = "dark") -> str:
        """الحصول على لون من الثيم."""
        colors = DARK_THEME_COLORS if theme == "dark" else LIGHT_THEME_COLORS
        return colors.get(key, "#000000")
    
    def is_dark(self) -> bool:
        """التحقق مما إذا كان الثيم الحالي داكنًا."""
        return self.effective_theme == "dark"

    is_dark_mode = is_dark


_instances = {}


def get_theme_manager(app):
    """One theme manager per application, so event filters never accumulate."""
    manager = _instances.get(id(app))
    if manager is None:
        manager = ThemeManager(app)
        _instances[id(app)] = manager
    return manager
