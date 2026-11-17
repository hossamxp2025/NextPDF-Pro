#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Filling an interactive form.

The dialog shows one editor per field, of the kind the field actually is,
and hands back the values.  It writes nothing itself, so it can be tested
without a document on disk.

It also carries the one honest warning this feature needs: a text field
holding Arabic keeps its value exactly, but the picture drawn inside the
field is made with the standard PDF fonts, which cannot shape Arabic.  The
way to get Arabic printed correctly is to flatten the form, which redraws
the values as real page text with a font that shapes them.
"""

import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QComboBox, QPushButton, QScrollArea, QWidget,
)

from src.i18n import get_translator
from src.engine.forms import (CHECKBOX, DROPDOWN, LISTBOX, TEXT,
                              checkbox_value, contains_arabic)

logger = logging.getLogger("NextPDF")

#: Field kinds the dialog can edit; anything else is shown but not editable.
EDITABLE = (TEXT, CHECKBOX, DROPDOWN, LISTBOX)


class FormDialog(QDialog):
    """One editor per field of the open form."""

    def __init__(self, fields, parent=None):
        super().__init__(parent)
        tr = get_translator().tr
        self.fields = list(fields or [])
        self.editors = {}
        self.setWindowTitle(tr("Fill the form"))
        self.setModal(True)
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)

        area = QScrollArea()
        area.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        for field in self.fields:
            editor = self._editor_for(field)
            caption = field["name"] or tr("Unnamed field")
            if field["page"]:
                caption = f"{caption}  ({tr('Page')} {field['page']})"
            form.addRow(caption, editor)
        area.setWidget(inner)
        layout.addWidget(area)

        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setObjectName("form_message")
        layout.addWidget(self.message)
        if self.has_arabic_text_value():
            self.message.setText(self.arabic_warning())

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton(tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton(tr("Apply"))
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.accept)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.apply_button)
        layout.addLayout(buttons)

    # ----------------------------------------------------------- building
    def _editor_for(self, field):
        kind = field["kind"]
        name = field["name"]
        if kind == CHECKBOX:
            editor = QCheckBox()
            editor.setChecked(checkbox_value(field["value"]))
        elif kind in (DROPDOWN, LISTBOX) and field["choices"]:
            editor = QComboBox()
            editor.addItems([str(choice) for choice in field["choices"]])
            current = editor.findText(str(field["value"] or ""))
            if current >= 0:
                editor.setCurrentIndex(current)
        else:
            editor = QLineEdit(str(field["value"] or ""))
            editor.setEnabled(kind in EDITABLE)
        editor.setObjectName("field_" + (name or "unnamed"))
        if field.get("read_only"):
            editor.setEnabled(False)
        self.editors[name] = editor
        return editor

    # ------------------------------------------------------------ results
    def values(self) -> dict:
        """What the user entered, by field name."""
        result = {}
        for field in self.fields:
            editor = self.editors.get(field["name"])
            if editor is None or not editor.isEnabled():
                continue
            if isinstance(editor, QCheckBox):
                result[field["name"]] = editor.isChecked()
            elif isinstance(editor, QComboBox):
                result[field["name"]] = editor.currentText()
            else:
                result[field["name"]] = editor.text()
        return result

    def changed_values(self) -> dict:
        """Only the fields whose value the user actually changed."""
        changed = {}
        for field in self.fields:
            if field["name"] not in self.values():
                continue
            new = self.values()[field["name"]]
            old = field["value"]
            if field["kind"] == CHECKBOX:
                if bool(new) != checkbox_value(old):
                    changed[field["name"]] = new
            elif str(new) != str(old or ""):
                changed[field["name"]] = new
        return changed

    def has_arabic_text_value(self) -> bool:
        for field in self.fields:
            if field["kind"] != TEXT:
                continue
            editor = self.editors.get(field["name"])
            text = editor.text() if isinstance(editor, QLineEdit) else field["value"]
            if contains_arabic(text):
                return True
        return False

    @staticmethod
    def arabic_warning() -> str:
        tr = get_translator().tr
        return tr("An Arabic value is stored exactly as you type it, but the "
                  "picture drawn inside the field uses the standard PDF "
                  "fonts, which cannot shape Arabic. Flatten the form to have "
                  "it drawn correctly on the page.")
