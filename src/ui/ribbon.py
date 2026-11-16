"""Professional tabbed ribbon.

Each tab is a horizontal scroller of labelled groups. Buttons show a tinted
vector icon above a caption that is never clipped (the button grows to fit,
and the ribbon scrolls horizontally). Full caption is also the tooltip.
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabBar,
                              QStackedWidget, QScrollArea, QPushButton, QLabel,
                              QFrame, QSizePolicy)
from src.config import resource_path
from src.i18n import get_translator

TAB_HEIGHT = 38
BUTTON_HEIGHT = 76
MIN_BUTTON_WIDTH = 78
ICON_SIZE = 28
ICON_TOP = 7
TEXT_TOP = ICON_TOP + ICON_SIZE + 3


def tinted_icon(name, color):
    """Recolour a monochrome SVG so icons stay legible in every theme."""
    if not name:
        return QIcon()
    source = QPixmap(resource_path(f"resources/icons/{name}.svg"))
    if source.isNull():
        return QIcon()
    scaled = source.scaled(ICON_SIZE * 2, ICON_SIZE * 2, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
    tinted = QPixmap(scaled.size())
    tinted.fill(Qt.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, scaled)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color))
    painter.end()
    return QIcon(tinted)


class RibbonButton(QPushButton):
    """Icon-above-caption button with explicit hover/pressed/disabled paint."""

    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setObjectName("ribbonTool")
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMinimumHeight(BUTTON_HEIGHT)
        self.setMaximumHeight(BUTTON_HEIGHT)
        self._hover = False

    def sizeHint(self):
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        width = max(MIN_BUTTON_WIDTH, text_width + 20)
        return QSize(width, BUTTON_HEIGHT)

    def minimumSizeHint(self):
        return self.sizeHint()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        palette = self.palette()
        pressed = self.isDown() and self.isEnabled()
        if pressed:
            background = QColor("#2563EB")
            text_colour = QColor("#FFFFFF")
        elif not self.isEnabled():
            background = None
            text_colour = palette.placeholderText().color()
        elif self._hover:
            background = palette.midlight().color()
            text_colour = palette.windowText().color()
        else:
            background = None
            text_colour = palette.windowText().color()
        if background is not None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(rect, 8, 8)
            if self._hover and not pressed:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QColor("#2563EB"))
                painter.drawRoundedRect(rect, 8, 8)

        icon = self.icon()
        if not icon.isNull():
            pixmap = icon.pixmap(QSize(ICON_SIZE, ICON_SIZE))
            painter.drawPixmap((self.width() - pixmap.width()) // 2, ICON_TOP, pixmap)

        painter.setPen(text_colour)
        font = self.font()
        font.setPointSizeF(9.5)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        available = self.width() - 8
        text = self.text()
        if metrics.horizontalAdvance(text) > available:
            text = metrics.elidedText(text, Qt.ElideRight, available)
        painter.drawText(0, TEXT_TOP, self.width(), metrics.height(),
                         Qt.AlignHCenter | Qt.AlignTop, text)
        painter.end()


class Ribbon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mainRibbon")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("ribbonTabs")
        self.tab_bar.setExpanding(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.setElideMode(Qt.ElideNone)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setFixedHeight(TAB_HEIGHT)
        self.stack = QStackedWidget()
        self._ids = []
        self.document_buttons = []
        self._icon_color = "#334155"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tab_bar)
        layout.addWidget(self.stack)
        self.tab_bar.currentChanged.connect(self.stack.setCurrentIndex)
        self.setFixedHeight(TAB_HEIGHT + BUTTON_HEIGHT + 22)
        self.setStyleSheet(f"""
          #mainRibbon {{background:palette(alternate-base);
                         border-bottom:1px solid palette(midlight);}}
          #ribbonTabs {{background:transparent;}}
          #ribbonTabs::tab {{padding:0 18px; margin:0; min-height:{TAB_HEIGHT - 2}px;
                              color:palette(window-text); font-size:13px;}}
          #ribbonTabs::tab:selected {{color:palette(text); font-weight:600;
                                        border-bottom:3px solid #2563EB;}}
          #ribbonTabs::tab:hover {{background:palette(midlight);}}
          QLabel#ribbonGroup {{color:palette(placeholder-text); font-size:11px;
                                padding:1px 6px 3px 6px;}}
          QFrame#ribbonGroupFrame {{border-right:1px solid palette(midlight);
                                     margin:5px 0;}}
        """)

    # -- public API -------------------------------------------------------
    @property
    def current_tab_id(self):
        index = self.tab_bar.currentIndex()
        return self._ids[index] if 0 <= index < len(self._ids) else None

    def set_icon_color(self, color):
        self._icon_color = color
        for button in self.findChildren(RibbonButton):
            name = button.property("iconName")
            if name:
                button.setIcon(tinted_icon(name, self._icon_color))

    def add_page(self, identity, title, tools=None, groups=None):
        """Add a tab. ``groups`` is [(group_title, tools)]; flat ``tools`` is
        wrapped in a single unnamed group for compatibility."""
        tr = get_translator().tr
        if groups is None:
            groups = [("", tools or [])]
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(8, 3, 8, 3)
        row.setSpacing(6)
        for group_title, group_tools in groups:
            frame = QFrame()
            frame.setObjectName("ribbonGroupFrame")
            column = QVBoxLayout(frame)
            column.setContentsMargins(4, 2, 6, 0)
            column.setSpacing(0)
            buttons = QHBoxLayout()
            buttons.setContentsMargins(0, 0, 0, 0)
            buttons.setSpacing(2)
            for key, handler, icon, needs_document in group_tools:
                buttons.addWidget(self._make_button(key, handler, icon, needs_document))
            column.addLayout(buttons)
            caption = QLabel(tr(group_title) if group_title else "")
            caption.setObjectName("ribbonGroup")
            caption.setAlignment(Qt.AlignHCenter)
            caption.setVisible(bool(group_title))
            column.addWidget(caption)
            row.addWidget(frame)
        row.addStretch()
        scroll = QScrollArea()
        scroll.setObjectName("ribbonScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(container)
        self._ids.append(identity)
        self.stack.addWidget(scroll)
        self.tab_bar.addTab(tr(title))

    def _make_button(self, key, handler, icon, needs_document):
        tr = get_translator().tr
        label = tr(key)
        button = RibbonButton(label)
        button.setObjectName("tool_" + key.replace(" ", "_"))
        button.setProperty("iconName", icon)
        button.setToolTip(label if handler else f"{label} — {tr('Not implemented')}")
        button.setAccessibleName(label)
        if icon:
            button.setIcon(tinted_icon(icon, self._icon_color))
        button.setEnabled(handler is not None)
        if handler:
            button.clicked.connect(handler)
            if needs_document:
                self.document_buttons.append(button)
        return button

    def set_document_available(self, available):
        for button in self.document_buttons:
            button.setEnabled(available)
