#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextPDF Pro v1.0.2 - Main Window (Professional Redesign)
واجهة احترافية مع شريط قوائم، شريط أدوات منظم، عارض PDF، لوحات جانبية، وشريط حالة.
"""

import os
import sys
import logging
from dataclasses import dataclass
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QStatusBar, QLabel, QProgressBar,
    QTabWidget, QMenuBar, QMenu, QApplication,
    QDockWidget, QFrame, QScrollArea, QSizePolicy,
    QPushButton, QButtonGroup, QStackedWidget, QToolBar, QSlider
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QLocale, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QKeySequence, QAction, QFont, QColor, QPixmap, QLinearGradient

# Package-style imports
from src.config import (settings, APP_NAME, APP_VERSION, APP_ORGANIZATION, APP_DESCRIPTION,
                        BUILD_ID, get_translator, resource_path, MIN_ZOOM, MAX_ZOOM)
from src.models.document import PDFDocument
from src.engine.text_editor import TextEditor
from src.engine.page_manager import PageManager
from src.engine.image_editor import ImageEditor
from src.engine.ocr_engine import OCREngine
from src.commands.command import CommandStack, PDFSnapshotCommand
from src.ui.theme_manager import get_theme_manager
from src.ui.components import (
    ModernButton, ModernIconButton, Card, RibbonGroup,
    EmptyState, PropertiesPanel, ThumbnailPanel, ThumbnailItem
)
from src.ui.pdf_viewer import (PDFViewer, MODE_REDACT, MODE_COMMENT,
                               MODE_FIELD, MODE_STAMP)
from src.ui.ribbon import Ribbon

logger = logging.getLogger("NextPDF")


def tr(key):
    """Translate a UI key with the shared translator (current language)."""
    return get_translator().tr(key)



@dataclass
class DocumentContext:
    document: PDFDocument
    viewer: PDFViewer
    text_editor: TextEditor
    page_manager: PageManager
    image_editor: ImageEditor
    command_stack: CommandStack
    file_path: str


class MainWindow(QMainWindow):
    """النافذة الرئيسية لـ NextPDF Pro v1.0.2 - واجهة احترافية."""

    def __init__(self):
        super().__init__()

        self._contexts = []
        self.current_context = None

        # حالة التطبيق
        self.current_document: Optional[PDFDocument] = None
        self.text_editor: Optional[TextEditor] = None
        self.page_manager: Optional[PageManager] = None
        self.image_editor: Optional[ImageEditor] = None
        self.ocr_engine: Optional[OCREngine] = None
        self.command_stack: Optional[CommandStack] = None

        # مكونات واجهة المستخدم
        self.theme_manager: Optional[ThemeManager] = None
        self.main_toolbar: Optional[QToolBar] = None
        self.thumbnail_panel: Optional[ThumbnailPanel] = None
        self.properties_panel: Optional[PropertiesPanel] = None
        self.pdf_viewer: Optional[PDFViewer] = None
        self.tab_widget: Optional[QTabWidget] = None
        self.status_bar: Optional[QStatusBar] = None
        self.empty_state: Optional[EmptyState] = None

        # تتبع العنصر المحدد
        self._selected_element = None
        self._selected_element_type = None

        self._setup_theme()
        self._setup_status_bar()
        self._setup_ui()
        self._setup_menus()
        self._setup_engines()

        # تعيين أيقونة النافذة
        icon_path = resource_path("resources/icons/NextPDF-Pro.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # استعادة حالة النافذة
        self._restore_window_state()
        self._update_window_title()

        logger.info("MainWindow initialized (professional theme)")

    def _setup_theme(self):
        """تهيئة مدير الثيم."""
        app = QApplication.instance()
        self.theme_manager = get_theme_manager(app)
        lang = settings.get("language", "ar")
        self.theme_manager.set_language(lang)
        self.theme_manager.set_theme(settings.get("theme", "light"))
        self.theme_manager.apply_theme()

    def _setup_ui(self):
        """إعداد تخطيط واجهة المستخدم."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1050, 680)
        self.resize(1400, 900)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        self._main_layout = main_layout
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === الشريط العلوي (Main Toolbar/Ribbon) ===
        self.ribbon = self._create_main_toolbar()
        main_layout.addWidget(self.ribbon)

        # === قسم المحتوى الرئيسي (Splitter) ===
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # اللوحة اليسرى - الصور المصغرة
        self.thumbnail_panel = ThumbnailPanel()
        self.thumbnail_panel.setMinimumWidth(200)
        self.thumbnail_panel.setMaximumWidth(320)
        self.splitter.addWidget(self.thumbnail_panel)

        # الوسط - عارض PDF مع تبويبات
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.setObjectName("pdfTabWidget")
        self.splitter.addWidget(self.tab_widget)

        # اللوحة اليمنى - الخصائص
        self.properties_panel = PropertiesPanel()
        self.properties_panel.setMinimumWidth(280)
        self.properties_panel.setMaximumWidth(400)
        self.splitter.addWidget(self.properties_panel)

        # إعداد نسب المقسم
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([240, 800, 300])

        main_layout.addWidget(self.splitter)

        # عرض الحالة الفارغة في البداية
        self._show_empty_state()

    def _create_main_toolbar(self):
        ribbon = Ribbon()
        ribbon.set_icon_color(self._ribbon_icon_color())
        ribbon.add_page("home", "Home", groups=[
            ("File", [
                ("New", self._new_document, "file_new", False),
                ("Open", self._open_file, "file_open", False),
                ("Save", self._save_file, "file_save", True),
                ("Save As", self._save_as_file, "file_save_as", True)]),
            ("Document", [
                ("Print", self._print_document, "file_print", True),
                ("Properties", self._show_properties, "properties", True)])])
        ribbon.add_page("edit", "Edit PDF", groups=[
            ("History", [
                ("Undo", self._undo, "edit_undo", True),
                ("Redo", self._redo, "edit_redo", True)]),
            ("Text", [
                ("Edit Text", self._edit_text_mode, "edit_text", True),
                ("Add Text", self._add_text_mode, "text_add", True),
                ("Delete Selected Text", self._delete_selected_text, "text_delete", True)])])
        ribbon.add_page("insert", "Insert", groups=[
            ("Content", [("Insert Image", self._insert_image, "image_insert", True)]),
            ("Pages", [("Insert Page", self._insert_page, "page_insert", True)])])
        ribbon.add_page("pages", "Organize Pages", groups=[
            ("Pages", [
                ("Insert Page", self._insert_page, "page_insert", True),
                ("Delete Page", self._delete_page, "page_delete", True),
                ("Rotate", self._rotate_page, "page_rotate", True)])])
        formats = ("PNG", "JPEG", "TIFF", "WEBP", "TXT", "HTML", "Markdown", "SVG", "JSON")
        extensions = ("png", "jpg", "tiff", "webp", "txt", "html", "md", "svg", "json")
        convert_tools = [(label, lambda checked=False, fmt=extension: self._run_conversion(fmt), "convert", True)
                         for label, extension in zip(formats, extensions)]
        office_tools = [
            ("Word page images", lambda: self._run_conversion("docx"), "convert_word", True),
            ("Editable Word", lambda: self._run_conversion("docx_editable"), "convert_word", True),
            ("Excel grid tables", lambda: self._run_conversion("xlsx"), "convert_excel", True),
            ("PowerPoint page images", lambda: self._run_conversion("pptx"), "convert_powerpoint", True),
            ("Editable slides", lambda: self._run_conversion("pptx_editable"), "convert_powerpoint", True),
            ("CSV grid tables", lambda: self._run_conversion("csv"), "convert_csv", True)]
        ribbon.add_page("convert", "Convert PDF", groups=[
            ("Images and text", convert_tools),
            ("Office", office_tools),
            ("Size", [("Reduce the file size", self._compress_document,
                       "compress", True)])])
        ribbon.add_page("create", "Create PDF", groups=[
            ("From files", [("Create from files", lambda: self._create_pdf("all"), "create_pdf", False)]),
            ("Images and text", [
                ("Images to PDF", lambda: self._create_pdf("images"), "create_images", False),
                ("Text to PDF", lambda: self._create_pdf("text"), "create_text", False)])])
        ribbon.add_page("ocr", "OCR", groups=[
            ("Recognition", [("OCR", self._run_ocr, "ocr_scan", True)])])
        ribbon.add_page("forms", "Forms", groups=[
            ("Fill", [
                ("Fill the form", self._fill_form, "form_fill", True),
                ("Flatten the form", self._flatten_form, "form_flatten", True)]),
            ("Build", [
                ("Add a text field", lambda: self._field_mode("text"),
                 "field_text", True),
                ("Add a tick box", lambda: self._field_mode("checkbox"),
                 "field_checkbox", True),
                ("Add a list of choices", lambda: self._field_mode("dropdown"),
                 "field_dropdown", True),
                ("Remove a field", self._remove_form_field, "field_delete",
                 True)])])
        ribbon.add_page("review", "Review", groups=[
            ("Comments", [
                ("Highlight", lambda: self._comment_mode("highlight"),
                 "comment_highlight", True),
                ("Sticky note", lambda: self._comment_mode("note"),
                 "comment_note", True),
                ("Text on the page", lambda: self._comment_mode("free_text"),
                 "comment_text", True)]),
            ("Shapes", [
                ("Rectangle", lambda: self._comment_mode("rectangle"),
                 "shape_rectangle", True),
                ("Ellipse", lambda: self._comment_mode("ellipse"),
                 "shape_ellipse", True),
                ("Line", lambda: self._comment_mode("line"),
                 "shape_line", True)]),
            ("Manage", [
                ("Edit the comment", self._edit_selected_comment,
                 "comment_edit", True),
                ("Delete the comment", self._delete_selected_comment,
                 "comment_delete", True),
                ("List the comments", self._list_comments,
                 "comment_list", True)])])
        ribbon.add_page("protect", "Protect and Sign", groups=[
            ("Security", [
                ("Protect with a password", self._protect_document, "protect", True),
                ("Remove protection", self._remove_protection, "protect_remove", True),
                ("Remove document information", self._strip_document_information,
                 "metadata_clean", True),
                ("Redact text", self._redact_text, "redact", True),
                ("Hide an area", self._mark_redaction_area, "redact_area", True),
                ("Apply the hidden areas", self._apply_marked_redactions,
                 "redact_apply", True)]),
            ("Visible stamp", [
                ("Stamp an image", lambda: self._stamp_mode("image"),
                 "stamp_image", True),
                ("Stamp a name", lambda: self._stamp_mode("text"),
                 "stamp_text", True),
                ("What a stamp is not", self._explain_stamp,
                 "stamp_about", False)])])
        ribbon.add_page("view", "View", groups=[
            ("Zoom", [
                ("Zoom In", self._zoom_in, "view_zoom_in", True),
                ("Zoom Out", self._zoom_out, "view_zoom_out", True),
                ("Fit Page", self._fit_page, "fit_page", True),
                ("Fit Width", self._fit_width, "fit_width", True)]),
            ("Panels", [
                ("Pages panel", self._toggle_thumbnail_panel, "panel_pages", False),
                ("Properties panel", self._toggle_properties_panel, "panel_properties", False)])])
        ribbon.add_page("settings", "Settings", groups=[
            ("Language", [("Switch language", self._toggle_language, "lang_toggle", False)]),
            ("Appearance", [
                ("Light theme", lambda: self._set_theme("light"), "theme_light", False),
                ("Dark theme", lambda: self._set_theme("dark"), "theme_dark", False),
                ("System theme", lambda: self._set_theme("system"), "theme_system", False)])])
        ribbon.set_document_available(self.current_context is not None)
        return ribbon

    def _ribbon_icon_color(self):
        """Icon tint that keeps contrast in both themes."""
        manager = getattr(self, "theme_manager", None)
        dark = manager.is_dark_mode() if manager is not None else False
        return "#E2E8F0" if dark else "#334155"

    def _setup_menus(self):
        """إعداد شريط القوائم."""
        translator = get_translator()
        menubar = self.menuBar()
        menubar.clear()
        menubar.setObjectName("appMenuBar")
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1E293B;
                color: #F8FAFC;
                border-bottom: 1px solid #334155;
                padding: 4px;
            }
            QMenuBar::item {
                background-color: transparent;
                color: #F8FAFC;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #334155;
                color: #2563EB;
            }
        """)

        # قائمة File
        file_menu = menubar.addMenu(translator.tr('File'))
        file_menu.addAction(translator.tr('New'), self._new_document, QKeySequence.New)
        file_menu.addAction(translator.tr('Open'), self._open_file, QKeySequence.Open)
        file_menu.addAction(translator.tr('Save'), self._save_file, QKeySequence.Save)
        file_menu.addAction(translator.tr('Save As'), self._save_as_file, QKeySequence.SaveAs)
        file_menu.addSeparator()
        file_menu.addAction(translator.tr('Exit'), self.close)

        # قائمة Edit
        edit_menu = menubar.addMenu(translator.tr('Edit'))
        edit_menu.addAction(translator.tr('Undo'), self._undo, QKeySequence.Undo)
        edit_menu.addAction(translator.tr('Redo'), self._redo, QKeySequence.Redo)

        # قائمة View
        view_menu = menubar.addMenu(translator.tr('View'))
        view_menu.addAction(translator.tr('Zoom In'), self._zoom_in)
        view_menu.addAction(translator.tr('Zoom Out'), self._zoom_out)

        # قائمة Tools
        tools_menu = menubar.addMenu(translator.tr('Tools'))
        tools_menu.addAction(translator.tr("OCR"), self._run_ocr)

        # قائمة Help
        help_menu = menubar.addMenu(translator.tr('Help'))
        help_menu.addAction(translator.tr('About'), self._show_about)
        help_menu.addSeparator()
        help_menu.addAction(translator.tr('NextPDF Pro — Terms and Conditions'), self._show_terms)

    def _setup_status_bar(self):
        """إعداد شريط الحالة الحديث."""
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("appStatusBar")
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1E293B;
                color: #94A3B8;
                border-top: 1px solid #334155;
                font-size: 12px;
                padding: 3px 12px;
            }
        """)

        translator = get_translator()

        # معلومات الصفحة
        self.page_label = QLabel(f"{translator.tr('Page')}: 0 / 0")
        self.page_label.setStyleSheet("color: #94A3B8; padding: 2px 12px;")
        self.status_bar.addWidget(self.page_label)

        # فاصل
        sep = QLabel("|")
        sep.setStyleSheet("color: #334155; padding: 0 8px;")
        self.status_bar.addWidget(sep)

        # نسبة التكبير
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #CBD5E1; padding: 2px 8px; font-weight: 600;")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setObjectName("zoomSlider")
        self.zoom_slider.setRange(MIN_ZOOM, MAX_ZOOM)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(160)
        self.zoom_slider.setToolTip(translator.tr("Zoom"))
        self.zoom_slider.setAccessibleName(translator.tr("Zoom"))
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider)
        self.status_bar.addWidget(self.zoom_slider)
        self.status_bar.addWidget(self.zoom_label)

        self.status_bar.addPermanentWidget(sep)

        # حالة المستند
        self.status_label = QLabel(f"{translator.tr('Ready')}")
        self.status_label.setStyleSheet("color: #10B981; padding: 2px 12px;")
        self.status_bar.addPermanentWidget(self.status_label)

        # شريط التقدم (مخفي افتراضياً)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _setup_engines(self):
        """إعداد محركات التحرير."""
        self.command_stack = CommandStack()
        self.ocr_engine = OCREngine(language=settings.get("ocr_language", "ara+eng"))

    def _restore_window_state(self):
        """استعادة هندسة وحالة النافذة من الإعدادات."""
        geometry = settings.get("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = settings.get("window_state")
        if state:
            self.restoreState(state)

    def _save_window_state(self):
        """حفظ هندسة وحالة النافذة في الإعدادات."""
        settings.set("window_geometry", self.saveGeometry())
        settings.set("window_state", self.saveState())

    # === Empty State / Document View ===

    def _show_empty_state(self):
        """عرض الحالة الفارغة عندما لا يوجد مستند مفتوح."""
        # مسح التبويبات
        while self.tab_widget.count():
            self.tab_widget.removeTab(0)

        translator = get_translator()
        self.empty_state = EmptyState()
        self.empty_state.action_clicked.connect(self._open_file)
        self.tab_widget.addTab(self.empty_state, translator.tr('Get Started'))
        self.tab_widget.setCurrentIndex(0)

        self.current_document = None
        self.text_editor = None
        self.page_manager = None
        self.image_editor = None
        self.pdf_viewer = None

        self.page_label.setText(f"{get_translator().tr('Page')}: 0 / 0")
        self.zoom_label.setText("100%")
        self.status_label.setText(f"{get_translator().tr('Ready')}")
        self.thumbnail_panel.clear_thumbnails()

    def _show_document_view(self, document: PDFDocument, file_path: str):
        """عرض طريقة عرض المستند مع عارض PDF."""
        # إزالة Tab الحالة الفارغة إذا كان موجوداً
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, EmptyState):
                self.tab_widget.removeTab(i)
                break

        self.current_document = document
        self.text_editor = TextEditor(document)
        self.page_manager = PageManager(document)
        self.image_editor = ImageEditor(document)

        # إنشاء عارض PDF
        viewer = PDFViewer(document, self.text_editor, self.page_manager, self.image_editor)
        context = DocumentContext(document, viewer, self.text_editor, self.page_manager,
                                  self.image_editor, CommandStack(), file_path)
        self._contexts.append(context)
        viewer.text_selected.connect(self._on_text_selected)
        viewer.image_selected.connect(self._on_image_selected)
        viewer.page_changed.connect(self._on_page_changed)
        viewer.add_text_committed.connect(lambda payload, c=context: self._commit_text(c, payload, False))
        viewer.edit_text_committed.connect(lambda payload, c=context: self._commit_text(c, payload, True))
        viewer.comment_drawn.connect(
            lambda kind, page, payload, c=context:
            self._commit_comment(c, kind, page, payload))
        viewer.field_drawn.connect(
            lambda kind, page, rect, c=context:
            self._commit_field(c, kind, page, rect))
        viewer.stamp_drawn.connect(
            lambda kind, page, rect, c=context:
            self._commit_stamp(c, kind, page, rect))

        tab_index = self.tab_widget.addTab(viewer, os.path.basename(file_path))
        self.tab_widget.setCurrentIndex(tab_index)
        self._on_tab_changed(tab_index)

        # تحديث الصور المصغرة
        self._update_thumbnails()

        # تحديث الحالة
        self.page_label.setText(f"{get_translator().tr('Page')}: 1 / {document.page_count}")
        self.status_label.setText(f"{get_translator().tr('Opened')}: {os.path.basename(file_path)}")

        logger.info(f"Opened document: {file_path}")

    def _commit_text(self, context, payload, editing):
        viewer = context.viewer
        if editing and payload.get("unsupported"):
            viewer.close_inline_editor(False)
            return
        def action():
            options = dict(font_family=payload["font"], font_size=payload["size"],
                           color=payload["color"], direction=payload["direction"],
                           bold=payload["bold"], italic=payload["italic"])
            if editing:
                return context.text_editor.replace_text_run(payload["run_id"], payload["text"], **options)
            return context.text_editor.add_text(payload["page"], payload["x"], payload["y"],
                                                payload["text"], **options)
        command = PDFSnapshotCommand(context.document, "Edit Text" if editing else "Add Text", action)
        context.command_stack.push(command)
        result = command.result
        viewer.close_inline_editor(bool(result and result.success))
        if result and result.success:
            viewer.refresh_current_page()
            if context is self.current_context:
                self._update_thumbnails()
                self._update_window_title()
        else:
            logger.error("Text operation failed: %s", getattr(result, "message", "unknown error"))

    def _on_tab_changed(self, index):
        if self.tab_widget is None:
            return
        widget = self.tab_widget.widget(index) if index >= 0 else None
        context = next ( (item for item in self._contexts if item.viewer is widget), None)
        self.current_context = context
        self.current_document = context.document if context else None
        self.text_editor = context.text_editor if context else None
        self.page_manager = context.page_manager if context else None
        self.image_editor = context.image_editor if context else None
        self.command_stack = context.command_stack if context else None
        if isinstance(self.ribbon, Ribbon):
            self.ribbon.set_document_available(context is not None)
        if context and hasattr(self, "zoom_slider"):
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(context.viewer.zoom_level)
            self.zoom_slider.blockSignals(False)
            self.zoom_label.setText(f"{context.viewer.zoom_level}%")
        self._update_window_title()
        if context and self.thumbnail_panel is not None:
            self._update_thumbnails()

    def _update_window_title(self):
        title = f"{APP_NAME} {APP_VERSION} - {get_translator().tr('Professional PDF Editor')}"
        context = self.current_context
        if context:
            name = os.path.basename(context.file_path or context.document.file_path or "")
            title += f" — {name}"
            if context.document.is_modified:
                title += " *"
        self.setWindowTitle(title)

    def _update_thumbnails(self):
        """تحديث لوحة الصور المصغرة."""
        self.thumbnail_panel.clear_thumbnails()

        if not self.current_document:
            return

        for page_num in range(1, self.current_document.page_count + 1):
            pix = self.current_document.get_page_thumb(page_num, size=(80, 100))
            if pix:
                from PySide6.QtGui import QPixmap, QImage
                img_data = pix.tobytes("png")
                img = QImage.fromData(img_data)
                pixmap = QPixmap.fromImage(img)
                item = self.thumbnail_panel.add_thumbnail(page_num, pixmap)
            else:
                item = self.thumbnail_panel.add_thumbnail(page_num)

            item.page_clicked.connect(self._on_thumbnail_clicked)

    # === File Operations ===

    def _new_document(self):
        """إنشاء مستند PDF فارغ جديد."""
        try:
            import fitz
        except ImportError:
            import fitz

        try:
            doc = fitz.open()
            page = doc.new_page()

            temp_path = os.path.join(os.environ.get("TEMP", "/tmp"), "new_document.pdf")
            doc.save(temp_path)
            doc.close()

            pdf_doc = PDFDocument()
            if pdf_doc.load(temp_path):
                self._show_document_view(pdf_doc, temp_path)
        except Exception as e:
            logger.error(f"Failed to create new document: {e}")
            QMessageBox.critical(self, tr("Error"), f"{tr('Failed to create a new document')}: {e}")

    def _open_file(self):
        """فتح ملف PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Open PDF File"),
            "",
            f"{tr('PDF files')} (*.pdf)"
        )

        if file_path:
            self._open_file_path(file_path)

    def _open_file_path(self, file_path: str):
        """فتح ملف PDF من المسار."""
        try:
            doc = PDFDocument()
            if doc.load(file_path):
                self._show_document_view(doc, file_path)
                return True
            if doc.needs_password:
                return self._open_protected_file(doc, file_path)
            return False
        except Exception as e:
            logger.error(f"Failed to open file {file_path}: {e}")
            QMessageBox.critical(self, tr("Error"), f"{tr('Failed to open the file')}: {e}")
            return False

    PASSWORD_ATTEMPTS = 3

    def _open_protected_file(self, doc, file_path: str) -> bool:
        """Ask for the password of an encrypted file and open it.

        The user gets three tries; cancelling at any point leaves the file
        closed without an error, because cancelling is not a failure.
        """
        from PySide6.QtWidgets import QInputDialog, QLineEdit

        tr = get_translator().tr
        for attempt in range(self.PASSWORD_ATTEMPTS):
            prompt = (tr("Wrong password, try again") if attempt
                      else tr("This file is protected. Enter its password."))
            password, accepted = QInputDialog.getText(
                self, tr("Protected file"), prompt, QLineEdit.Password)
            if not accepted:
                return False
            if doc.load(file_path, password):
                self._show_document_view(doc, file_path)
                return True
        QMessageBox.warning(
            self, tr("Protected file"),
            tr("The file was not opened because the password did not match."))
        return False

    # ------------------------------------------------------------ protection
    def _protected_save(self, **save_kwargs) -> bool:
        """Ask where to write, then save the current document with *kwargs*.

        Protection changes the whole file, so it is always written to a new
        path: the original stays as it is until the user replaces it.
        """
        tr = get_translator().tr
        document = self.current_document
        if document is None:
            return False
        suggested = ""
        if document.file_path:
            base, ext = os.path.splitext(document.file_path)
            suggested = f"{base}-protected{ext or '.pdf'}"
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("Save the protected file as"), suggested,
            f"{tr('PDF files')} (*.pdf)")
        if not file_path:
            return False
        if not document.save(file_path, **save_kwargs):
            QMessageBox.critical(self, tr("Error"),
                                 f"{tr('Failed to save the file')}: "
                                 f"{document.last_error or ''}")
            return False
        self._update_window_title()
        return True

    def _protect_document(self):
        """Encrypt the open document and set its permissions."""
        from src.ui.protect_dialog import ProtectDialog

        tr = get_translator().tr
        if self.current_document is None:
            return
        dialog = ProtectDialog(self, was_protected=self.current_document.is_encrypted)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        if self._protected_save(**dialog.save_arguments()):
            self.status_label.setText(tr("The document is now protected."))

    def _remove_protection(self):
        tr = get_translator().tr
        document = self.current_document
        if document is None:
            return
        if not document.is_encrypted:
            QMessageBox.information(self, tr("Protected file"),
                                    tr("This document is not protected."))
            return
        if self._protected_save(remove_encryption=True):
            self.status_label.setText(tr("The protection was removed."))

    def _strip_document_information(self):
        tr = get_translator().tr
        if self.current_document is None:
            return
        if self._protected_save(strip_metadata=True):
            self.status_label.setText(tr("The document information was removed."))

    def _redact_text(self):
        """Remove every occurrence of a phrase from the open document."""
        from PySide6.QtWidgets import QInputDialog

        tr = get_translator().tr
        document = self.current_document
        if document is None:
            return
        needle, accepted = QInputDialog.getText(
            self, tr("Redact text"),
            f"{tr('Text to redact')}\n{tr('The text will be removed from the file, not covered.')}")
        if not accepted or not needle.strip():
            return
        removed = document.redact_text(needle)
        if not removed:
            QMessageBox.information(self, tr("Redact text"),
                                    tr("Nothing matched that text."))
            return
        self._refresh_current_view()
        self.status_label.setText(f"{tr('Removed areas')}: {removed}")

    def _mark_redaction_area(self):
        """Let the user drag rectangles over what should be removed."""
        tr = get_translator().tr
        viewer = getattr(self.current_context, "viewer", None)
        if viewer is None:
            return
        turning_on = viewer.current_mode() != MODE_REDACT
        viewer.set_redact_mode(turning_on)
        if turning_on:
            self.status_label.setText(
                tr("Drag over what should be removed, then apply."))
        else:
            self.status_label.setText("")

    def _apply_marked_redactions(self):
        """Remove the marked areas from the page content."""
        tr = get_translator().tr
        document = self.current_document
        viewer = getattr(self.current_context, "viewer", None)
        if document is None or viewer is None:
            return
        areas = {page: list(rects)
                 for page, rects in viewer.pending_redactions.items() if rects}
        if not areas:
            QMessageBox.information(self, tr("Hide an area"),
                                    tr("Mark an area on the page first."))
            return
        removed = document.redact_areas(areas)
        if not removed:
            QMessageBox.critical(self, tr("Error"),
                                 f"{tr('Redaction failed')}: "
                                 f"{document.last_error or ''}")
            return
        viewer.clear_pending_redactions()
        viewer.set_redact_mode(False)
        self._refresh_current_view()
        self.status_label.setText(f"{tr('Removed areas')}: {removed}")

    # ---------------------------------------------------------------- forms
    def _fill_form(self):
        """Fill the interactive fields of the open document."""
        from PySide6.QtWidgets import QDialog
        from src.ui.form_dialog import FormDialog

        tr = get_translator().tr
        context = self.current_context
        if context is None:
            return
        document = context.document
        fields = document.form_fields()
        if not fields:
            QMessageBox.information(
                self, tr("Fill the form"),
                tr("This document has no interactive fields."))
            return
        dialog = FormDialog(fields, self)
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.changed_values()
        if not values:
            return
        appearance_warning = []

        def fill():
            filled = 0
            for name, value in values.items():
                result = document.set_field_value(name, value)
                if result["stored"]:
                    filled += 1
                    if not result["appearance_ok"]:
                        appearance_warning.append(name)
            return filled or False

        command = PDFSnapshotCommand(document, "Fill the form", fill)
        context.command_stack.push(command)
        if not command.result:
            QMessageBox.warning(self, tr("Fill the form"),
                                document.last_error or tr("Nothing was filled"))
            return
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()
        self.status_label.setText(f"{tr('Filled fields')}: {command.result}")
        if appearance_warning:
            QMessageBox.information(self, tr("Fill the form"),
                                    FormDialog.arabic_warning())

    def _flatten_form(self):
        """Make the filled values part of the page content."""
        tr = get_translator().tr
        context = self.current_context
        if context is None:
            return
        document = context.document
        if not document.form_fields():
            QMessageBox.information(
                self, tr("Flatten the form"),
                tr("This document has no interactive fields."))
            return
        answer = QMessageBox.question(
            self, tr("Flatten the form"),
            tr("The values become part of the page and the form stops being "
               "fillable. Continue?"))
        if answer != QMessageBox.Yes:
            return
        command = PDFSnapshotCommand(document, "Flatten the form",
                                     document.flatten_form)
        context.command_stack.push(command)
        result = command.result
        if not result:
            QMessageBox.warning(self, tr("Flatten the form"),
                                document.last_error or tr("Nothing was flattened"))
            return
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()
        self.status_label.setText(
            f"{tr('Flattened fields')}: {result['flattened']}")

    def _field_mode(self, kind):
        """Arm the viewer to draw the next field of *kind*."""
        tr = get_translator().tr
        viewer = getattr(self.current_context, "viewer", None)
        if viewer is None:
            return
        already = (viewer.current_mode() == MODE_FIELD
                   and viewer.field_kind == kind)
        viewer.set_field_mode(None if already else kind)
        self.status_label.setText(
            "" if already else tr("Drag where the field belongs"))

    def _commit_field(self, context, kind, page, rect):
        """Name and write a field the user drew."""
        from PySide6.QtWidgets import QInputDialog

        tr = get_translator().tr
        document = context.document
        name, accepted = QInputDialog.getText(self, tr("Field name"),
                                              tr("Field name"))
        if not accepted or not name.strip():
            return
        options = {}
        if kind == "dropdown":
            text, accepted = QInputDialog.getText(
                self, tr("Choices"), tr("The choices, separated by commas"))
            if not accepted:
                return
            choices = [part.strip() for part in text.split(",") if part.strip()]
            if not choices:
                QMessageBox.warning(self, tr("Forms"),
                                    tr("A list of choices needs its choices."))
                return
            options["choices"] = choices
        command = PDFSnapshotCommand(
            document, f"Add field: {kind}",
            lambda: document.add_form_field(page, rect, name.strip(),
                                            kind=kind, **options))
        context.command_stack.push(command)
        if command.result is None:
            QMessageBox.warning(self, tr("Forms"),
                                document.last_error or tr("The field could not "
                                                          "be added"))
            return
        context.viewer.set_field_mode(None)
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()
        self.status_label.setText(
            f"{tr('Fields')}: {len(document.form_fields())}")

    def _remove_form_field(self):
        """Remove one field, chosen by name."""
        from PySide6.QtWidgets import QInputDialog

        tr = get_translator().tr
        context = self.current_context
        if context is None:
            return
        document = context.document
        names = [field["name"] for field in document.form_fields()
                 if field["name"]]
        if not names:
            QMessageBox.information(
                self, tr("Remove a field"),
                tr("This document has no interactive fields."))
            return
        name, accepted = QInputDialog.getItem(self, tr("Remove a field"),
                                              tr("Field name"), names, 0, False)
        if not accepted or not name:
            return
        command = PDFSnapshotCommand(document, "Remove field",
                                     lambda: document.delete_form_field(name))
        context.command_stack.push(command)
        if command.result is not True:
            QMessageBox.warning(self, tr("Forms"),
                                document.last_error or tr("The field could not "
                                                          "be removed"))
            return
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()

    # --------------------------------------------------------------- stamps
    STAMP_NOT_A_SIGNATURE = (
        "A visible stamp is a picture or text placed on the page. It is not a "
        "digital signature: it does not prove who placed it and it cannot "
        "detect a later change to the file. Digital signing is not available "
        "yet.")

    def _explain_stamp(self):
        """Say plainly what the stamp does and does not prove."""
        tr = get_translator().tr
        QMessageBox.information(self, tr("Visible stamp"),
                                tr(self.STAMP_NOT_A_SIGNATURE))

    def _stamp_mode(self, kind):
        """Arm the viewer to draw the area for the next stamp of *kind*."""
        tr = get_translator().tr
        viewer = getattr(self.current_context, "viewer", None)
        if viewer is None:
            return
        already = (viewer.current_mode() == MODE_STAMP
                   and viewer.stamp_kind == kind)
        viewer.set_stamp_mode(None if already else kind)
        self.status_label.setText(
            "" if already else tr("Drag where the stamp belongs"))

    def _commit_stamp(self, context, kind, page, rect):
        """Place the stamp the user drew the area for."""
        from PySide6.QtWidgets import QInputDialog

        tr = get_translator().tr
        document = context.document
        if kind == "image":
            path, _ = QFileDialog.getOpenFileName(
                self, tr("Choose the stamp image"), "",
                tr("Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"))
            if not path:
                return
            drop_white = QMessageBox.question(
                self, tr("Visible stamp"),
                tr("Make the white background of the image transparent?")
            ) == QMessageBox.Yes
            description = "Stamp an image"
            action = lambda: document.add_image_stamp(
                page, rect, path, drop_white_background=drop_white)
        else:
            text, accepted = QInputDialog.getText(self, tr("Stamp a name"),
                                                  tr("The text of the stamp"))
            if not accepted or not text.strip():
                return
            description = "Stamp a name"
            action = lambda: document.add_text_stamp(page, rect, text.strip())
        command = PDFSnapshotCommand(document, description, action)
        context.command_stack.push(command)
        if command.result is None:
            QMessageBox.warning(self, tr("Visible stamp"),
                                document.last_error
                                or tr("The stamp could not be placed"))
            return
        context.viewer.set_stamp_mode(None)
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()
        self.status_label.setText(tr("The stamp was placed."))

    # ------------------------------------------------------------- comments
    COMMENT_TITLES = {
        "highlight": "Highlight",
        "note": "Sticky note",
        "free_text": "Text on the page",
        "rectangle": "Rectangle",
        "ellipse": "Ellipse",
        "line": "Line",
    }

    def _comment_mode(self, kind):
        """Arm the viewer to draw the next comment of *kind*."""
        tr = get_translator().tr
        viewer = getattr(self.current_context, "viewer", None)
        if viewer is None:
            return
        already = (viewer.current_mode() == MODE_COMMENT
                   and viewer.comment_kind == kind)
        viewer.set_comment_mode(None if already else kind)
        if already:
            self.status_label.setText("")
            return
        self.status_label.setText(
            tr("Click where the note belongs") if kind == "note"
            else tr("Drag over the part you mean"))

    def _commit_comment(self, context, kind, page, payload):
        """Write a drawn comment onto the page, through the undo stack."""
        tr = get_translator().tr
        document = context.document
        options = {}
        if kind == "highlight":
            options = {"rects": list(payload)}
        elif kind == "note":
            text = self._ask_comment_text(tr("Sticky note"))
            if text is None:
                return
            options = {"point": payload, "content": text}
        elif kind == "free_text":
            text = self._ask_comment_text(tr("Text on the page"))
            if text is None:
                return
            options = {"rect": payload[0], "text": text}
        else:
            options = {"rect": payload[0]}
        command = PDFSnapshotCommand(
            document, f"Comment: {kind}",
            lambda: document.add_comment(page, kind, **options))
        context.command_stack.push(command)
        if command.result is None:
            QMessageBox.warning(self, tr("Comments"),
                                document.last_error or tr("The comment could "
                                                          "not be added"))
            return
        context.viewer.set_comment_mode(None)
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()
        self.status_label.setText(
            f"{tr('Comments')}: {len(document.page_annotations(page))}")

    def _ask_comment_text(self, title, existing=""):
        """Ask for the text of a comment; None when the user cancels."""
        from PySide6.QtWidgets import QInputDialog

        tr = get_translator().tr
        text, accepted = QInputDialog.getMultiLineText(
            self, title, tr("Comment text"), existing)
        if not accepted or not text.strip():
            return None
        return text

    def _selected_comment(self):
        viewer = getattr(self.current_context, "viewer", None)
        return getattr(viewer, "selected_annotation", None) if viewer else None

    def _delete_selected_comment(self):
        tr = get_translator().tr
        context = self.current_context
        selected = self._selected_comment()
        if context is None:
            return
        if selected is None:
            QMessageBox.information(self, tr("Comments"),
                                    tr("Click a comment on the page first."))
            return
        document = context.document
        page, xref = selected["page"], selected["xref"]
        command = PDFSnapshotCommand(
            document, "Delete comment",
            lambda: document.delete_comment(page, xref))
        context.command_stack.push(command)
        if command.result is not True:
            QMessageBox.warning(self, tr("Comments"),
                                document.last_error or tr("The comment could "
                                                          "not be removed"))
            return
        context.viewer.clear_annotation_selection()
        context.viewer.refresh_current_page()
        self._update_thumbnails()
        self._update_window_title()

    def _edit_selected_comment(self):
        tr = get_translator().tr
        context = self.current_context
        selected = self._selected_comment()
        if context is None:
            return
        if selected is None:
            QMessageBox.information(self, tr("Comments"),
                                    tr("Click a comment on the page first."))
            return
        text = self._ask_comment_text(tr("Edit the comment"),
                                      selected.get("content", ""))
        if text is None:
            return
        document = context.document
        page, xref = selected["page"], selected["xref"]
        command = PDFSnapshotCommand(
            document, "Edit comment",
            lambda: document.set_comment_text(page, xref, text))
        context.command_stack.push(command)
        if command.result is not True:
            QMessageBox.warning(self, tr("Comments"),
                                document.last_error or tr("The comment could "
                                                          "not be changed"))
            return
        context.viewer.clear_annotation_selection()
        context.viewer.refresh_current_page()
        self._update_window_title()

    def _list_comments(self):
        """Show every comment in the document, page by page."""
        tr = get_translator().tr
        document = self.current_document
        if document is None:
            return
        items = document.all_annotations()
        if not items:
            QMessageBox.information(self, tr("Comments"),
                                    tr("This document has no comments."))
            return
        lines = []
        for item in items:
            content = (item.get("content") or "").replace("\n", " ").strip()
            kind = tr(self.COMMENT_TITLES.get(item["kind"], item["kind"]))
            line = f"{tr('Page')} {item['page']} — {kind}"
            if content:
                line += f": {content[:80]}"
            lines.append(line)
        QMessageBox.information(self, tr("Comments"), "\n".join(lines))

    # ------------------------------------------------------- document tools
    def _show_properties(self):
        """Show what the open file says about itself."""
        from src.ui.properties_dialog import PropertiesDialog

        if self.current_document is None:
            return
        dialog = PropertiesDialog(self.current_document, self)
        dialog.exec()

    def _print_document(self):
        """Print the open document through the system print dialog."""
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        from PySide6.QtGui import QPainter, QImage

        tr = get_translator().tr
        document = self.current_document
        if document is None or document.doc is None:
            return
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(tr("Print"))
        if dialog.exec() != QPrintDialog.Accepted:
            return
        first = max(1, printer.fromPage() or 1)
        last = printer.toPage() or document.page_count
        last = min(last, document.page_count)
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, tr("Error"), tr("Printing failed"))
            return
        try:
            dpi = printer.resolution() or 300
            for number in range(first, last + 1):
                if number > first:
                    printer.newPage()
                page = document.get_page(number)
                if page is None:
                    continue
                pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                image = QImage(pixmap.samples, pixmap.width, pixmap.height,
                               pixmap.stride, QImage.Format_RGB888)
                area = painter.viewport()
                scaled = image.size().scaled(area.size(), Qt.KeepAspectRatio)
                painter.setViewport(area.x(), area.y(), scaled.width(),
                                    scaled.height())
                painter.setWindow(image.rect())
                painter.drawImage(0, 0, image)
        except Exception:
            logger.exception("Printing failed")
            QMessageBox.critical(self, tr("Error"), tr("Printing failed"))
        finally:
            painter.end()
        self.status_label.setText(f"{tr('Sent to the printer')}: "
                                  f"{last - first + 1}")

    def _compress_document(self):
        """Write a smaller copy of the open file and report what it saved."""
        from src.engine.optimizer import compress_pdf
        from src.ui.properties_dialog import human_size

        tr = get_translator().tr
        document = self.current_document
        if document is None:
            return
        if not document.file_path or not os.path.isfile(document.file_path):
            QMessageBox.information(self, tr("Reduce the file size"),
                                    tr("Save the document first."))
            return
        if document.is_modified:
            QMessageBox.information(
                self, tr("Reduce the file size"),
                tr("There are unsaved changes. Save them first, so the smaller "
                   "copy holds them too."))
            return
        base, ext = os.path.splitext(document.file_path)
        target, _ = QFileDialog.getSaveFileName(
            self, tr("Save the smaller file as"), f"{base}-small{ext or '.pdf'}",
            f"{tr('PDF files')} (*.pdf)")
        if not target:
            return
        try:
            result = compress_pdf(document.file_path, target,
                                  password=getattr(document, "_open_password", None))
        except Exception as exc:
            logger.exception("Compression failed")
            QMessageBox.critical(self, tr("Error"),
                                 f"{tr('Could not reduce the file size')}: {exc}")
            return
        if not result["changed"]:
            QMessageBox.information(
                self, tr("Reduce the file size"),
                tr("This file is already as small as this tool can make it; "
                   "the copy is identical."))
            return
        percent = round(result["ratio"] * 100)
        QMessageBox.information(
            self, tr("Reduce the file size"),
            f"{human_size(result['before'])} ← → {human_size(result['after'])}"
            f"  ({tr('Saved')} {percent}%)")
        self.status_label.setText(
            f"{tr('Saved')} {percent}% — {human_size(result['after'])}")

    def _refresh_current_view(self):
        """Redraw the viewer after the page content changed underneath it."""
        viewer = getattr(self.current_context, "viewer", None)
        if viewer is None:
            return
        try:
            viewer.refresh_current_page()
        except Exception:
            logger.debug("Viewer refresh failed", exc_info=True)

    def _save_file(self):
        """حفظ المستند الحالي."""
        if not self.current_document or not self.current_document.file_path:
            self._save_as_file()
            return

        if self.current_document.save():
            self._update_window_title()
            self.status_label.setText(tr("Saved"))
            logger.info(f"Saved document: {self.current_document.file_path}")

    def _save_as_file(self):
        """حفظ المستند باسم جديد."""
        if not self.current_document:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save As"),
            "",
            f"{tr('PDF files')} (*.pdf)"
        )

        if file_path:
            if self.current_document.save_as(file_path):
                self.status_label.setText(f"{tr('Saved as')}: {os.path.basename(file_path)}")
                current_index = self.tab_widget.currentIndex()
                if current_index >= 0:
                    self.tab_widget.setTabText(current_index, os.path.basename(file_path))

    def save_as_path(self, path):
        context = self.current_context
        if context is None or not context.document.save_as(path):
            return False
        context.file_path = path
        self._update_window_title()
        index = self.tab_widget.indexOf(context.viewer)
        if index >= 0:
            self.tab_widget.setTabText(index, os.path.basename(path))
        return True

    def _close_tab(self, index: int):
        """إغلاق تبويب مستند."""
        viewer = self.tab_widget.widget(index)
        context = next((item for item in self._contexts if item.viewer is viewer), None)
        if context is None:
            return
        if context.document.is_modified:
            reply = QMessageBox.question(self, "Unsaved changes", "Save changes before closing?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                         QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                self.tab_widget.setCurrentWidget(viewer)
                self._save_file()
                if context.document.is_modified:
                    return
        self._contexts.remove(context)
        self.tab_widget.removeTab(index)
        # Remove Python event filters before deferred native widget destruction.
        # A later nested Qt event loop (for example OCR progress) processes the
        # deletion after the PDF has closed; filters must not touch child widgets
        # while their C++ destructors are running.
        viewer.canvas.removeEventFilter(viewer)
        viewer.scroll_area.viewport().removeEventFilter(viewer)
        viewer.setParent(None)
        context.document.close()
        viewer.deleteLater()

        if self.tab_widget.count() == 0:
            self._show_empty_state()
        else:
            self._on_tab_changed(self.tab_widget.currentIndex())

    # === Edit Operations ===

    def _undo(self):
        """تراجع عن الأمر الأخير."""
        if self.command_stack and self.command_stack.can_undo():
            desc = self.command_stack.get_undo_description()
            self.command_stack.undo()
            self.status_label.setText(f"{tr('Undone')}: {desc}")

    def _redo(self):
        """إعادة الأمر الأخير."""
        if self.command_stack and self.command_stack.can_redo():
            desc = self.command_stack.get_redo_description()
            self.command_stack.redo()
            self.status_label.setText(f"{tr('Redone')}: {desc}")

    # === Text Editing ===

    def _delete_selected_text(self):
        context = self.current_context
        run = context.viewer.get_selected_run() if context else None
        if run is None:
            return
        command = PDFSnapshotCommand(context.document, "Delete Selected Text",
                                     lambda: context.text_editor.delete_text_run(run.run_id))
        context.command_stack.push(command)
        if command.result:
            context.viewer.refresh_current_page()
            self._update_thumbnails()
        else:
            logger.warning("Selected text could not be deleted")

    def _edit_text_mode(self):
        """الدخول في وضع تحرير النص."""
        viewer = self._get_current_viewer()
        if not viewer:
            QMessageBox.warning(self, tr("Warning"), tr("Please open a PDF file first"))
            return

        viewer.set_editing_mode(True)
        self.status_label.setText(tr("Text editing mode - Click text to edit"))

    def _add_text_mode(self):
        """الدخول في وضع إضافة نص."""
        if not self.current_document:
            QMessageBox.warning(self, tr("Warning"), tr("Please open a PDF file first"))
            return

        viewer = self._get_current_viewer()
        if not viewer:
            QMessageBox.warning(self, tr("Error"), tr("No active PDF viewer"))
            return

        viewer.set_add_text_mode(True)
        self.status_label.setText(tr("Add text mode - Click page to add text"))

    # === Image Operations ===

    def _insert_image(self):
        """إدراج صورة في الصفحة الحالية."""
        if not self.current_document:
            QMessageBox.warning(self, tr("Warning"), tr("Please open a PDF file first"))
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Image"),
            "",
            f"{tr('Images')} (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            viewer = self.tab_widget.currentWidget()
            if viewer and hasattr(viewer, 'current_page'):
                page_num = viewer.current_page
                img_id = self.image_editor.insert_image(
                    page_num, file_path, 100, 100, 200, 200
                )
                if img_id:
                    self.status_label.setText(tr("Image inserted"))
                    viewer.refresh_current_page()

    # === Page Operations ===

    def _insert_page(self):
        """إدراج صفحة فارغة."""
        if not self.page_manager:
            return

        viewer = self.tab_widget.currentWidget()
        page_num = viewer.current_page if viewer else 1

        if self.page_manager.insert_blank_page(page_num):
            self._update_thumbnails()
            self.status_label.setText(tr("Blank page inserted"))

    def _delete_page(self):
        """حذف الصفحة الحالية."""
        if not self.page_manager:
            return

        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'current_page'):
            page_num = viewer.current_page
            if self.page_manager.delete_pages([page_num]):
                self._update_thumbnails()
                self.status_label.setText(tr("Page deleted"))

    def _rotate_page(self):
        """تدوير الصفحة الحالية."""
        if not self.page_manager:
            return

        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'current_page'):
            page_num = viewer.current_page
            if self.page_manager.rotate_pages([page_num], 90):
                viewer.refresh_current_page()
                self.status_label.setText(tr("Page rotated"))

    # === View Operations ===

    def _zoom_in(self):
        """تكبير."""
        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'zoom_in'):
            viewer.zoom_in()
            self.zoom_label.setText(f"{viewer.zoom_level}%")
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(viewer.zoom_level)
            self.zoom_slider.blockSignals(False)

    def _zoom_out(self):
        """تصغير."""
        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'zoom_out'):
            viewer.zoom_out()
            self.zoom_label.setText(f"{viewer.zoom_level}%")
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(viewer.zoom_level)
            self.zoom_slider.blockSignals(False)

    def _on_zoom_slider(self, value):
        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, "set_zoom_percent"):
            viewer.set_zoom_percent(value)
            self.zoom_label.setText(f"{viewer.zoom_level}%")

    def _fit_page(self):
        """ملاءمة الصفحة مع النافذة."""
        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'fit_page'):
            viewer.fit_page()
            self.zoom_label.setText(f"{viewer.zoom_level}%")

    def _fit_width(self):
        """ملاءمة عرض الصفحة مع النافذة."""
        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'fit_width'):
            viewer.fit_width()
            self.zoom_label.setText(f"{viewer.zoom_level}%")

    def _toggle_thumbnail_panel(self):
        self.thumbnail_panel.setVisible(not self.thumbnail_panel.isVisible())

    def _toggle_properties_panel(self):
        self.properties_panel.setVisible(not self.properties_panel.isVisible())

    # === OCR ===

    def _run_ocr(self):
        """Open the isolated-process OCR workflow for the active document."""
        if self.current_context is None:
            return
        from src.ui.ocr_dialog import OCRDialog
        dialog = OCRDialog(self.current_context, self)
        dialog.exec()

    def _run_conversion(self, output_format):
        if self.current_context is None:
            return
        from src.ui.ocr_dialog import OCRDialog
        dialog = OCRDialog(self.current_context, self, conversion_format=output_format)
        dialog.exec()

    # === Create PDF ===

    def _create_pdf(self, category="all"):
        """Open the Create PDF workflow (documents and images to one PDF)."""
        from src.ui.create_pdf_dialog import CreatePDFDialog
        dialog = CreatePDFDialog(self, category=category)
        dialog.exec()

    # === Selection Handlers ===

    def _on_text_selected(self, run):
        """معالجة تحديد النص."""
        self._selected_element = run
        self._selected_element_type = 'text'

        self.properties_panel.show_text_properties({
            "font_family": run.font_name,
            "font_size": run.font_size,
            "color": f"#{int(run.color[0]*255):02x}{int(run.color[1]*255):02x}{int(run.color[2]*255):02x}",
            "direction": run.direction,
            "bold": run.bold,
            "italic": run.italic,
            "underline": run.underline,
        })

        self.status_label.setText(f"{tr('Text selected')}: {run.text[:30]}...")

    def _on_image_selected(self, image):
        """معالجة تحديد الصورة."""
        self._selected_element = image
        self._selected_element_type = 'image'

        self.properties_panel.show_image_properties({
            "width": image.width,
            "height": image.height,
            "x": image.x,
            "y": image.y,
            "rotation": image.rotation,
            "opacity": image.opacity,
        })

        self.status_label.setText(tr("Image selected"))

    def _on_page_changed(self, page_number: int):
        """معالجة تغيير الصفحة."""
        self.page_label.setText(f"{get_translator().tr('Page')}: {page_number} / {self.current_document.page_count if self.current_document else 0}")
        self.thumbnail_panel.select_page(page_number)

    def _on_thumbnail_clicked(self, page_number: int):
        """معالجة النقر على الصورة المصغرة."""
        viewer = self.tab_widget.currentWidget()
        if viewer and hasattr(viewer, 'set_page'):
            viewer.set_page(page_number)

    # === Language / Appearance ===

    def apply_preferences(self, theme=None, language=None):
        """Apply theme/language live without touching any open document."""
        changed = False
        if theme is not None:
            settings.set("theme", theme)
            self.theme_manager.set_theme(theme)
            self.theme_manager.apply_theme()
            ribbon = getattr(self, "ribbon", None)
            if ribbon is not None:
                ribbon.set_icon_color(self._ribbon_icon_color())
            changed = True
        if language is not None:
            settings.set("language", language)
            if language != get_translator().language:
                get_translator().set_language(language)
                self._retranslate_ui()
                changed = True
            else:
                self.theme_manager.set_language(language)
        if changed:
            app = QApplication.instance()
            if app is not None:
                app.processEvents()

    def _set_theme(self, theme):
        self.apply_preferences(theme=theme)

    def _toggle_language(self):
        """التبديل بين العربية والإنجليزية."""
        current = settings.get("language", "ar")
        self.apply_preferences(language="en" if current == "ar" else "ar")

    def _retranslate_ui(self):
        """إعادة ترجمة عناصر واجهة المستخدم بناءً على اللغة الحالية."""
        translator = get_translator()
        lang = translator.language
        self.theme_manager.set_language(lang)
        old = self.ribbon
        active = old.current_tab_id
        self.ribbon = self._create_main_toolbar()
        if active in self.ribbon._ids:
            self.ribbon.tab_bar.setCurrentIndex(self.ribbon._ids.index(active))
        self._main_layout.insertWidget(0, self.ribbon)
        self._main_layout.removeWidget(old)
        old.setParent(None)
        old.deleteLater()
        self._setup_menus()
        for context in self._contexts:
            context.viewer.retranslate_ui()
        self.thumbnail_panel.retranslate()
        self.properties_panel.retranslate()
        self._update_window_title()

    def _show_about(self):
        """إظهار نافذة حول البرنامج."""
        from src.config import APP_IDENTITY_1, APP_IDENTITY_2
        tr = get_translator().tr
        lines = [
            f"{APP_NAME} {APP_VERSION} (Build {BUILD_ID})",
            "",
            tr("Established and developed by"),
            tr("Future of Automation (مستقبل الأتمتة)"),
            f"{APP_IDENTITY_1} | {APP_IDENTITY_2}",
            "",
            tr("Free & Open Source Software"),
            tr("Licensed under GNU AGPL v3.0"),
            "",
            tr("A professional PDF editor for Windows."),
        ]
        QMessageBox.about(
            self,
            tr("About NextPDF Pro"),
            "\n".join(lines),
        )

    def _show_terms(self):
        """إظهار نافذة 독립ة لاتفاقية الشروط والأحكام كاملة."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
        from src.config import resource_path
        tr = get_translator().tr
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("NextPDF Pro — Terms and Conditions"))
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        # bevorzug Arabic full terms key when available; fall back to English key.
        terms_key = "Terms intro ar" if get_translator().language == "ar" else "Terms intro en"
        text.setPlainText(tr(terms_key))
        layout.addWidget(text)
        btns = QHBoxLayout()
        close_btn = QPushButton(tr("Close") if hasattr(tr, "__call__") else "إغلاق")
        try:
            close_btn.setText(tr("Close"))
        except Exception:
            close_btn.setText("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        btns.addStretch()
        btns.addWidget(close_btn)
        layout.addLayout(btns)
        dialog.exec()

    def closeEvent(self, event):
        """معالجة حدث إغلاق النافذة."""
        from src.ui.ocr_dialog import OCRDialog
        from src.ui.create_pdf_dialog import CreatePDFDialog
        for dialog in self.findChildren(OCRDialog) + self.findChildren(CreatePDFDialog):
            if dialog.worker.is_running():
                dialog.reject()
                event.ignore()
                return
        self._save_window_state()
        for context in list(self._contexts):
            index = self.tab_widget.indexOf(context.viewer)
            if index < 0:
                logger.error("Document context is missing its viewer tab")
                event.ignore()
                return
            self._close_tab(index)
            if context in self._contexts:
                event.ignore()
                return
        event.accept()

    # === Helper Methods ===

    def _get_current_viewer(self) -> Optional[PDFViewer]:
        """الحصول على عارض الصفحة الحالي النشط."""
        viewer = self.tab_widget.currentWidget()
        if viewer and isinstance(viewer, PDFViewer):
            return viewer
        return None
