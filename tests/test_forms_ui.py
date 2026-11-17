#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The Forms tab: the fill dialog, drawing fields in the viewer, removing one,
flattening, and undoing each of those.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QInputDialog, QLineEdit, QMessageBox,
                               QPushButton)

from src.engine import forms
from src.ui.form_dialog import FormDialog
from src.ui.main_window import MainWindow
from src.ui.pdf_viewer import MODE_FIELD, MODE_SELECT


def app():
    return QApplication.instance() or QApplication([])


def form_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    for name, kind, rect, value, choices in (
            ("full_name", fitz.PDF_WIDGET_TYPE_TEXT, (40, 50, 300, 80), "", None),
            ("agree", fitz.PDF_WIDGET_TYPE_CHECKBOX, (40, 100, 60, 120), False, None),
            ("city", fitz.PDF_WIDGET_TYPE_COMBOBOX, (40, 140, 300, 170),
             "Cairo", ["Cairo", "Giza"])):
        widget = fitz.Widget()
        widget.rect = fitz.Rect(rect)
        widget.field_name = name
        widget.field_type = kind
        if choices:
            widget.choice_values = choices
        widget.field_value = value
        page.add_widget(widget)
    doc.save(path)
    doc.close()
    return path


def plain_pdf(path):
    doc = fitz.open()
    doc.new_page(width=400, height=300).insert_text((40, 60), "plain page")
    doc.save(path)
    doc.close()
    return path


FIELDS = [
    {"name": "full_name", "kind": "text", "value": "", "choices": [],
     "page": 1, "rect": (40, 50, 300, 80), "read_only": False, "label": ""},
    {"name": "agree", "kind": "checkbox", "value": "Off", "choices": [],
     "page": 1, "rect": (40, 100, 60, 120), "read_only": False, "label": ""},
    {"name": "city", "kind": "dropdown", "value": "Cairo",
     "choices": ["Cairo", "Giza"], "page": 1, "rect": (40, 140, 300, 170),
     "read_only": False, "label": ""},
    {"name": "locked", "kind": "text", "value": "fixed", "choices": [],
     "page": 1, "rect": (40, 200, 300, 230), "read_only": True, "label": ""},
]


class FormDialogTests(unittest.TestCase):
    def setUp(self):
        app()
        self.dialog = FormDialog([dict(field) for field in FIELDS])

    def tearDown(self):
        self.dialog.deleteLater()

    def test_each_field_gets_the_editor_its_kind_needs(self):
        self.assertIsInstance(self.dialog.editors["full_name"], QLineEdit)
        self.assertIsInstance(self.dialog.editors["agree"], QCheckBox)
        self.assertIsInstance(self.dialog.editors["city"], QComboBox)

    def test_a_dropdown_offers_exactly_its_choices(self):
        box = self.dialog.editors["city"]
        self.assertEqual([box.itemText(i) for i in range(box.count())],
                         ["Cairo", "Giza"])

    def test_the_current_value_is_shown(self):
        self.assertEqual(self.dialog.editors["city"].currentText(), "Cairo")

    def test_a_read_only_field_cannot_be_edited(self):
        self.assertFalse(self.dialog.editors["locked"].isEnabled())

    def test_only_what_changed_is_returned(self):
        self.dialog.editors["full_name"].setText("Hossam")
        self.assertEqual(self.dialog.changed_values(), {"full_name": "Hossam"})

    def test_a_tick_is_returned_as_a_yes(self):
        self.dialog.editors["agree"].setChecked(True)
        self.assertEqual(self.dialog.changed_values(), {"agree": True})

    def test_a_read_only_field_is_never_returned(self):
        self.assertNotIn("locked", self.dialog.values())

    def test_an_arabic_value_raises_the_appearance_warning(self):
        self.assertFalse(self.dialog.has_arabic_text_value())
        self.dialog.editors["full_name"].setText("حسام")
        self.assertTrue(self.dialog.has_arabic_text_value())
        # The warning is translated at runtime, so only its substance is
        # checked: it says something, and it names flattening as the way out.
        warning = FormDialog.arabic_warning()
        self.assertGreater(len(warning), 40)
        self.assertNotEqual(warning, "An Arabic value")


