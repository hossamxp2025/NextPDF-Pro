#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF viewer for NextPDF Pro.

The page is painted by a dedicated canvas widget.  All coordinate conversion
goes through one place (`PageCanvas.widget_to_pdf` / `pdf_to_widget`) which
accounts for the page margins, zoom, the 96-DPI display scale, the device pixel
ratio and page rotation.  Mouse events are already widget-relative; scrollbar
offsets are never added back.
"""

import logging
from typing import List, Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame,
    QToolButton, QComboBox, QDoubleSpinBox, QTextEdit, QColorDialog,
    QSizePolicy, QSpinBox,
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, Signal, QEvent
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont, QMouseEvent,
    QWheelEvent, QCursor, QKeyEvent, QPolygonF, QGuiApplication,
)

from src.i18n import get_translator
from src.engine.text_editor import TextEditor, DEFAULT_FONT, _DISPLAY_FONTS

logger = logging.getLogger("NextPDF")

VIEW_DPI = 96.0          # 100 % zoom means 96 device-independent px per inch
PAGE_MARGIN = 16         # canvas margin around the page, in logical pixels
MODE_SELECT = "select"
MODE_EDIT_TEXT = "edit_text"
MODE_ADD_TEXT = "add_text"
MODE_REDACT = "redact"
MODE_COMMENT = "comment"
MODE_FIELD = "field"


class TextEditOverlay(QFrame):
    """Floating inline editor used for both Add Text and Edit Text."""

    committed = Signal(object)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("textOverlay")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame#textOverlay {
                background-color: #1E293B;
                border: 1px solid #2563EB;
                border-radius: 8px;
            }
            QFrame#textOverlay QLabel { color: #CBD5E1; font-size: 11px; }
            QFrame#textOverlay QComboBox, QFrame#textOverlay QDoubleSpinBox,
            QFrame#textOverlay QSpinBox {
                background-color: #0F172A; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 4px; padding: 2px 4px;
                min-height: 22px;
            }
            QFrame#textOverlay QTextEdit {
                background-color: #0F172A; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 6px;
                padding: 4px; font-size: 14px;
            }
            QFrame#textOverlay QToolButton {
                background-color: #334155; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 4px;
                padding: 3px 8px; min-height: 22px;
            }
            QFrame#textOverlay QToolButton:hover { background-color: #475569; }
            QFrame#textOverlay QToolButton:checked { background-color: #2563EB; }
        """)
        self.setFixedWidth(380)
        self._mode = "add"
        self._run = None
        self._pdf_point = (0.0, 0.0)
        self._page = 1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        tr = get_translator().tr
        self.title_label = QLabel(tr("Enter text"))
        self.title_label.setStyleSheet("color: #F8FAFC; font-weight: 600; font-size: 12px;")
        layout.addWidget(self.title_label)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.font_combo = QComboBox()
        for font in _DISPLAY_FONTS:
            label = tr("Default font") if font == DEFAULT_FONT else font
            self.font_combo.addItem(label, font)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(6, 200)
        self.size_spin.setValue(14)
        self.size_spin.setDecimals(1)
        self.size_spin.setSingleStep(1)
        self.size_spin.setFixedWidth(70)
        self.color_btn = QToolButton()
        self.color_btn.setProperty("documentColorControl", True)
        self.color_btn.setText("A")
        self.color_btn.setToolTip(tr("Color"))
        self.color_btn.clicked.connect(self._pick_color)
        self.color = QColor("#000000")
        self._update_color_button()
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setToolTip(tr("Bold"))
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setToolTip(tr("Italic"))
        row1.addWidget(self.font_combo, 1)
        row1.addWidget(self.size_spin)
        row1.addWidget(self.color_btn)
        row1.addWidget(self.bold_btn)
        row1.addWidget(self.italic_btn)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem(tr("Auto"), "auto")
        self.direction_combo.addItem(tr("Left to right"), "LTR")
        self.direction_combo.addItem(tr("Right to left"), "RTL")
        self._direction_touched = False
        self.direction_combo.currentIndexChanged.connect(self._direction_changed)
        row2.addWidget(QLabel(tr("Direction")))
        row2.addWidget(self.direction_combo, 1)
        layout.addLayout(row2)

        self.text_edit = QTextEdit()
        self.text_edit.setFixedHeight(88)
        self.text_edit.setPlaceholderText(tr("Enter text"))
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.installEventFilter(self)
        layout.addWidget(self.text_edit)

        row3 = QHBoxLayout()
        row3.addStretch()
        self.cancel_btn = QToolButton()
        self.cancel_btn.setText(tr("Cancel"))
        self.cancel_btn.clicked.connect(self._cancel)
        self.apply_btn = QToolButton()
        self.apply_btn.setText(tr("Apply"))
        self.apply_btn.setStyleSheet(
            "QToolButton { background-color: #2563EB; color: white; "
            "border: none; border-radius: 4px; padding: 5px 14px; }"
        )
        self.apply_btn.clicked.connect(self._commit)
        row3.addWidget(self.cancel_btn)
        row3.addWidget(self.apply_btn)
        layout.addLayout(row3)

    # ------------------------------------------------------------------ setup
    def configure_add(self, page: int, x: float, y: float):
        self._mode = "add"
        self._run = None
        self._page = page
        self._pdf_point = (x, y)
        self.title_label.setText(get_translator().tr("Enter text"))
        self.text_edit.clear()
        self.apply_btn.setText(get_translator().tr("Apply"))
        self.cancel_btn.setText(get_translator().tr("Cancel"))
        self.text_edit.setFocus()

    def configure_edit(self, page: int, run):
        self._mode = "edit"
        self._run = run
        self._page = page
        self._pdf_point = (run.x, run.y)
        self.title_label.setText(get_translator().tr("Edit text"))
        self.text_edit.setPlainText(run.text)
        self.size_spin.setValue(float(run.font_size or 12))
        self.font_combo.setCurrentIndex(0)
        if run.direction == "RTL":
            self.direction_combo.setCurrentIndex(2)
            self._direction_touched = True
        else:
            self.direction_combo.setCurrentIndex(1)
            self._direction_touched = True
        self.bold_btn.setChecked(bool(run.bold))
        self.italic_btn.setChecked(bool(run.italic))
        c = QColor.fromRgbF(*(list(run.color) + [1.0])[:3])
        self.color = c
        self._update_color_button()
        self.text_edit.setFocus()
        self.text_edit.selectAll()

    def retranslate(self):
        tr = get_translator().tr
        self.title_label.setText(tr("Edit text") if self._mode == "edit" else tr("Enter text"))
        self.cancel_btn.setText(tr("Cancel"))
        self.apply_btn.setText(tr("Apply"))
        self.text_edit.setPlaceholderText(tr("Enter text"))
        self.color_btn.setToolTip(tr("Color"))
        self.bold_btn.setToolTip(tr("Bold"))
        self.italic_btn.setToolTip(tr("Italic"))
        self.direction_combo.setItemText(0, tr("Auto"))
        self.direction_combo.setItemText(1, tr("Left to right"))
        self.direction_combo.setItemText(2, tr("Right to left"))

    # ----------------------------------------------------------------- events
    def _pick_color(self):
        color = QColorDialog.getColor(self.color, self, get_translator().tr("Color"))
        if color.isValid():
            self.color = color
            self._update_color_button()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"QToolButton {{ background-color: {self.color.name()}; color: "
            f"{'#000000' if self.color.lightness() > 128 else '#FFFFFF'}; "
            "border: 1px solid #475569; border-radius: 4px; font-weight: 700; }}"
        )

    def _direction_changed(self, _index):
        if self.sender() is self.direction_combo:
            self._direction_touched = True

    def _on_text_changed(self):
        if self._direction_touched:
            return
        text = self.text_edit.toPlainText()
        has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in text)
        self.direction_combo.blockSignals(True)
        self.direction_combo.setCurrentIndex(2 if has_arabic else 1)
        self.direction_combo.blockSignals(False)

    def eventFilter(self, obj, event):
        if obj is self.text_edit and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self._cancel()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter) and (event.modifiers() & Qt.ControlModifier):
                self._commit()
                return True
        return super().eventFilter(obj, event)

    def _direction(self) -> str:
        value = self.direction_combo.currentData()
        if value in ("LTR", "RTL"):
            return value
        text = self.text_edit.toPlainText()
        return "RTL" if any("\u0600" <= ch <= "\u06FF" for ch in text) else "LTR"

    def _commit(self):
        text = self.text_edit.toPlainText()
        if not text.strip():
            self._cancel()
            return
        payload = {
            "mode": self._mode,
            "page": self._page,
            "x": self._pdf_point[0],
            "y": self._pdf_point[1],
            "text": text,
            "font": self.font_combo.currentData() or DEFAULT_FONT,
            "size": float(self.size_spin.value()),
            "color": (self.color.redF(), self.color.greenF(), self.color.blueF()),
            "direction": self._direction(),
            "bold": self.bold_btn.isChecked(),
            "italic": self.italic_btn.isChecked(),
            "run": self._run,
        }
        self.committed.emit(payload)

    def _cancel(self):
        self.hide()
        self.cancelled.emit()


