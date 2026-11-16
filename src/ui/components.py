#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reusable UI components for NextPDF Pro (localized, theme-aware)."""

from PySide6.QtWidgets import (
    QWidget, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

from src.i18n import get_translator


class ModernButton(QPushButton):
    """Modern styled button with hover/pressed states."""

    def __init__(self, text="", icon=None, button_type="default", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        if icon is not None:
            self.setIcon(icon)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._apply_style()

    def _apply_style(self):
        type_map = {
            "default": "btnDefault",
            "primary": "btnPrimary",
            "secondary": "btnSecondary",
            "ghost": "btnGhost",
            "danger": "btnDanger",
        }
        self.setObjectName(type_map.get(self.button_type, "btnDefault"))


class ModernIconButton(QToolButton):
    """Icon-only button for toolbars."""

    def __init__(self, icon=None, tooltip="", parent=None):
        super().__init__(parent)
        self.setIcon(icon or QIcon())
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("toolIcon")
        self.setMinimumSize(38, 34)
        self.setIconSize(QSize(18, 18))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)


class Card(QFrame):
    """Card container with a title."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(8)
        self.title_label = None
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
            self.layout.addWidget(self.title_label)

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def addLayout(self, layout):
        self.layout.addLayout(layout)


class RibbonGroup(QFrame):
    """A labelled group of related buttons in the ribbon."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("ribbonButtonGroup")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("ribbonGroupTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "color: #94A3B8; font-size: 10px; font-weight: 600; margin: 0;"
        )
        if title:
            layout.addWidget(self.title_label)
        else:
            self.title_label.hide()
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(4)
        layout.addLayout(self.buttons_layout)

    def addButton(self, button):
        self.buttons_layout.addWidget(button)

    def addStretch(self):
        self.buttons_layout.addStretch()

    def retranslate(self, title: str):
        self.title_label.setText(title)
        self.title_label.setVisible(bool(title))


