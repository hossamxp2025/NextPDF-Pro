#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The three document buttons that used to be dead: Properties, Print and
Reduce the file size.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import (QApplication, QFileDialog, QMessageBox,
                               QPushButton)

from src.models.document import PDFDocument
from src.ui.main_window import MainWindow
from src.ui.properties_dialog import PropertiesDialog, human_size, page_size_text

SAMPLE = "PROPERTIES SAMPLE"


def app():
    return QApplication.instance() or QApplication([])


def make_pdf(path, metadata=None, pages=1):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=595, height=842).insert_text((72, 72), SAMPLE)
    if metadata:
        doc.set_metadata(metadata)
    doc.save(path)
    doc.close()
    return path


def heavy_pdf(path, pages=3, dpi=300):
    with fitz.open() as typeset:
        page = typeset.new_page(width=400, height=300)
        for y in range(40, 280, 12):
            page.insert_text((20, y), "lorem ipsum dolor sit amet et cetera",
                             fontsize=9)
        image = page.get_pixmap(dpi=dpi).tobytes("png")
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page(width=400, height=300).insert_image(
                fitz.Rect(0, 0, 400, 300), stream=image)
        doc.save(path, deflate=False)
    return path


class SizeFormattingTests(unittest.TestCase):
    def test_bytes_are_shown_whole(self):
        self.assertEqual(human_size(512), "512 B")

    def test_kilobytes_and_megabytes_carry_one_decimal(self):
        self.assertEqual(human_size(2048), "2.0 KB")
        self.assertEqual(human_size(5 * 1024 * 1024), "5.0 MB")


class PropertiesDialogTests(unittest.TestCase):
    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_props_")
        self.path = make_pdf(os.path.join(self.tmp, "doc.pdf"),
                             metadata={"title": "Quarter report",
                                       "author": "Finance"})
        self.document = PDFDocument()
        self.assertTrue(self.document.load(self.path))

    def tearDown(self):
        self.document.close()

    def test_the_file_facts_come_from_the_file(self):
        dialog = PropertiesDialog(self.document)
        self.assertEqual(dialog.values["File name"], "doc.pdf")
        self.assertEqual(dialog.values["Pages"], "1")
        self.assertNotEqual(dialog.values["File size"], "—")
        dialog.deleteLater()

    def test_the_metadata_is_shown_as_written(self):
        dialog = PropertiesDialog(self.document)
        self.assertEqual(dialog.values["Title"], "Quarter report")
        self.assertEqual(dialog.values["Author"], "Finance")
        dialog.deleteLater()

    def test_a_missing_field_is_a_dash_not_a_guess(self):
        dialog = PropertiesDialog(self.document)
        self.assertEqual(dialog.values["Subject"], "—")
        dialog.deleteLater()

    def test_an_unprotected_file_says_so(self):
        dialog = PropertiesDialog(self.document)
        self.assertIn(dialog.values["Protection"], ("Not protected", "غير محمي"))
        dialog.deleteLater()

    def test_a_protected_file_is_reported_as_protected(self):
        protected = os.path.join(self.tmp, "protected.pdf")
        self.document.save(protected, user_password="open-me")
        dialog = PropertiesDialog(self.document)
        self.assertIn(dialog.values["Protection"], ("Protected", "محمي"))
        dialog.deleteLater()

    def test_the_page_size_is_reported_in_millimetres(self):
        text = page_size_text(self.document)
        self.assertIn("210", text)
        self.assertIn("297", text)

    def test_mixed_page_sizes_are_marked(self):
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.new_page(width=300, height=300)
        mixed = os.path.join(self.tmp, "mixed.pdf")
        doc.save(mixed)
        doc.close()
        document = PDFDocument()
        document.load(mixed)
        try:
            self.assertTrue(page_size_text(document).endswith("(+)"))
        finally:
            document.close()


class DocumentButtonTests(unittest.TestCase):
    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_doc_tools_")
        self.window = MainWindow()

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def test_the_document_buttons_are_enabled_with_a_file_open(self):
        self.window._open_file_path(make_pdf(os.path.join(self.tmp, "a.pdf")))
        for name in ("tool_Print", "tool_Properties", "tool_Reduce_the_file_size"):
            button = self.window.ribbon.findChild(QPushButton, name)
            self.assertIsNotNone(button, f"{name} is missing from the ribbon")
            self.assertTrue(button.isEnabled(), f"{name} is disabled")

    def test_the_properties_button_opens_a_dialog_about_the_open_file(self):
        path = make_pdf(os.path.join(self.tmp, "b.pdf"),
                        metadata={"title": "Opened"})
        self.window._open_file_path(path)
        shown = []
        PropertiesDialog.exec = lambda self: shown.append(self) or 0
        self.window._show_properties()
        self.assertTrue(shown)
        self.assertEqual(shown[0].values["Title"], "Opened")

    def test_compressing_writes_a_smaller_file(self):
        source = heavy_pdf(os.path.join(self.tmp, "heavy.pdf"))
        target = os.path.join(self.tmp, "small.pdf")
        self.window._open_file_path(source)
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (target, ""))
        messages = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: messages.append(a[2] if len(a) > 2 else ""))
        self.window._compress_document()
        self.assertTrue(os.path.isfile(target))
        self.assertLess(os.path.getsize(target), os.path.getsize(source))
        self.assertTrue(messages and "%" in messages[0])

    def test_compressing_refuses_while_there_are_unsaved_changes(self):
        source = make_pdf(os.path.join(self.tmp, "c.pdf"))
        self.window._open_file_path(source)
        self.window.current_document.is_modified = True
        asked = []
        QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: asked.append(a) or ("", ""))
        messages = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: messages.append(a[2] if len(a) > 2 else ""))
        self.window._compress_document()
        self.assertTrue(messages)
        self.assertEqual(asked, [], "it must not ask for a path before saving")

    def test_cancelling_the_print_dialog_writes_nothing(self):
        from PySide6.QtPrintSupport import QPrintDialog

        self.window._open_file_path(make_pdf(os.path.join(self.tmp, "d.pdf")))
        QPrintDialog.exec = lambda self: 0
        self.window._print_document()  # must simply return

    def test_printing_renders_every_selected_page(self):
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog

        path = make_pdf(os.path.join(self.tmp, "e.pdf"), pages=2)
        self.window._open_file_path(path)
        output = os.path.join(self.tmp, "print.pdf")
        original_exec = QPrintDialog.exec

        def accept(dialog):
            printer = dialog.printer()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(output)
            return 1

        QPrintDialog.exec = accept
        try:
            self.window._print_document()
        finally:
            QPrintDialog.exec = original_exec
        self.assertTrue(os.path.isfile(output))
        with fitz.open(output) as printed:
            self.assertEqual(printed.page_count, 2)


if __name__ == "__main__":
    unittest.main()
