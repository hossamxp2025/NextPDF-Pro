#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Protection dialog: password, permissions and document information.

The dialog only collects the choices and validates them.  Writing the file
is the caller's job, so the dialog can be tested without touching disk.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QGroupBox,
)

from src.i18n import get_translator
from src.models.document import permissions_from_flags, FULL_PERMISSIONS

logger = logging.getLogger("NextPDF")

#: The permissions offered, in the order they are shown.
PERMISSION_LABELS = (
    ("print", "Allow printing"),
    ("copy", "Allow copying text"),
    ("modify", "Allow changing the document"),
    ("annotate", "Allow comments"),
)


class ProtectDialog(QDialog):
    """Collects an open password, an owner password and the permissions."""

    def __init__(self, parent=None, was_protected: bool = False):
        super().__init__(parent)
        tr = get_translator().tr
        self.tr_ = tr
        self.was_protected = was_protected
        self.setWindowTitle(tr("Protect with a password"))
        self.setModal(True)

        layout = QVBoxLayout(self)

        note = QLabel(tr(
            "The open password is asked for when the file is opened. The owner "
            "password is what lifts the restrictions below, so it has to be "
            "different from the open password."))
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QFormLayout()
        self.user_password = QLineEdit()
        self.user_password.setEchoMode(QLineEdit.Password)
        self.user_password_confirm = QLineEdit()
        self.user_password_confirm.setEchoMode(QLineEdit.Password)
        self.owner_password = QLineEdit()
        self.owner_password.setEchoMode(QLineEdit.Password)
        form.addRow(tr("Open password"), self.user_password)
        form.addRow(tr("Repeat the open password"), self.user_password_confirm)
        form.addRow(tr("Owner password"), self.owner_password)
        layout.addLayout(form)

        box = QGroupBox(tr("Permissions"))
        box_layout = QVBoxLayout(box)
        self.permission_boxes = {}
        for name, caption in PERMISSION_LABELS:
            check = QCheckBox(tr(caption))
            check.setChecked(True)
            check.setObjectName(f"permission_{name}")
            box_layout.addWidget(check)
            self.permission_boxes[name] = check
        layout.addWidget(box)

        self.strip_metadata = QCheckBox(
            tr("Also remove the document information"))
        layout.addWidget(self.strip_metadata)

        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setObjectName("protect_message")
        layout.addWidget(self.message)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton(tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton(tr("Apply"))
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self._on_apply)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.apply_button)
        layout.addLayout(buttons)

    # ----------------------------------------------------------- validation
    def restricted_permissions(self) -> bool:
        return any(not c.isChecked() for c in self.permission_boxes.values())

    def validation_error(self):
        """The reason the choices cannot be applied, or None."""
        tr = self.tr_
        user = self.user_password.text()
        owner = self.owner_password.text()
        if user != self.user_password_confirm.text():
            return tr("The two open passwords are not the same.")
        if not user and not owner and not self.strip_metadata.isChecked():
            return tr("Enter a password, or choose to remove the document "
                      "information.")
        if user and owner and user == owner:
            return tr("The owner password has to be different from the open "
                      "password.")
        if self.restricted_permissions() and not owner:
            return tr("Restrictions need an owner password, otherwise whoever "
                      "opens the file may do everything.")
        return None

    def _on_apply(self):
        error = self.validation_error()
        if error:
            self.message.setText(error)
            return
        self.accept()

    # -------------------------------------------------------------- results
    def save_arguments(self) -> dict:
        """The keyword arguments for ``PDFDocument.save``."""
        allowed = {name: box.isChecked()
                   for name, box in self.permission_boxes.items()}
        args = {
            "user_password": self.user_password.text() or None,
            "owner_password": self.owner_password.text() or None,
            "strip_metadata": self.strip_metadata.isChecked(),
        }
        args["permissions"] = (
            permissions_from_flags(allowed) if self.restricted_permissions()
            else FULL_PERMISSIONS
        )
        return args