class EmptyState(QWidget):
    """Empty state shown when no document is open."""

    action_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        self.icon_label = QLabel("📄")
        self.icon_label.setObjectName("emptyIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 64px; margin-bottom: 8px;")
        layout.addWidget(self.icon_label)

        self.title_label = QLabel()
        self.title_label.setObjectName("emptyTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.title_label)

        self.action_btn = ModernButton("", button_type="primary")
        self.action_btn.setMinimumSize(220, 42)
        self.action_btn.clicked.connect(self.action_clicked.emit)
        layout.addWidget(self.action_btn, alignment=Qt.AlignCenter)
        self.retranslate()

    def retranslate(self):
        tr = get_translator().tr
        self.title_label.setText(tr("Open a PDF file to get started"))
        self.action_btn.setText(tr("Open PDF"))


class PropertiesPanel(QScrollArea):
    """Right sidebar with contextual properties."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("propertiesContainer")
        self.setWidgetResizable(True)
        self.setMinimumWidth(270)
        self.setMaximumWidth(400)

        self.container = QWidget()
        self.container.setObjectName("propertiesContainer")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)
        self.layout.addStretch()
        self.setWidget(self.container)
        self._state = ("empty", None)
        self.show_empty()

    # ---------------------------------------------------------------- helpers
    def _clear_layout(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().deleteLater()

    def _add_field(self, layout, label_text, value_text):
        label = QLabel(label_text)
        label.setObjectName("propLabel")
        label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        layout.addWidget(label)
        value = QLabel(str(value_text))
        value.setObjectName("propValue")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setStyleSheet("color: #F8FAFC; font-size: 13px;")
        layout.addWidget(value)

    def _empty_card(self):
        tr = get_translator().tr
        card = Card(tr("No Selection"))
        icon = QLabel("🔍")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 40px; color: #64748B;")
        card.layout.addWidget(icon)
        msg = QLabel(tr("Select an element to view its properties"))
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #94A3B8; font-size: 13px;")
        card.layout.addWidget(msg)
        return card

    def _rebuild(self):
        kind, data = self._state
        self._clear_layout()
        if kind == "text" and data:
            self._build_text(data)
        elif kind == "image" and data:
            self._build_image(data)
        else:
            self.layout.addWidget(self._empty_card())
        self.layout.addStretch()

    def retranslate(self):
        self._rebuild()

    def show_empty(self):
        self._state = ("empty", None)
        self._rebuild()

    # ------------------------------------------------------------------ states
    def _build_text(self, text_data):
        tr = get_translator().tr
        card = Card(tr("Text Properties"))
        layout = card.layout
        self._add_field(layout, tr("Font Family"), text_data.get("font_family", ""))
        self._add_field(layout, tr("Font Size"), f"{text_data.get('font_size', 0):g}")
        self._add_field(layout, tr("Color"), text_data.get("color", ""))
        self._add_field(layout, tr("Direction"), tr("Right to left") if text_data.get("direction") == "RTL" else tr("Left to right"))
        styles = []
        if text_data.get("bold"):
            styles.append(tr("Bold"))
        if text_data.get("italic"):
            styles.append(tr("Italic"))
        self._add_field(layout, tr("Style"), ", ".join(styles) if styles else tr("Regular"))
        self.layout.addWidget(card)

    def _build_image(self, image_data):
        tr = get_translator().tr
        card = Card(tr("Image Properties"))
        layout = card.layout
        self._add_field(layout, tr("Size"), f"{image_data.get('width', 0):.0f} × {image_data.get('height', 0):.0f}")
        self._add_field(layout, tr("Position"), f"X: {image_data.get('x', 0):.0f}, Y: {image_data.get('y', 0):.0f}")
        self._add_field(layout, tr("Rotation"), f"{image_data.get('rotation', 0)}°")
        self._add_field(layout, tr("Opacity"), f"{image_data.get('opacity', 1.0) * 100:.0f}%")
        self.layout.addWidget(card)

    def show_text_properties(self, text_data):
        self._state = ("text", dict(text_data))
        self._rebuild()

    def show_image_properties(self, image_data):
        self._state = ("image", dict(image_data))
        self._rebuild()


class ThumbnailItem(QWidget):
    """Single page thumbnail item."""

    page_clicked = Signal(int)

    def __init__(self, page_number, pixmap=None, parent=None):
        super().__init__(parent)
        self.page_number = page_number
        self.setFixedSize(100, 142)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(80, 100)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet(
            "QLabel { background-color: #334155; border: 1px solid #475569; border-radius: 6px; }"
        )
        if pixmap:
            self.thumb_label.setPixmap(pixmap.scaled(80, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.thumb_label.setText("📄")
        layout.addWidget(self.thumb_label, alignment=Qt.AlignCenter)

        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.page_label)
        self.retranslate()

    def retranslate(self):
        self.page_label.setText(f"{get_translator().tr('Page')} {self.page_number}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.page_clicked.emit(self.page_number)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "ThumbnailItem { background-color: #DBEAFE; border: 2px solid #2563EB; border-radius: 8px; }"
            )
        else:
            self.setStyleSheet(
                "ThumbnailItem { background-color: transparent; border: none; border-radius: 8px; }"
            )


class ThumbnailPanel(QWidget):
    """Left sidebar with page thumbnails."""

    page_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet("QWidget { background-color: #1E293B; border-bottom: 1px solid #334155; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        self.title_label = QLabel()
        self.title_label.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background-color: #0F172A; border: none; }")
        self.thumbs_container = QWidget()
        self.thumbs_layout = QVBoxLayout(self.thumbs_container)
        self.thumbs_layout.setContentsMargins(8, 8, 8, 8)
        self.thumbs_layout.setSpacing(6)
        self.thumbs_layout.addStretch()
        self.scroll.setWidget(self.thumbs_container)
        layout.addWidget(self.scroll)
        self.thumb_items = []
        self.retranslate()

    def retranslate(self):
        self.title_label.setText(get_translator().tr("Pages"))
        for item in self.thumb_items:
            item.retranslate()

    def add_thumbnail(self, page_number, pixmap=None):
        item = ThumbnailItem(page_number, pixmap)
        item.page_clicked.connect(self.page_selected.emit)
        self.thumbs_layout.insertWidget(self.thumbs_layout.count() - 1, item)
        self.thumb_items.append(item)
        return item

    def clear_thumbnails(self):
        for item in self.thumb_items:
            item.setParent(None)
            item.deleteLater()
        self.thumb_items.clear()

    def select_page(self, page_number):
        for item in self.thumb_items:
            item.set_selected(item.page_number == page_number)
