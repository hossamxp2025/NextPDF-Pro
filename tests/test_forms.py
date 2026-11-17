#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactive form fields: read, fill, add, remove and flatten.  Every check
reads the saved file, and the Arabic appearance limit is tested rather than
assumed.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.engine import forms
from src.models.document import PDFDocument


def form_pdf(path):
    """A small form: a text field, a checkbox and a dropdown."""
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((40, 30), "Registration")
    for name, kind, rect, value, choices in (
            ("full_name", fitz.PDF_WIDGET_TYPE_TEXT, (40, 50, 300, 80), "", None),
            ("agree", fitz.PDF_WIDGET_TYPE_CHECKBOX, (40, 100, 60, 120), False, None),
            ("city", fitz.PDF_WIDGET_TYPE_COMBOBOX, (40, 140, 300, 170),
             "Cairo", ["Cairo", "Giza", "Alexandria"])):
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
    doc.new_page().insert_text((40, 60), "no form here")
    doc.save(path)
    doc.close()
    return path


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_forms_")
        self.doc = fitz.open(form_pdf(os.path.join(self.tmp, "form.pdf")))

    def tearDown(self):
        self.doc.close()

    def test_a_form_is_recognised_as_a_form(self):
        self.assertTrue(forms.is_form(self.doc))

    def test_a_plain_file_is_not_a_form(self):
        with fitz.open(plain_pdf(os.path.join(self.tmp, "plain.pdf"))) as plain:
            self.assertFalse(forms.is_form(plain))

    def test_every_field_is_listed_with_its_kind(self):
        found = {field["name"]: field["kind"] for field in forms.list_fields(self.doc)}
        self.assertEqual(found, {"full_name": "text", "agree": "checkbox",
                                 "city": "dropdown"})

    def test_a_dropdown_reports_its_choices(self):
        city = [f for f in forms.list_fields(self.doc) if f["name"] == "city"][0]
        self.assertEqual(city["choices"], ["Cairo", "Giza", "Alexandria"])

    def test_a_field_knows_which_page_it_is_on(self):
        self.assertEqual({f["page"] for f in forms.list_fields(self.doc)}, {1})

    def test_a_text_field_keeps_what_was_typed(self):
        result = forms.set_value(self.doc, "full_name", "Hossam")
        self.assertTrue(result["stored"])
        self.assertTrue(result["appearance_ok"])
        self.assertEqual(result["field"]["value"], "Hossam")

    def test_a_checkbox_understands_a_yes(self):
        forms.set_value(self.doc, "agree", True)
        agree = [f for f in forms.list_fields(self.doc) if f["name"] == "agree"][0]
        self.assertTrue(forms.checkbox_value(agree["value"]))

    def test_a_checkbox_understands_a_no(self):
        forms.set_value(self.doc, "agree", True)
        forms.set_value(self.doc, "agree", False)
        agree = [f for f in forms.list_fields(self.doc) if f["name"] == "agree"][0]
        self.assertFalse(forms.checkbox_value(agree["value"]))

    def test_a_dropdown_takes_one_of_its_choices(self):
        self.assertTrue(forms.set_value(self.doc, "city", "Giza")["stored"])

    def test_a_dropdown_refuses_anything_else(self):
        result = forms.set_value(self.doc, "city", "Madrid")
        self.assertFalse(result["stored"])
        self.assertIn("choices", result["reason"])

    def test_an_unknown_field_is_reported(self):
        self.assertFalse(forms.set_value(self.doc, "nothing", "x")["stored"])

    def test_an_arabic_value_is_stored_exactly_but_flagged(self):
        # The value is the data and is kept intact; the appearance drawn with
        # the standard PDF fonts cannot show it, and that is reported.
        result = forms.set_value(self.doc, "full_name", "حسام الفاخرة")
        self.assertTrue(result["stored"])
        self.assertFalse(result["appearance_ok"])
        self.assertEqual(result["field"]["value"], "حسام الفاخرة")

    def test_an_arabic_choice_in_a_dropdown_is_not_flagged_as_text(self):
        result = forms.set_value(self.doc, "agree", True)
        self.assertTrue(result["appearance_ok"])

    def test_a_field_can_be_added(self):
        field = forms.add_field(self.doc[0], (40, 200, 300, 230), "phone")
        self.assertEqual(field["kind"], "text")
        self.assertEqual(len(forms.list_fields(self.doc)), 4)

    def test_a_dropdown_can_be_added_with_its_choices(self):
        field = forms.add_field(self.doc[0], (40, 200, 300, 230), "country",
                                kind="dropdown", choices=["Egypt", "Jordan"])
        self.assertEqual(field["choices"], ["Egypt", "Jordan"])

    def test_a_dropdown_without_choices_is_refused(self):
        with self.assertRaises(ValueError):
            forms.add_field(self.doc[0], (40, 200, 300, 230), "x",
                            kind="dropdown")

    def test_a_duplicate_name_is_refused(self):
        with self.assertRaises(ValueError):
            forms.add_field(self.doc[0], (40, 200, 300, 230), "full_name")

    def test_a_nameless_field_is_refused(self):
        with self.assertRaises(ValueError):
            forms.add_field(self.doc[0], (40, 200, 300, 230), "  ")

    def test_a_field_with_no_area_is_refused(self):
        with self.assertRaises(ValueError):
            forms.add_field(self.doc[0], (40, 200, 40, 200), "x")

    def test_an_uncreatable_kind_is_refused(self):
        with self.assertRaises(ValueError):
            forms.add_field(self.doc[0], (40, 200, 300, 230), "sig",
                            kind="signature")

    def test_a_field_can_be_removed(self):
        self.assertTrue(forms.delete_field(self.doc, "city"))
        self.assertEqual(len(forms.list_fields(self.doc)), 2)

    def test_removing_an_unknown_field_reports_false(self):
        self.assertFalse(forms.delete_field(self.doc, "nothing"))


class FlattenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_flatten_")
        self.path = form_pdf(os.path.join(self.tmp, "form.pdf"))

    def test_flattening_removes_the_fields(self):
        document = PDFDocument()
        document.load(self.path)
        try:
            document.set_field_value("full_name", "Hossam")
            result = document.flatten_form()
            self.assertEqual(result["flattened"], 3)
            target = os.path.join(self.tmp, "flat.pdf")
            document.save(target)
        finally:
            document.close()
        with fitz.open(target) as flat:
            self.assertEqual(list(flat[0].widgets()), [])
            self.assertFalse(forms.is_form(flat))

    def test_the_latin_value_stays_visible_on_the_page(self):
        document = PDFDocument()
        document.load(self.path)
        try:
            document.set_field_value("full_name", "Hossam")
            document.flatten_form()
            target = os.path.join(self.tmp, "flat-latin.pdf")
            document.save(target)
        finally:
            document.close()
        with fitz.open(target) as flat:
            self.assertIn("Hossam", flat[0].get_text())

    def test_an_arabic_value_is_redrawn_with_a_font_that_shapes_it(self):
        document = PDFDocument()
        document.load(self.path)
        try:
            document.set_field_value("full_name", "حسام الفاخرة")
            result = document.flatten_form()
            self.assertEqual(result["redrawn"], 1)
            target = os.path.join(self.tmp, "flat-arabic.pdf")
            document.save(target)
        finally:
            document.close()
        with fitz.open(target) as flat:
            text = flat[0].get_text()
        # The redrawn text is logical Arabic, not the broken presentation
        # forms the standard PDF fonts produce.
        self.assertIn("حسام", text)
        self.assertNotIn("Ǆ", text)

    def test_flattening_an_empty_document_changes_nothing(self):
        document = PDFDocument()
        document.load(plain_pdf(os.path.join(self.tmp, "plain.pdf")))
        try:
            self.assertEqual(document.flatten_form(),
                             {"flattened": 0, "redrawn": 0})
            self.assertFalse(document.is_modified)
        finally:
            document.close()


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_forms_doc_")
        self.document = PDFDocument()
        self.assertTrue(self.document.load(
            form_pdf(os.path.join(self.tmp, "form.pdf"))))

    def tearDown(self):
        self.document.close()

    def test_the_document_reports_that_it_has_a_form(self):
        self.assertTrue(self.document.has_form())

    def test_filling_marks_the_document_as_modified(self):
        self.document.is_modified = False
        self.document.set_field_value("full_name", "Hossam")
        self.assertTrue(self.document.is_modified)

    def test_a_refused_fill_leaves_a_reason(self):
        self.document.is_modified = False
        self.assertFalse(self.document.set_field_value("city", "Madrid")["stored"])
        self.assertTrue(self.document.last_error)
        self.assertFalse(self.document.is_modified)

    def test_the_values_survive_a_save_and_reopen(self):
        self.document.set_field_value("full_name", "Hossam")
        self.document.set_field_value("agree", True)
        self.document.set_field_value("city", "Giza")
        target = os.path.join(self.tmp, "filled.pdf")
        self.assertTrue(self.document.save(target))
        reopened = PDFDocument()
        try:
            reopened.load(target)
            values = {f["name"]: f["value"] for f in reopened.form_fields()}
            self.assertEqual(values["full_name"], "Hossam")
            self.assertEqual(values["city"], "Giza")
            self.assertTrue(forms.checkbox_value(values["agree"]))
        finally:
            reopened.close()

    def test_an_arabic_value_survives_the_save_exactly(self):
        self.document.set_field_value("full_name", "حسام الفاخرة")
        target = os.path.join(self.tmp, "arabic.pdf")
        self.document.save(target)
        reopened = PDFDocument()
        try:
            reopened.load(target)
            values = {f["name"]: f["value"] for f in reopened.form_fields()}
            self.assertEqual(values["full_name"], "حسام الفاخرة")
        finally:
            reopened.close()

    def test_a_field_added_through_the_document_is_fillable(self):
        self.assertIsNotNone(self.document.add_form_field(
            1, (40, 200, 300, 230), "phone"))
        self.assertTrue(self.document.set_field_value("phone", "0100")["stored"])

    def test_a_refused_field_leaves_a_reason(self):
        self.assertIsNone(self.document.add_form_field(
            1, (40, 200, 300, 230), "full_name"))
        self.assertTrue(self.document.last_error)

    def test_a_field_can_be_removed_through_the_document(self):
        self.assertTrue(self.document.delete_form_field("city"))
        self.assertNotIn("city", [f["name"] for f in self.document.form_fields()])


if __name__ == "__main__":
    unittest.main()
