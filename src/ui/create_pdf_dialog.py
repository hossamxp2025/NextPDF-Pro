"""Create PDF from documents and images; layout is reflowed, not reproduced."""
import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                               QListWidgetItem, QPushButton, QProgressBar, QLabel,
                               QFileDialog)
from src.i18n import get_translator
from src.workers.creation_process import CreationProcess

FILTERS = {
    "all": "All supported (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp "
           "*.txt *.md *.html *.htm *.csv *.docx *.xlsx *.pptx)",
    "images": "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)",
    "text": "Documents (*.txt *.md *.html *.htm *.csv *.docx *.xlsx *.pptx)",
}

# Engine messages are English; the dialog translates the ones users can act on.
KNOWN_ERRORS = {
    "No source files were selected": "No source files were selected",
    "Encrypted PDF requires a password": "Encrypted PDF requires a password",
    "The selected sources produced no pages": "The selected sources produced no pages",
    "Create PDF output must use a different path": "Create PDF output must use a different path",
}


class CreatePDFDialog(QDialog):
    def __init__(self, parent=None, category="all"):
        super().__init__(parent)
        translator = get_translator()
        self.tr_text = translator.tr
        self.setWindowTitle(self.tr_text("Create PDF"))
        self.setMinimumSize(560, 420)
        self._category = category
        layout = QVBoxLayout(self)

        self.note = QLabel(self.tr_text(
            "PDF files are merged as they are. Images keep their aspect ratio. "
            "Documents are reflowed into pages; this is not a page-faithful Office render."))
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

        self.files = QListWidget()
        self.files.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.files, 1)

        row = QHBoxLayout()
        self.add_button = QPushButton(self.tr_text("Add files"))
        self.remove_button = QPushButton(self.tr_text("Remove"))
        self.up_button = QPushButton(self.tr_text("Move up"))
        self.down_button = QPushButton(self.tr_text("Move down"))
        self.add_button.clicked.connect(self._add_files)
        self.remove_button.clicked.connect(self._remove_selected)
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button.clicked.connect(lambda: self._move(1))
        for button in (self.add_button, self.remove_button, self.up_button, self.down_button):
            row.addWidget(button)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        actions = QHBoxLayout()
        self.create_button = QPushButton(self.tr_text("Create"))
        self.create_button.clicked.connect(self._choose_output)
        self.cancel_button = QPushButton(self.tr_text("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.open_button = QPushButton(self.tr_text("Open output"))
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_output)
        for button in (self.create_button, self.cancel_button, self.open_button):
            actions.addWidget(button)
        layout.addLayout(actions)

        self.worker = CreationProcess(self)
        self.worker.progress.connect(self._progress)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(self._cancelled)
        self._cancelling = False
        self._output = None

    def sources(self):
        return [self.files.item(index).data(Qt.UserRole) or self.files.item(index).text()
                for index in range(self.files.count())]

    def add_source(self, path):
        path = os.path.abspath(path)
        for index in range(self.files.count()):
            existing = self.files.item(index).data(Qt.UserRole) or self.files.item(index).text()
            if os.path.normcase(existing) == os.path.normcase(path):
                return False
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.UserRole, path)
        item.setToolTip(path)
        self.files.addItem(item)
        return True

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.tr_text("Add files"), "", self.tr_text(FILTERS[self._category]))
        for path in paths:
            self.add_source(path)

    def _remove_selected(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))

    def _move(self, offset):
        row = self.files.currentRow()
        target = row + offset
        if row < 0 or not 0 <= target < self.files.count():
            return
        item = self.files.takeItem(row)
        self.files.insertItem(target, item)
        self.files.setCurrentRow(target)

    def _choose_output(self):
        sources = self.sources()
        if not sources:
            self.status.setText(self.tr_text("Add at least one file"))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr_text("Save created PDF"), "",
                                              self.tr_text("PDF (*.pdf)"))
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self.start_creation(path)

    def start_creation(self, target):
        try:
            sources = self.sources()
            if not sources:
                raise ValueError("Add at least one file")
            for source in sources:
                if os.path.normcase(os.path.realpath(source)) == os.path.normcase(os.path.realpath(target)):
                    raise ValueError("Create PDF output must use a different path")
            self.progress.setRange(0, max(1, len(sources)))
            self.progress.setValue(0)
            self._cancelling = False
            self._output = None
            self.open_button.setEnabled(False)
            self.worker.start(sources, target)
            self._set_busy(True)
            self.status.setText(self.tr_text("Creating PDF"))
        except (ValueError, OSError, RuntimeError) as exc:
            key = str(exc) if str(exc) in KNOWN_ERRORS else "Create PDF failed"
            self.status.setText(self.tr_text(key))

    def _set_busy(self, busy):
        for widget in (self.add_button, self.remove_button, self.up_button,
                       self.down_button, self.create_button, self.files):
            widget.setEnabled(not busy)

    def _progress(self, current, total):
        self.progress.setRange(0, total)
        self.progress.setValue(current)

    def _completed(self, path):
        self._set_busy(False)
        self._output = path
        self.open_button.setEnabled(True)
        self.status.setText(self.tr_text("PDF created"))

    def _failed(self, message):
        self._set_busy(False)
        key = KNOWN_ERRORS.get(message, "Create PDF failed")
        self.status.setText(self.tr_text(key))

    def _cancelled(self):
        self._set_busy(False)
        self.status.setText(self.tr_text("PDF creation cancelled"))
        if self._cancelling:
            super().reject()

    def _open_output(self):
        if self._output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._output))

    def reject(self):
        if self.worker.is_running():
            self._cancelling = True
            self.status.setText(self.tr_text("Cancelling PDF creation"))
            self.worker.cancel()
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker.is_running():
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
