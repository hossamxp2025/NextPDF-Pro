"""OCR options and progress; processing occurs in an isolated child process."""
import os
import re
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox,
                              QLineEdit, QPushButton, QProgressBar, QLabel,
                              QFileDialog, QSpinBox)
from src.i18n import get_translator
from src.workers.ocr_process import OCRProcess, ConversionProcess


#: Conversion formats whose output is a rendered image, so the resolution
#: matters.  OCR recognition runs at its own fixed resolution, so the control
#: is not shown there rather than pretending to change it.
RASTER_FORMATS = {"png", "jpg", "tiff", "webp", "docx", "pptx"}

#: Conversion formats that read the text, so a scanned page is recognised
#: automatically and the recognition language matters.
TEXT_FORMATS = {"txt", "html", "md", "json"}


class OCRDialog(QDialog):
    def __init__(self, context, parent=None, conversion_format=None):
        super().__init__(parent)
        self.context = context
        mapping = {
            "OCR": "Convert PDF", "Start OCR": "Start conversion",
            "Save OCR output": "Save conversion output", "OCR failed": "Conversion failed",
            "Processing OCR": "Converting PDF", "OCR output saved": "Conversion output saved",
            "OCR cancelled": "Conversion cancelled", "Cancelling OCR": "Cancelling conversion",
            "OCR preserves the page image; it does not restore editable layout.": "Text formats export logical text, not original layout. SVG requires one selected page. Several pages of PNG, JPEG or WEBP are written as numbered files beside the one you name; TIFF holds them all in one file.",
        } if conversion_format else {}
        translator = get_translator()
        self.tr_text = lambda key: translator.tr(mapping.get(key, key))
        tr = self.tr_text
        self.setWindowTitle(tr("Convert PDF") if conversion_format else tr("OCR"))
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.scope = QComboBox()
        for key, value in (("Current page", "current"), ("All pages", "all"), ("Selected pages", "selected")):
            self.scope.addItem(tr(key), value)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("1-3,5")
        self.language = QComboBox()
        for key, value in (("Arabic", "ara"), ("English", "eng"), ("Arabic and English", "ara+eng")):
            self.language.addItem(tr(key), value)
        self.language.setCurrentIndex(2)
        self.output_format = QComboBox()
        self.output_format.addItem(tr("Searchable PDF"), "pdf")
        self.output_format.addItem("TXT", "txt")
        if conversion_format:
            self.output_format.clear()
            self.output_format.addItem(conversion_format.upper(), conversion_format)
        # Resolution only changes a rendered image; it means nothing for the
        # text formats, so it is only shown where it has an effect.
        self.dpi = QSpinBox()
        self.dpi.setRange(72, 600)
        self.dpi.setSingleStep(25)
        self.dpi.setValue(150)
        self.dpi.setSuffix(" DPI")
        form.addRow(tr("Pages"), self.scope)
        form.addRow(tr("Page range"), self.pages)
        form.addRow(tr("Recognition language"), self.language)
        form.addRow(tr("Output format"), self.output_format)
        form.addRow(tr("Resolution"), self.dpi)
        if conversion_format and conversion_format not in TEXT_FORMATS:
            self.language.hide()
            form.labelForField(self.language).hide()
        if conversion_format is None or conversion_format not in RASTER_FORMATS:
            self.dpi.hide()
            form.labelForField(self.dpi).hide()
        layout.addLayout(form)
        self.note = QLabel(tr("OCR preserves the page image; it does not restore editable layout."))
        self.note.setWordWrap(True)
        if conversion_format in {"docx", "pptx"}:
            self.note.setText(tr("Page images only: appearance preserved, text and tables are not editable."))
        elif conversion_format == "docx_editable":
            self.note.setText(tr("Editable Word: tables, shading, fonts and reading order are rebuilt; absolute positions are not. Legacy visual Arabic is refused."))
        elif conversion_format == "pptx_editable":
            self.note.setText(tr("Editable slides: real positioned text boxes and images, approximate layout. Legacy visual Arabic is refused."))
        elif conversion_format == "md":
            self.note.setText(tr("Markdown: headings come from the text sizes on the page and detected tables become real tables. A scanned page is recognised automatically and marked as recognised."))
        elif conversion_format in TEXT_FORMATS:
            self.note.setText(tr("Logical text, not the original layout. A scanned page is recognised automatically with the chosen language."))
        elif conversion_format in {"xlsx", "csv"}:
            self.note.setText(tr("Extracts rectangular tables and some aligned borderless tables. Review the output. CSV requires one table. Merged cells and scanned tables are not reliably supported."))
        layout.addWidget(self.note)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.start_button = QPushButton(tr("Start OCR"))
        self.start_button.clicked.connect(self._choose_output)
        self.cancel_button = QPushButton(tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.open_button = QPushButton(tr("Open output"))
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_output)
        for button in (self.start_button, self.cancel_button, self.open_button):
            layout.addWidget(button)
        self.worker = ConversionProcess(self) if conversion_format else OCRProcess(self)
        self.worker.progress.connect(self._progress)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(self._cancelled)
        self._cancelling = False
        self._output = None

    def selected_pages(self):
        count = self.context.document.page_count
        scope = self.scope.currentData()
        if scope == "current":
            return [self.context.viewer.current_page]
        if scope == "all":
            return list(range(1, count + 1))
        text = self.pages.text().replace(" ", "")
        if not re.fullmatch(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*", text):
            raise ValueError("Page range is invalid")
        numbers = []
        for part in text.split(","):
            bounds = [int(value) for value in part.split("-")]
            a, b = bounds[0], bounds[-1]
            if not 1 <= a <= b <= count:
                raise ValueError("Page range is invalid")
            numbers.extend(range(a, b + 1))
        return list(dict.fromkeys(numbers))

    def _choose_output(self):
        try:
            self.selected_pages()
        except ValueError:
            self.status.setText(self.tr_text("Page range is invalid"))
            return
        extension = self._extension()
        path, _ = QFileDialog.getSaveFileName(self, self.tr_text("Save OCR output"), "",
                                             f"{extension.upper()} (*.{extension})")
        if path:
            if not path.lower().endswith("." + extension):
                path += "." + extension
            self.start_export(path)

    def _extension(self):
        selected = self.output_format.currentData()
        return {"docx_editable": "docx", "pptx_editable": "pptx"}.get(selected, selected)

    def start_export(self, target):
        try:
            source = self.context.document.file_path
            if source and os.path.normcase(os.path.realpath(source)) == os.path.normcase(os.path.realpath(target)):
                raise ValueError("OCR output must use a different path")
            pages = self.selected_pages()
            data = self.context.document.to_bytes()
            if not data:
                raise ValueError("OCR failed")
            self.progress.setRange(0, len(pages))
            self.progress.setValue(0)
            self._cancelling = False
            self._output = None
            self.open_button.setEnabled(False)
            self.worker.start(data, target, self.language.currentData(), pages,
                              self.output_format.currentData(), self.dpi.value())
            self._set_busy(True)
            self.status.setText(self.tr_text("Processing OCR"))
        except (ValueError, OSError, RuntimeError) as exc:
            key = str(exc) if str(exc) in {"OCR output must use a different path", "Page range is invalid"} else "OCR failed"
            self.status.setText(self.tr_text(key))

    def _set_busy(self, busy):
        for widget in (self.start_button, self.scope, self.pages, self.language,
                       self.output_format, self.dpi):
            widget.setEnabled(not busy)

    def _progress(self, current, total):
        self.progress.setRange(0, total)
        self.progress.setValue(current)

    def _completed(self, path):
        self._set_busy(False)
        self._output = path
        self.open_button.setEnabled(True)
        written = len(getattr(self.worker, "published_files", ()) or ())
        if written > 1:
            self.status.setText(
                f"{self.tr_text('OCR output saved')} ({written})")
        else:
            self.status.setText(self.tr_text("OCR output saved"))

    def _failed(self, message):
        self._set_busy(False)
        # Engine messages are English keys; translate them when known so the
        # user never sees a raw traceback or English-only text in Arabic UI.
        key = "No extractable tables were found in this PDF. Try a document with a clearly structured table or use another extraction method."
        text = self.tr_text(key) if message == "no_tables" else self.tr_text("OCR failed")
        self.status.setText(text)

    def _cancelled(self):
        self._set_busy(False)
        self.status.setText(self.tr_text("OCR cancelled"))
        if self._cancelling:
            super().reject()

    def _open_output(self):
        if self._output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._output))

    def reject(self):
        if self.worker.is_running():
            self._cancelling = True
            self.status.setText(self.tr_text("Cancelling OCR"))
            self.worker.cancel()
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker.is_running():
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