class PageCanvas(QWidget):
    """Paints one PDF page and performs exact coordinate mapping."""

    def __init__(self, viewer, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self._pixmap: Optional[QPixmap] = None
        self._page_rect = fitz.Rect(0, 0, 595, 842)
        self._rotation = 0
        self._scale = VIEW_DPI / 72.0
        self._selection_rects: List[tuple] = []   # PDF bboxes
        self._search_rects: List[tuple] = []      # PDF bboxes
        self._redact_rects: List[tuple] = []      # PDF bboxes marked for removal
        self._annotation_rect = None              # the selected comment's bbox
        self._drag_rect: Optional[QRectF] = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    # ---------------------------------------------------------------- geometry
    def set_page(self, pixmap: QPixmap, page_rect, rotation: int, scale: float):
        self._pixmap = pixmap
        self._page_rect = fitz.Rect(page_rect)
        self._rotation = int(rotation)
        self._scale = float(scale)
        if pixmap is not None:
            dpr = pixmap.devicePixelRatio() or 1.0
            logical_w = pixmap.width() / dpr
            logical_h = pixmap.height() / dpr
        else:
            logical_w = self._page_rect.width * scale
            logical_h = self._page_rect.height * scale
        self.setFixedSize(
            int(round(logical_w)) + PAGE_MARGIN * 2,
            int(round(logical_h)) + PAGE_MARGIN * 2,
        )
        self.update()

    @property
    def scale(self) -> float:
        return self._scale

    def widget_to_pdf(self, pos: QPointF) -> Optional[fitz.Point]:
        """Map a canvas-relative point to unrotated PDF page coordinates."""
        page = self.viewer.document.get_page(self.viewer.current_page) if self.viewer.document else None
        if page is None:
            return None
        x = (pos.x() - PAGE_MARGIN) / self._scale
        y = (pos.y() - PAGE_MARGIN) / self._scale
        point = fitz.Point(x, y)
        try:
            return point * page.derotation_matrix
        except Exception:
            return point

    def pdf_to_widget(self, rect_like) -> QPolygonF:
        """Map a PDF bbox to a widget-space polygon (rotation aware)."""
        rect = fitz.Rect(rect_like)
        page = self.viewer.document.get_page(self.viewer.current_page) if self.viewer.document else None
        matrix = page.rotation_matrix if page is not None else fitz.Matrix(1, 0, 0, 1, 0, 0)
        points = [
            fitz.Point(rect.x0, rect.y0), fitz.Point(rect.x1, rect.y0),
            fitz.Point(rect.x1, rect.y1), fitz.Point(rect.x0, rect.y1),
        ]
        poly = QPolygonF()
        for p in points:
            try:
                p = p * matrix
            except Exception:
                pass
            poly.append(QPointF(p.x * self._scale + PAGE_MARGIN,
                                p.y * self._scale + PAGE_MARGIN))
        return poly

    def set_selection(self, bboxes: List[tuple]):
        self._selection_rects = list(bboxes or [])
        self.update()

    def set_search_rects(self, bboxes: List[tuple]):
        self._search_rects = list(bboxes or [])
        self.update()

    def clear_search(self):
        self._search_rects = []
        self.update()

    def set_redact_rects(self, bboxes: List[tuple]):
        self._redact_rects = list(bboxes or [])
        self.update()

    def set_annotation_selection(self, bbox):
        self._annotation_rect = tuple(bbox) if bbox else None
        self.update()

    # ----------------------------------------------------------------- paint
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), self.palette().window())
        page_w = self._page_rect.width * self._scale
        page_h = self._page_rect.height * self._scale
        page_rect = QRectF(PAGE_MARGIN, PAGE_MARGIN, page_w, page_h)
        # shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawRoundedRect(page_rect.translated(2, 3), 3, 3)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRect(page_rect)
        if self._pixmap is not None:
            dpr = self._pixmap.devicePixelRatio() or 1.0
            painter.drawPixmap(
                QRect(int(PAGE_MARGIN), int(PAGE_MARGIN),
                      int(round(self._pixmap.width() / dpr)),
                      int(round(self._pixmap.height() / dpr))),
                self._pixmap,
            )
        # search hits
        for bbox in self._search_rects:
            poly = self.pdf_to_widget(bbox)
            painter.setPen(QPen(QColor("#F59E0B"), 2))
            painter.setBrush(QColor(245, 158, 11, 55))
            painter.drawPolygon(poly)
        # selected text
        for bbox in self._selection_rects:
            poly = self.pdf_to_widget(bbox)
            painter.setPen(QPen(QColor("#2563EB"), 2))
            painter.setBrush(QColor(37, 99, 235, 60))
            painter.drawPolygon(poly)
        # areas marked for removal: drawn the way they will be written
        for bbox in self._redact_rects:
            poly = self.pdf_to_widget(bbox)
            painter.setPen(QPen(QColor("#DC2626"), 2))
            painter.setBrush(QColor(0, 0, 0, 210))
            painter.drawPolygon(poly)
        # the selected comment: outlined, never filled, so it stays readable
        if self._annotation_rect is not None:
            poly = self.pdf_to_widget(self._annotation_rect)
            painter.setPen(QPen(QColor("#7C3AED"), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(poly)
        # drag rectangle
        if self._drag_rect is not None:
            painter.setPen(QPen(QColor("#2563EB"), 1, Qt.DashLine))
            painter.setBrush(QColor(37, 99, 235, 30))
            painter.drawRect(self._drag_rect)
        painter.end()


class PDFViewer(QWidget):
    """A document tab: navigation bar, page canvas and inline text editor."""

    page_changed = Signal(int)
    text_selected = Signal(object)
    image_selected = Signal(object)
    zoom_changed = Signal(int)
    add_text_committed = Signal(object)
    edit_text_committed = Signal(object)
    search_navigate = Signal(int)  # direction -1/+1
    redaction_marked = Signal(int)  # how many areas are marked in total
    #: (kind, page, payload) — payload is a list of PDF rects, or a point for
    #: a note.  The viewer only reports what was drawn; the window writes it.
    comment_drawn = Signal(str, int, object)
    comment_selected = Signal(object)  # the annotation under the click, or None
    #: (kind, page, rect) — a form field the user drew; the window names it.
    field_drawn = Signal(str, int, object)

    def __init__(self, document, text_editor, page_manager, image_editor, parent=None):
        super().__init__(parent)
        self.document = document
        self.text_editor = text_editor or (TextEditor(document) if document else None)
        self.page_manager = page_manager
        self.image_editor = image_editor

        self.current_page = 1
        self.zoom_level = 100
        self.min_zoom = 10
        self.max_zoom = 800
        self.display_mode = "single"

        self._mode = MODE_SELECT
        self._panning = False
        self._pan_start = QPoint()
        self._selecting = False
        self._select_start: Optional[QPointF] = None
        self._select_end: Optional[QPointF] = None
        self._selected_run = None
        self._selected_runs: List[object] = []
        self._pixmap_cache = {}
        self.inline_editor: Optional[TextEditOverlay] = None
        #: Areas the user marked for removal, as {1-based page: [pdf bbox]}.
        #: Nothing is written until the window applies them.
        self.pending_redactions: dict = {}
        #: The kind of comment the next drag or click creates, or None.
        self.comment_kind: Optional[str] = None
        #: The kind of form field the next drag creates, or None.
        self.field_kind: Optional[str] = None
        #: The annotation the user last clicked on, as the engine describes it.
        self.selected_annotation: Optional[dict] = None

        self._setup_ui()
        self.retranslate_ui()
        if self.document and self.document.page_count:
            self.render_page(1)
        else:
            self._show_empty_state()

    # ------------------------------------------------------------------- UI
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("viewerBar")
        bar.setFixedHeight(44)
        bar.setStyleSheet("""
            QFrame#viewerBar { background-color: #1E293B; border-bottom: 1px solid #334155; }
            QFrame#viewerBar QToolButton {
                background-color: #334155; color: #F8FAFC; border: 1px solid #475569;
                border-radius: 5px; padding: 3px 9px; min-height: 26px;
            }
            QFrame#viewerBar QToolButton:hover { background-color: #475569; }
            QFrame#viewerBar QLabel { color: #CBD5E1; font-size: 12px; }
            QFrame#viewerBar QSpinBox {
                background-color: #0F172A; color: #F8FAFC; border: 1px solid #475569;
                border-radius: 5px; min-height: 24px; padding: 1px 4px;
            }
        """)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(10, 0, 10, 0)
        bar_layout.setSpacing(6)

        self.prev_btn = QToolButton()
        self.prev_btn.setText("‹")
        self.prev_btn.clicked.connect(self.previous_page)
        self.next_btn = QToolButton()
        self.next_btn.setText("›")
        self.next_btn.clicked.connect(self.next_page)
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setFixedWidth(64)
        self.page_spin.valueChanged.connect(self.set_page)
        self.total_label = QLabel("/ 1")
        bar_layout.addWidget(self.prev_btn)
        bar_layout.addWidget(self.page_spin)
        bar_layout.addWidget(self.total_label)
        bar_layout.addWidget(self.next_btn)
        bar_layout.addSpacing(12)
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("−")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_label_btn = QToolButton()
        self.zoom_label_btn.setText("100%")
        self.zoom_label_btn.clicked.connect(self.actual_size)
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.fit_btn = QToolButton()
        self.fit_btn.clicked.connect(self.fit_page)
        self.fit_width_btn = QToolButton()
        self.fit_width_btn.clicked.connect(self.fit_width)
        bar_layout.addWidget(self.zoom_out_btn)
        bar_layout.addWidget(self.zoom_label_btn)
        bar_layout.addWidget(self.zoom_in_btn)
        bar_layout.addWidget(self.fit_btn)
        bar_layout.addWidget(self.fit_width_btn)
        bar_layout.addStretch()
        self.mode_label = QLabel("")
        self.mode_label.setStyleSheet("color: #F59E0B; font-size: 11px;")
        bar_layout.addWidget(self.mode_label)
        layout.addWidget(bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #0F172A; border: none; }")
        self.canvas = PageCanvas(self)
        self.canvas.installEventFilter(self)
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.viewport().installEventFilter(self)
        layout.addWidget(self.scroll_area, 1)

    def _show_empty_state(self):
        self.canvas.set_page(None, fitz.Rect(0, 0, 400, 300), 0, 1.0)
        self.canvas.update()
        self.page_spin.setRange(1, 1)
        self.total_label.setText("/ 0")

    # ------------------------------------------------------------- translation
    def retranslate_ui(self):
        tr = get_translator().tr
        self.prev_btn.setToolTip(tr("Previous Page"))
        self.next_btn.setToolTip(tr("Next Page"))
        self.zoom_in_btn.setToolTip(tr("Zoom In"))
        self.zoom_out_btn.setToolTip(tr("Zoom Out"))
        self.fit_btn.setText(tr("Fit Page"))
        self.fit_width_btn.setText(tr("Fit Width"))
        self.zoom_label_btn.setToolTip(tr("Actual Size"))
        self.zoom_label_btn.setText(f"{self.zoom_level}%")
        self.page_spin.setToolTip(tr("Go to Page"))
        self.mode_label.setText(self._mode_text())
        if self.inline_editor is not None:
            self.inline_editor.retranslate()

    def _mode_text(self) -> str:
        tr = get_translator().tr
        if self._mode == MODE_EDIT_TEXT:
            return tr("Text editing mode: click a text line to edit")
        if self._mode == MODE_ADD_TEXT:
            return tr("Add text mode: click on the page to place text")
        if self._mode == MODE_REDACT:
            return tr("Hiding mode: drag over what should be removed")
        if self._mode == MODE_COMMENT:
            if self.comment_kind == "note":
                return tr("Comment mode: click where the note belongs")
            return tr("Comment mode: drag over the part you mean")
        if self._mode == MODE_FIELD:
            return tr("Field mode: drag where the field belongs")
        return ""

    # ---------------------------------------------------------------- rendering
    def _logical_scale(self) -> float:
        return (self.zoom_level / 100.0) * (VIEW_DPI / 72.0)

    def render_page(self, page_number: int):
        if not self.document or not self.document.doc:
            self._show_empty_state()
            return
        page_number = max(1, min(int(page_number), self.document.page_count))
        page = self.document.get_page(page_number)
        if page is None:
            return
        try:
            dpr = self.devicePixelRatioF() or 1.0
            scale = self._logical_scale()
            physical = scale * dpr
            pix = page.get_pixmap(matrix=fitz.Matrix(physical, physical), alpha=False)
            img = QImage.fromData(pix.tobytes("png"))
            pixmap = QPixmap.fromImage(img)
            pixmap.setDevicePixelRatio(dpr)
            self.current_page = page_number
            self.canvas.set_page(pixmap, page.rect, page.rotation, scale)
            self._pixmap_cache = {page_number: pixmap}
            self.page_spin.blockSignals(True)
            self.page_spin.setRange(1, self.document.page_count)
            self.page_spin.setValue(page_number)
            self.page_spin.blockSignals(False)
            self.total_label.setText(f"/ {self.document.page_count}")
            self.zoom_label_btn.setText(f"{self.zoom_level}%")
            self.canvas.set_selection([])
            self.canvas.clear_search()
            self._show_pending_redactions()
            self.page_changed.emit(page_number)
        except Exception:
            logger.exception("Failed to render page %d", page_number)
            self._show_empty_state()

    def refresh_current_page(self, keep_selection: bool = False):
        selected_bboxes = [r.bbox for r in self._selected_runs] if keep_selection else []
        self.render_page(self.current_page)
        if keep_selection:
            self.canvas.set_selection(selected_bboxes)

    # ------------------------------------------------------------------ zoom
    def _set_zoom(self, value: int, anchor: Optional[QPoint] = None):
        value = max(self.min_zoom, min(self.max_zoom, int(value)))
        if value == self.zoom_level:
            return
        vbar = self.scroll_area.verticalScrollBar()
        hbar = self.scroll_area.horizontalScrollBar()
        old_v = vbar.value() / max(1, vbar.maximum()) if vbar.maximum() else 0.5
        old_h = hbar.value() / max(1, hbar.maximum()) if hbar.maximum() else 0.5
        self.zoom_level = value
        self.close_inline_editor()
        self.render_page(self.current_page)
        if vbar.maximum():
            vbar.setValue(int(old_v * vbar.maximum()))
        if hbar.maximum():
            hbar.setValue(int(old_h * hbar.maximum()))
        self.zoom_changed.emit(self.zoom_level)
        self.zoom_label_btn.setText(f"{self.zoom_level}%")

    def zoom_in(self):
        self._set_zoom(self.zoom_level + 25)

    def zoom_out(self):
        self._set_zoom(self.zoom_level - 25)

    def set_zoom_percent(self, value):
        self._set_zoom(int(value))

    def actual_size(self):
        self._set_zoom(100)

    def _fit_scale(self) -> float:
        if not self.document:
            return 1.0
        page = self.document.get_page(self.current_page)
        if page is None:
            return 1.0
        vp = self.scroll_area.viewport().size()
        avail_w = max(50, vp.width() - PAGE_MARGIN * 2 - 8)
        avail_h = max(50, vp.height() - PAGE_MARGIN * 2 - 8)
        rect = page.rect
        return min(avail_w / max(1.0, rect.width), avail_h / max(1.0, rect.height))

    def fit_page(self):
        if not self.document:
            return
        scale = self._fit_scale()
        self._set_zoom(int(round(scale * 72.0 / VIEW_DPI * 100.0)))

    def fit_width(self):
        if not self.document:
            return
        page = self.document.get_page(self.current_page)
        if page is None:
            return
        vp = self.scroll_area.viewport().width()
        avail_w = max(50, vp - PAGE_MARGIN * 2 - 8)
        scale = avail_w / max(1.0, page.rect.width)
        self._set_zoom(int(round(scale * 72.0 / VIEW_DPI * 100.0)))

    # -------------------------------------------------------------- navigation
    def set_page(self, page_number: int):
        if not self.document:
            return
        page_number = max(1, min(int(page_number), self.document.page_count))
        if page_number != self.current_page or self.canvas._pixmap is None:
            self.close_inline_editor()
            self.render_page(page_number)

    def next_page(self):
        if self.document and self.current_page < self.document.page_count:
            self.set_page(self.current_page + 1)

    def previous_page(self):
        if self.document and self.current_page > 1:
            self.set_page(self.current_page - 1)

    # ------------------------------------------------------------------ modes
    def set_mode(self, mode: str):
        self._mode = mode
        if mode == MODE_SELECT:
            self.setCursor(QCursor(Qt.ArrowCursor))
        elif mode == MODE_EDIT_TEXT:
            self.setCursor(QCursor(Qt.IBeamCursor))
        elif mode in (MODE_ADD_TEXT, MODE_REDACT, MODE_COMMENT, MODE_FIELD):
            self.setCursor(QCursor(Qt.CrossCursor))
        self.mode_label.setText(self._mode_text())
        if mode == MODE_SELECT and self.inline_editor is not None:
            self.close_inline_editor()

    def set_editing_mode(self, enabled: bool):
        self.set_mode(MODE_EDIT_TEXT if enabled else MODE_SELECT)

    def set_add_text_mode(self, enabled: bool):
        self.set_mode(MODE_ADD_TEXT if enabled else MODE_SELECT)

    def current_mode(self) -> str:
        return self._mode

    def clear_modes(self):
        self.comment_kind = None
        self.field_kind = None
        self.set_mode(MODE_SELECT)

    def set_field_mode(self, kind: Optional[str]):
        """Draw the next form field of *kind*, or leave the mode with None."""
        self.field_kind = kind
        self.set_mode(MODE_FIELD if kind else MODE_SELECT)
        self.mode_label.setText(self._mode_text())

    # ------------------------------------------------------------- redaction
    def set_redact_mode(self, enabled: bool):
        """Turn area marking on or off.  Turning it off keeps the marks."""
        self.set_mode(MODE_REDACT if enabled else MODE_SELECT)

    def mark_redaction(self, page_number: int, bbox) -> int:
        """Mark one area on *page_number* (1-based).  Returns the total."""
        rect = tuple(float(v) for v in fitz.Rect(bbox))
        self.pending_redactions.setdefault(int(page_number), []).append(rect)
        self._show_pending_redactions()
        total = self.pending_redaction_count()
        self.redaction_marked.emit(total)
        return total

    def pending_redaction_count(self) -> int:
        return sum(len(v) for v in self.pending_redactions.values())

    def clear_pending_redactions(self):
        self.pending_redactions = {}
        self.canvas.set_redact_rects([])
        self.redaction_marked.emit(0)

    # ---------------------------------------------------------- commenting
    def set_comment_mode(self, kind: Optional[str]):
        """Draw the next comment of *kind*, or leave comment mode with None."""
        self.comment_kind = kind
        self.set_mode(MODE_COMMENT if kind else MODE_SELECT)
        self.mode_label.setText(self._mode_text())

    def select_annotation_at(self, x: float, y: float):
        """Select the comment under a page point, if there is one."""
        from src.engine.annotations import find_at

        page = self.document.get_page(self.current_page) if self.document else None
        found = find_at(page, x, y) if page is not None else None
        self.selected_annotation = found
        self.canvas.set_annotation_selection(found["rect"] if found else None)
        self.comment_selected.emit(found)
        return found

    def clear_annotation_selection(self):
        self.selected_annotation = None
        self.canvas.set_annotation_selection(None)
        self.comment_selected.emit(None)

    def _show_pending_redactions(self):
        self.canvas.set_redact_rects(
            self.pending_redactions.get(self.current_page, []))

    # ------------------------------------------------------------- selection
    def get_selected_run(self):
        return self._selected_run

    def get_selected_runs(self):
        return list(self._selected_runs)

    def _select_run(self, run, emit: bool = True):
        self._selected_run = run
        self._selected_runs = [run] if run is not None else []
        self.canvas.set_selection([run.bbox] if run else [])
        if emit and run is not None:
            self.text_selected.emit(run)

    def select_run_by_bbox(self, page: int, bbox):
        if page != self.current_page:
            self.set_page(page)
        runs = self.document.get_text_runs_for_page(page) if self.document else []
        for run in runs:
            if run.bbox == tuple(bbox) or run.contains(
                (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            ):
                self._select_run(run)
                return run
        return None

    # ------------------------------------------------------------- mouse events
    def eventFilter(self, obj, event):
        if obj is getattr(self, "canvas", None):
            etype = event.type()
            if etype == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._on_canvas_press(event)
                return True
            if etype == QEvent.MouseMove:
                self._on_canvas_move(event)
                return True
            if etype == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._on_canvas_release(event)
                return True
            if etype == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
                self._panning = True
                self._pan_start = event.pos()
                self.canvas.setCursor(QCursor(Qt.ClosedHandCursor))
                return True
            if etype == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
                self._panning = False
                self.canvas.setCursor(QCursor(Qt.ArrowCursor))
                return True
            if etype == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self._begin_edit_at(event.pos())
                return True
        if obj is self.scroll_area.viewport() and event.type() == QEvent.Resize:
            if self._fit_on_resize:
                self.fit_page()
        return super().eventFilter(obj, event)

    _fit_on_resize = False

    def _on_canvas_press(self, event: QMouseEvent):
        if self.document is None:
            return
        self.canvas.setFocus()
        pos = event.position()
        if self._mode == MODE_ADD_TEXT:
            point = self.canvas.widget_to_pdf(pos)
            if point is not None:
                self._open_add_overlay(point, pos)
            return
        if self._mode == MODE_EDIT_TEXT:
            self._begin_edit_at(pos)
            return
        if self._mode == MODE_COMMENT and self.comment_kind == "note":
            point = self.canvas.widget_to_pdf(pos)
            if point is not None:
                self.comment_drawn.emit("note", self.current_page,
                                        (point.x, point.y))
            return
        self._selecting = True
        self._select_start = pos
        self._select_end = pos
        if self._mode in (MODE_REDACT, MODE_COMMENT, MODE_FIELD):
            return
        point = self.canvas.widget_to_pdf(pos)
        if point is not None:
            if self.select_annotation_at(point.x, point.y) is not None:
                self._selecting = False
                return
            run = self.text_editor.select_text_at_position(self.current_page, point.x, point.y)
            if run is not None:
                self._select_run(run)
            else:
                self._select_run(None)
                self.canvas.set_selection([])

    def _on_canvas_move(self, event: QMouseEvent):
        pos = event.position()
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.scroll_area.horizontalScrollBar().setValue(
                self.scroll_area.horizontalScrollBar().value() - delta.x()
            )
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().value() - delta.y()
            )
            return
        if self._selecting and self._select_start is not None:
            self._select_end = pos
            self.canvas._drag_rect = QRectF(self._select_start, pos).normalized()
            if self._mode in (MODE_REDACT, MODE_COMMENT, MODE_FIELD):
                self.canvas.update()
                return
            start_pdf = self.canvas.widget_to_pdf(self._select_start)
            end_pdf = self.canvas.widget_to_pdf(pos)
            if start_pdf and end_pdf:
                rect = fitz.Rect(
                    min(start_pdf.x, end_pdf.x), min(start_pdf.y, end_pdf.y),
                    max(start_pdf.x, end_pdf.x), max(start_pdf.y, end_pdf.y),
                )
                runs = [
                    r for r in self.document.get_text_runs_for_page(self.current_page)
                    if fitz.Rect(r.bbox).intersects(rect)
                ]
                self.canvas._selection_rects = [r.bbox for r in runs]
            self.canvas.update()
            return
        # cursor feedback over text
        if self._mode == MODE_SELECT:
            point = self.canvas.widget_to_pdf(pos)
            if point is not None and self.text_editor is not None:
                run = self.text_editor.select_text_at_position(self.current_page, point.x, point.y)
                self.canvas.setCursor(QCursor(Qt.IBeamCursor if run else Qt.ArrowCursor))

    def _on_canvas_release(self, event: QMouseEvent):
        if not self._selecting:
            return
        self._selecting = False
        start = self._select_start
        end = self._select_end
        self.canvas._drag_rect = None
        self._select_start = self._select_end = None
        if start is None or end is None or self.document is None:
            return
        start_pdf = self.canvas.widget_to_pdf(start)
        end_pdf = self.canvas.widget_to_pdf(end)
        if start_pdf is None or end_pdf is None:
            return
        rect = fitz.Rect(
            min(start_pdf.x, end_pdf.x), min(start_pdf.y, end_pdf.y),
            max(start_pdf.x, end_pdf.x), max(start_pdf.y, end_pdf.y),
        )
        if rect.width < 2 and rect.height < 2:
            return
        if self._mode == MODE_REDACT:
            self.mark_redaction(self.current_page, rect)
            return
        if self._mode == MODE_COMMENT:
            self._emit_drawn_comment(rect)
            return
        if self._mode == MODE_FIELD:
            if self.field_kind:
                self.field_drawn.emit(self.field_kind, self.current_page,
                                      (rect.x0, rect.y0, rect.x1, rect.y1))
            return
        runs = [
            r for r in self.document.get_text_runs_for_page(self.current_page)
            if fitz.Rect(r.bbox).intersects(rect)
        ]
        self._selected_runs = runs
        self._selected_run = runs[0] if runs else None
        self.canvas.set_selection([r.bbox for r in runs])
        if runs:
            self.text_selected.emit(runs[0])
        else:
            self.canvas.set_selection([])

    def _emit_drawn_comment(self, rect):
        """Report the drawn area as the payload the comment kind needs.

        A highlight follows the text it was dragged over, so the lines that
        the drag touches are used when there are any; without text under the
        drag the drawn rectangle itself is used, and nothing is invented.
        """
        kind = self.comment_kind
        if not kind:
            return
        payload = [(rect.x0, rect.y0, rect.x1, rect.y1)]
        if kind == "highlight" and self.document is not None:
            runs = [r for r in self.document.get_text_runs_for_page(self.current_page)
                    if fitz.Rect(r.bbox).intersects(rect)]
            if runs:
                payload = [tuple(fitz.Rect(run.bbox) & rect) for run in runs
                           if (fitz.Rect(run.bbox) & rect).get_area() > 0]
        self.comment_drawn.emit(kind, self.current_page, payload)

    # --------------------------------------------------------------- overlays
    def _overlay_parent_rect(self) -> QRect:
        return self.canvas.rect()

    def _open_add_overlay(self, point, widget_pos: QPointF):
        self._ensure_overlay()
        self.inline_editor.configure_add(self.current_page, point.x, point.y)
        self._place_overlay(widget_pos)
        self.inline_editor.show()
        self.inline_editor.raise_()
        self.inline_editor.text_edit.setFocus()

    def _begin_edit_at(self, widget_pos: QPointF):
        if self.document is None or self.text_editor is None:
            return
        point = self.canvas.widget_to_pdf(widget_pos)
        if point is None:
            return
        run = self.text_editor.select_text_at_position(self.current_page, point.x, point.y)
        if run is None:
            return
        supported, reason = self.text_editor.can_edit_run(run)
        self._select_run(run)
        if not supported:
            self.edit_text_committed.emit({
                "unsupported": True, "reason": reason, "run": run
            })
            return
        self._ensure_overlay()
        self.inline_editor.configure_edit(self.current_page, run)
        self._place_overlay(widget_pos)
        self.inline_editor.show()
        self.inline_editor.raise_()
        self.inline_editor.text_edit.setFocus()

    def _ensure_overlay(self):
        if self.inline_editor is None:
            self.inline_editor = TextEditOverlay(self.canvas)
            self.inline_editor.committed.connect(self._on_overlay_committed)
            self.inline_editor.cancelled.connect(self._on_overlay_cancelled)

    def _place_overlay(self, widget_pos: QPointF):
        editor = self.inline_editor
        editor.adjustSize()
        w = editor.width()
        h = editor.sizeHint().height()
        x = int(widget_pos.x()) + 12
        y = int(widget_pos.y()) + 12
        max_x = self.canvas.width() - w - 8
        max_y = self.canvas.height() - h - 8
        if x > max_x:
            x = max(8, int(widget_pos.x()) - w - 12)
        if y > max_y:
            y = max(8, self.canvas.height() - h - 8)
        editor.move(max(8, x), max(8, y))
        editor.setFixedHeight(max(200, min(300, h)))

    def _on_overlay_committed(self, payload: dict):
        if payload.get("mode") == "edit":
            run = payload.get("run")
            payload["run_id"] = run.run_id if run is not None else None
            payload["old_text"] = run.text if run is not None else ""
            self.inline_editor.hide()
            self.edit_text_committed.emit(payload)
        else:
            self.inline_editor.hide()
            self.add_text_committed.emit(payload)

    def _on_overlay_cancelled(self):
        self.clear_modes()

    def close_inline_editor(self, success: bool = False):
        if self.inline_editor is not None:
            self.inline_editor.hide()
        if success:
            self.set_mode(MODE_SELECT)

    # ---------------------------------------------------------------- search
    def show_search_hits(self, hits: List[tuple], active_index: int = 0):
        """hits: list of (page_number, bbox)."""
        self._search_hits = list(hits)
        self._active_hit = active_index
        if not hits:
            self.canvas.clear_search()
            return
        page, bbox = hits[active_index]
        if page != self.current_page:
            self.set_page(page)
        rects = [b for (p, b) in hits if p == self.current_page]
        self.canvas.set_search_rects(rects)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.close_inline_editor()
            self.clear_modes()
            self.canvas.set_selection([])
            self.clear_annotation_selection()
            return
        if event.key() in (Qt.Key_PageDown, Qt.Key_Down) and event.modifiers() & Qt.ControlModifier:
            self.next_page()
            return
        if event.key() in (Qt.Key_PageUp, Qt.Key_Up) and event.modifiers() & Qt.ControlModifier:
            self.previous_page()
            return
        super().keyPressEvent(event)
