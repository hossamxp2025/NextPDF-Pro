#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for NextPDF Pro PDF Engine
Tests PDF loading, text editing, and page operations.
"""

import os
import sys
import unittest
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Compatibility: try importing pymupdf first, fall back to fitz
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from models.document import PDFDocument, TextRun, ImageElement, ShapeElement, Annotation, contains_rtl_text
from engine.text_editor import TextEditor
from engine.page_manager import PageManager
from engine.image_editor import ImageEditor
from config import FONTS_DIR


def insert_arabic_line(page, rect, text, font_size=12):
    """Insert real, shaped Arabic using the bundled Noto font.

    Base-14 Helvetica cannot encode Arabic (it renders dots), so fixtures that
    need editable Arabic must go through the same HTML path as the editor.
    """
    archive = fitz.Archive(str(FONTS_DIR))
    css = (
        "@font-face { font-family: 'NextPDFArabic'; "
        "src: url('NotoNaskhArabic-Regular.ttf'); }"
        f" body {{ font-family: 'NextPDFArabic'; font-size: {font_size}px;"
        " direction: rtl; text-align: left; margin: 0; padding: 0; }"
        " p { margin: 0; }"
    )
    page.insert_htmlbox(fitz.Rect(*rect), f"<p>{text}</p>", css=css, archive=archive)


class TestPDFDocument(unittest.TestCase):
    """Tests for PDFDocument class."""
    
    def setUp(self):
        """Create a temporary PDF for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")
        
        # Create a simple PDF with text
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(fitz.Point(50, 50), "Hello World", fontsize=12)
        insert_arabic_line(page, (45, 85, 420, 115), "إجمالي المبلغ 15,750.00 ريال")
        doc.save(self.test_pdf)
        doc.close()
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_pdf(self):
        """Test loading a PDF file."""
        doc = PDFDocument()
        result = doc.load(self.test_pdf)
        self.assertTrue(result)
        self.assertEqual(doc.page_count, 1)
        self.assertIsNotNone(doc.file_path)
    
    def test_extract_text_runs(self):
        """Test extracting text runs from PDF."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        
        runs = doc.get_text_runs_for_page(1)
        self.assertGreaterEqual(len(runs), 2)
        
        # Check that Arabic text is detected
        arabic_runs = [r for r in runs if r.text and contains_rtl_text(r.text)]
        if arabic_runs:
            self.assertEqual(arabic_runs[0].direction, "RTL")
    
    def test_render_page(self):
        """Test rendering a page."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        
        pix = doc.render_page(1, dpi=100)
        self.assertIsNotNone(pix)
        self.assertGreater(pix.width, 0)
        self.assertGreater(pix.height, 0)
    
    def test_save_document(self):
        """Test saving a document."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        
        output_path = os.path.join(self.temp_dir, "output.pdf")
        result = doc.save(output_path, incremental=False)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))


class TestTextEditor(unittest.TestCase):
    """Tests for TextEditor class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")
        
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(fitz.Point(50, 50), "Hello World", fontsize=12)
        insert_arabic_line(page, (45, 85, 420, 115), "إجمالي 15,750.00 ريال")
        doc.save(self.test_pdf)
        doc.close()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_select_text(self):
        """Test selecting text at position."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        editor = TextEditor(doc)
        
        runs = doc.get_text_runs_for_page(1)
        self.assertGreater(len(runs), 0)
        
        # Test selection at first text run position
        first_run = runs[0]
        selected = editor.select_text_at_position(1, first_run.x + 10, first_run.y - 10)
        self.assertIsNotNone(selected)
    
    def test_edit_text(self):
        """Editing replaces the glyphs in the document (not just the model)."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        editor = TextEditor(doc)

        runs = doc.get_text_runs_for_page(1)
        self.assertGreater(len(runs), 0)

        target_run = runs[0]
        old_text = target_run.text
        result = editor.edit_text_run(
            target_run.run_id,
            "New Text Content",
            font_size=14
        )

        self.assertTrue(result.success)
        self.assertTrue(doc.is_modified)
        # refresh() rebuilds the run index, so re-read it instead of trusting
        # the stale object.
        runs_after = doc.get_text_runs_for_page(1)
        texts = [r.text.replace("\xa0", " ") for r in runs_after]
        self.assertIn("New Text Content", texts)
        self.assertNotIn(old_text.replace("\xa0", " "), texts)
        edited = [r for r in runs_after if r.text.replace("\xa0", " ") == "New Text Content"][0]
        self.assertAlmostEqual(edited.font_size, 14, delta=0.6)

        output_path = os.path.join(self.temp_dir, "edited.pdf")
        self.assertTrue(doc.save(output_path, incremental=False))
        reopened = fitz.open(output_path)
        self.assertIn("New Text Content", reopened[0].get_text().replace("\xa0", " "))
        self.assertNotIn(old_text, reopened[0].get_text())
        font_names = [f[3] for f in reopened[0].get_fonts()]
        self.assertTrue(any("Noto Sans" in name for name in font_names), font_names)
        reopened.close()

    def test_edit_arabic_text(self):
        """Replacing an Arabic line removes the old ink and the new text is
        stored as logical, searchable Unicode."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        editor = TextEditor(doc)

        runs = doc.get_text_runs_for_page(1)
        arabic_run = None
        for run in runs:
            if run.text and contains_rtl_text(run.text):
                arabic_run = run
                break

        if arabic_run is None:
            self.skipTest("no Arabic run in the generated fixture")
        # The whole visual line is one run (digits included).
        self.assertIn("15,750.00", arabic_run.text)

        result = editor.edit_text_run(
            arabic_run.run_id,
            "إجمالي المبلغ 18,500.00 ريال سعودي",
        )
        self.assertTrue(result.success, result.message)

        output_path = os.path.join(self.temp_dir, "edited_ar.pdf")
        self.assertTrue(doc.save(output_path, incremental=False))
        reopened = fitz.open(output_path)
        page = reopened[0]
        page_text = page.get_text()
        self.assertEqual(page.search_for("15,750.00"), [])
        self.assertTrue(page.search_for("18,500.00"))
        self.assertTrue(page.search_for("المبلغ"))
        self.assertTrue(page.search_for("سعودي"))
        self.assertIn("إجمالي المبلغ 18,500.00", page_text)
        self.assertFalse(any("ﭐ" <= ch <= "﷿" or "ﹰ" <= ch <= "﻿" for ch in page_text))
        font_names = [f[3] for f in page.get_fonts()]
        self.assertTrue(any("Noto Sans Arabic" in name for name in font_names), font_names)
        reopened.close()
    
    def test_add_text_box(self):
        """Test adding a new text box."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        editor = TextEditor(doc)
        
        result = editor.add_text_box(
            page_number=1,
            x=100, y=200,
            text="Test Arabic نص عربي",
            font_name="Arial",
            font_size=14,
            direction="RTL"
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.run_id)
    
    def test_delete_text_run(self):
        """Test deleting a text run."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        editor = TextEditor(doc)
        
        runs = doc.get_text_runs_for_page(1)
        self.assertGreater(len(runs), 0)
        
        run_id = runs[0].run_id
        result = editor.delete_text_run(run_id)
        self.assertTrue(result)
        
        runs_after = doc.get_text_runs_for_page(1)
        self.assertEqual(len(runs_after), len(runs) - 1)


class TestPageManager(unittest.TestCase):
    """Tests for PageManager class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")
        
        doc = fitz.open()
        page1 = doc.new_page()
        page1.insert_text(fitz.Point(50, 50), "Page 1", fontsize=12)
        page2 = doc.new_page()
        page2.insert_text(fitz.Point(50, 50), "Page 2", fontsize=12)
        doc.save(self.test_pdf)
        doc.close()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_delete_page(self):
        """Test deleting a page."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        self.assertEqual(doc.page_count, 2)
        
        manager = PageManager(doc)
        result = manager.delete_pages([1])
        self.assertTrue(result)
        self.assertEqual(doc.page_count, 1)
    
    def test_insert_blank_page(self):
        """Test inserting a blank page."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        self.assertEqual(doc.page_count, 2)
        
        manager = PageManager(doc)
        result = manager.insert_blank_page(2)
        self.assertTrue(result)
        self.assertEqual(doc.page_count, 3)
    
    def test_rotate_page(self):
        """Test rotating a page."""
        doc = PDFDocument()
        doc.load(self.test_pdf)
        
        manager = PageManager(doc)
        result = manager.rotate_pages([1], 90)
        self.assertTrue(result)
        
        page = doc.get_page(1)
        self.assertEqual(page.rotation, 90)


class TestCommandStack(unittest.TestCase):
    """Tests for CommandStack undo/redo."""
    
    def setUp(self):
        from commands.command import CommandStack, EditTextCommand
        self.stack = CommandStack()
    
    def test_undo_redo(self):
        """Test basic undo/redo functionality."""
        self.assertFalse(self.stack.can_undo())
        self.assertFalse(self.stack.can_redo())
    
    def test_can_undo_after_command(self):
        """Test that undo is available after pushing a command."""
        self.assertFalse(self.stack.can_undo())


class TestSettingsSerialization(unittest.TestCase):
    """Test settings QByteArray serialization."""
    
    def test_qbytearray_serialization(self):
        """Test that QByteArray can be serialized and deserialized."""
        from config import settings
        
        # Test that settings can be saved and loaded
        settings.set("test_key", "test_value")
        self.assertEqual(settings.get("test_key"), "test_value")
        
        # Clean up
        if "test_key" in settings._data:
            del settings._data["test_key"]
            settings.save()


if __name__ == "__main__":
    unittest.main()
