#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Document properties: what the open file actually says about itself.

Every value shown is read from the document, and a value the file does not
carry is shown as a dash rather than guessed or left blank.
"""

import logging
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox,
)

from src.i18n import get_translator
from src.models.document import PERMISSION_BITS, permissions_are_restricted

logger = logging.getLogger("NextPDF")

#: Metadata keys shown, in order, with their captions.
METADATA_FIELDS = (
    ("title", "Title"),
    ("author", "Author"),
    ("subject", "Subject"),
    ("keywords", "Keywords"),
    ("creator", "Created with"),
    ("producer", "Produced by"),
    ("creationDate", "Created on"),
    ("modDate", "Changed on"),
)

PERMISSION_CAPTIONS = (
    ("print", "Allow printing"),
    ("copy", "Allow copying text"),
    ("modify", "Allow changing the document"),
    ("annotate", "Allow comments"),
)


def human_size(size: int) -> str:
    """A byte count a person can read, without inventing precision."""
    size = float(max(0, int(size)))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def page_size_text(document) -> str:
    """The page size in millimetres, noting when pages differ."""
    page = document.get_page(1) if document.page_count else None
    if page is None:
        return "—"
    sizes = set()
    for number in range(1, document.page_count + 1):
        other = document.get_page(number)
        if other is not None:
            sizes.add((round(other.rect.width), round(other.rect.height)))
    width = page.rect.width * 25.4 / 72.0
    height = page.rect.height * 25.4 / 72.0
    text = f"{width:.0f} × {height:.0f} mm"
    return text if len(sizes) <= 1 else f"{text} (+)"


class PropertiesDialog(QDialog):
    """Read-only view of the open document's properties."""

    def __init__(self, document, parent=None):
        super().__init__(parent)
        tr = get_translator().tr
        self.document = document
        self.setWindowTitle(tr("Properties"))
        self.setModal(True)
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        file_box = QGroupBox(tr("File"))
        file_form = QFormLayout(file_box)
        path = document.file_path or ""
        size = os.path.getsize(path) if path and os.path.isfile(path) else 0
        self.values = {}
        self._row(file_form, "Location", os.path.dirname(path) or "—")
        self._row(file_form, "File name", os.path.basename(path) or "—")
        self._row(file_form, "File size", human_size(size) if size else "—")
        self._row(file_form, "Pages", str(document.page_count))
        self._row(file_form, "Page size", page_size_text(document))
        layout.addWidget(file_box)

        info_box = QGroupBox(tr("Document information"))
        info_form = QFormLayout(info_box)
        metadata = document.metadata or {}
        for key, caption in METADATA_FIELDS:
            value = (metadata.get(key) or "").strip()
            self._row(info_form, caption, value or "—")
        layout.addWidget(info_box)

        security_box = QGroupBox(tr("Security"))
        security_form = QFormLayout(security_box)
        encrypted = bool(getattr(document, "is_encrypted", False))
        self._row(security_form, "Protection",
                  tr("Protected") if encrypted else tr("Not protected"))
        permissions = int(getattr(document, "permissions", 4095))
        if encrypted and permissions_are_restricted(permissions):
            for name, caption in PERMISSION_CAPTIONS:
                allowed = bool(permissions & PERMISSION_BITS[name])
                self._row(security_form, caption,
                          tr("Allowed") if allowed else tr("Not allowed"))
        layout.addWidget(security_box)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.close_button = QPushButton(tr("Close"))
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def _row(self, form, caption, value):
        tr = get_translator().tr
        label = QLabel(str(value))
        label.setWordWrap(True)
        label.setObjectName("property_" + caption.replace(" ", "_").lower())
        form.addRow(tr(caption), label)
        self.values[caption] = str(value)
        return label