class FormsTabTests(unittest.TestCase):
    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_forms_ui_")
        self.path = form_pdf(os.path.join(self.tmp, "form.pdf"))
        self.window = MainWindow()
        self.assertTrue(self.window._open_file_path(self.path))
        self.viewer = self.window.current_context.viewer
        self.document = self.window.current_document
        self.messages = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.warning = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def values(self):
        return {f["name"]: f["value"] for f in self.document.form_fields()}

    def drag(self, rect):
        polygon = self.viewer.canvas.pdf_to_widget(rect)
        start, end = polygon.at(0), polygon.at(2)

        def event(kind, point):
            return QMouseEvent(kind, QPointF(point), Qt.LeftButton,
                               Qt.LeftButton, Qt.NoModifier)

        self.viewer._on_canvas_press(event(QEvent.MouseButtonPress, start))
        self.viewer._on_canvas_move(event(QEvent.MouseMove, end))
        self.viewer._on_canvas_release(event(QEvent.MouseButtonRelease, end))

    # --------------------------------------------------------------- tests
    def test_the_forms_tab_has_working_buttons(self):
        names = ("tool_Fill_the_form", "tool_Flatten_the_form",
                 "tool_Add_a_text_field", "tool_Add_a_tick_box",
                 "tool_Add_a_list_of_choices", "tool_Remove_a_field")
        for name in names:
            button = self.window.ribbon.findChild(QPushButton, name)
            self.assertIsNotNone(button, f"{name} is missing from the ribbon")
            self.assertTrue(button.isEnabled(), f"{name} is disabled")

    def test_filling_through_the_dialog_writes_the_values(self):
        def fill(dialog):
            dialog.editors["full_name"].setText("Hossam")
            dialog.editors["agree"].setChecked(True)
            dialog.editors["city"].setCurrentText("Giza")
            return QDialog.Accepted

        FormDialog.exec = fill
        self.window._fill_form()
        values = self.values()
        self.assertEqual(values["full_name"], "Hossam")
        self.assertEqual(values["city"], "Giza")
        self.assertTrue(forms.checkbox_value(values["agree"]))

    def test_cancelling_the_dialog_writes_nothing(self):
        FormDialog.exec = lambda dialog: QDialog.Rejected
        self.window._fill_form()
        self.assertEqual(self.values()["full_name"], "")

    def test_filling_can_be_undone(self):
        FormDialog.exec = (lambda dialog:
                           (dialog.editors["full_name"].setText("Hossam"),
                            QDialog.Accepted)[1])
        self.window._fill_form()
        self.window._undo()
        self.assertEqual(self.values()["full_name"], "")

    def test_an_arabic_value_is_stored_and_the_user_is_warned(self):
        FormDialog.exec = (lambda dialog:
                           (dialog.editors["full_name"].setText("حسام"),
                            QDialog.Accepted)[1])
        self.window._fill_form()
        self.assertEqual(self.values()["full_name"], "حسام")
        self.assertTrue(self.messages, "the appearance limit must be said")

    def test_a_document_without_fields_says_so(self):
        plain = plain_pdf(os.path.join(self.tmp, "plain.pdf"))
        self.window._open_file_path(plain)
        self.window._fill_form()
        self.assertTrue(self.messages)

    def test_drawing_a_text_field_asks_for_a_name_and_adds_it(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("phone", True))
        self.window._field_mode("text")
        self.assertEqual(self.viewer.current_mode(), MODE_FIELD)
        self.drag(fitz.Rect(40, 200, 300, 230))
        self.assertIn("phone", self.values())
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    def test_a_cancelled_name_adds_nothing(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
        self.window._field_mode("text")
        self.drag(fitz.Rect(40, 200, 300, 230))
        self.assertEqual(len(self.document.form_fields()), 3)

    def test_a_duplicate_name_is_refused_with_a_message(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("full_name", True))
        self.window._field_mode("text")
        self.drag(fitz.Rect(40, 200, 300, 230))
        self.assertEqual(len(self.document.form_fields()), 3)
        self.assertTrue(self.messages)

    def test_a_drawn_tick_box_is_a_tick_box(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("confirmed", True))
        self.window._field_mode("checkbox")
        self.drag(fitz.Rect(40, 200, 70, 230))
        kinds = {f["name"]: f["kind"] for f in self.document.form_fields()}
        self.assertEqual(kinds["confirmed"], "checkbox")

    def test_a_drawn_list_takes_its_choices(self):
        answers = iter([("country", True), ("Egypt, Jordan", True)])
        QInputDialog.getText = staticmethod(lambda *a, **k: next(answers))
        self.window._field_mode("dropdown")
        self.drag(fitz.Rect(40, 200, 300, 230))
        country = [f for f in self.document.form_fields()
                   if f["name"] == "country"][0]
        self.assertEqual(country["choices"], ["Egypt", "Jordan"])

    def test_adding_a_field_can_be_undone(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("phone", True))
        self.window._field_mode("text")
        self.drag(fitz.Rect(40, 200, 300, 230))
        self.window._undo()
        self.assertNotIn("phone", self.values())

    def test_a_field_can_be_removed_by_name(self):
        QInputDialog.getItem = staticmethod(lambda *a, **k: ("city", True))
        self.window._remove_form_field()
        self.assertNotIn("city", self.values())

    def test_removing_a_field_can_be_undone(self):
        QInputDialog.getItem = staticmethod(lambda *a, **k: ("city", True))
        self.window._remove_form_field()
        self.window._undo()
        self.assertIn("city", self.values())

    def test_flattening_removes_the_fields_from_the_document(self):
        FormDialog.exec = (lambda dialog:
                           (dialog.editors["full_name"].setText("Hossam"),
                            QDialog.Accepted)[1])
        self.window._fill_form()
        self.window._flatten_form()
        self.assertEqual(self.document.form_fields(), [])

    def test_flattening_can_be_undone(self):
        self.window._flatten_form()
        self.assertEqual(self.document.form_fields(), [])
        self.window._undo()
        self.assertEqual(len(self.document.form_fields()), 3)

    def test_flattening_a_document_without_fields_says_so(self):
        self.window._open_file_path(plain_pdf(os.path.join(self.tmp, "p2.pdf")))
        self.window._flatten_form()
        self.assertTrue(self.messages)

    def test_the_filled_values_reach_the_saved_file(self):
        FormDialog.exec = (lambda dialog:
                           (dialog.editors["full_name"].setText("Hossam"),
                            QDialog.Accepted)[1])
        self.window._fill_form()
        target = os.path.join(self.tmp, "filled.pdf")
        self.assertTrue(self.document.save(target))
        with fitz.open(target) as saved:
            values = {w.field_name: w.field_value for w in saved[0].widgets()}
        self.assertEqual(values["full_name"], "Hossam")


if __name__ == "__main__":
    unittest.main()
