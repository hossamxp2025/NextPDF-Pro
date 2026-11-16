#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Page operations: insert, delete, rotate, move, extract, merge and split."""

import logging
import os
from typing import List

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from src.models.document import PDFDocument

logger = logging.getLogger("NextPDF")


class PageManager:
    """Manages PDF page operations for one document."""

    def __init__(self, document: PDFDocument):
        self.doc = document

    def merge_pdfs(self, output_path: str, source_paths: List[str]) -> bool:
        """Merge multiple PDF files into one output file."""
        if not source_paths:
            return False
        merged = None
        try:
            merged = fitz.open()
            for path in source_paths:
                if not os.path.exists(path):
                    logger.error("Merge source missing: %s", path)
                    continue
                src = fitz.open(path)
                try:
                    if getattr(src, "needs_pass", False):
                        logger.error("Skipping encrypted PDF: %s", path)
                        continue
                    merged.insert_pdf(src)
                finally:
                    src.close()
            if merged.page_count == 0:
                return False
            os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
            merged.save(output_path, garbage=4, deflate=True)
            logger.info("Merged %d PDFs into %s", len(source_paths), output_path)
            return True
        except Exception:
            logger.exception("Failed to merge PDFs")
            return False
        finally:
            if merged is not None:
                merged.close()

    def split_pdf(self, output_dir: str, pages_per_file: int = 1) -> List[str]:
        output_paths: List[str] = []
        if self.doc.doc is None or pages_per_file < 1:
            return output_paths
        try:
            os.makedirs(output_dir, exist_ok=True)
            total = self.doc.page_count
            for start in range(0, total, pages_per_file):
                end = min(start + pages_per_file, total)
                new_doc = fitz.open()
                try:
                    new_doc.insert_pdf(self.doc.doc, from_page=start, to_page=end - 1)
                    output_path = os.path.join(output_dir, f"split_{start + 1}_{end}.pdf")
                    new_doc.save(output_path, garbage=4, deflate=True)
                    output_paths.append(output_path)
                finally:
                    new_doc.close()
            return output_paths
        except Exception:
            logger.exception("Failed to split PDF")
            return output_paths

    def extract_pages(self, output_path: str, page_numbers: List[int]) -> bool:
        if self.doc.doc is None or not page_numbers:
            return False
        new_doc = None
        try:
            new_doc = fitz.open()
            for page_num in page_numbers:
                if 1 <= page_num <= self.doc.page_count:
                    new_doc.insert_pdf(
                        self.doc.doc, from_page=page_num - 1, to_page=page_num - 1
                    )
            if new_doc.page_count == 0:
                return False
            os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
            new_doc.save(output_path, garbage=4, deflate=True)
            logger.info("Extracted %d pages to %s", len(page_numbers), output_path)
            return True
        except Exception:
            logger.exception("Failed to extract pages")
            return False
        finally:
            if new_doc is not None:
                new_doc.close()

    def delete_pages(self, page_numbers: List[int]) -> bool:
        if self.doc.doc is None:
            return False
        if len(page_numbers) >= self.doc.page_count:
            logger.warning("Refusing to delete every page")
            return False
        try:
            for page_num in sorted(set(page_numbers), reverse=True):
                if 1 <= page_num <= self.doc.page_count:
                    self.doc.delete_page(page_num)
            return self.doc.page_count > 0
        except Exception:
            logger.exception("Failed to delete pages")
            return False

    def insert_page(self, position: int, source_pdf_path: str, source_page: int = 1) -> bool:
        if self.doc.doc is None or not os.path.exists(source_pdf_path):
            return False
        src_doc = None
        try:
            src_doc = fitz.open(source_pdf_path)
            if getattr(src_doc, "needs_pass", False):
                return False
            index = max(0, min(position - 1, self.doc.page_count))
            self.doc.doc.insert_pdf(
                src_doc, from_page=source_page - 1, to_page=source_page - 1,
                start_at=index,
            )
            self.doc.refresh()
            self.doc.is_modified = True
            return True
        except Exception:
            logger.exception("Failed to insert page")
            return False
        finally:
            if src_doc is not None:
                src_doc.close()

    def insert_blank_page(self, position: int, width: float = 595, height: float = 842) -> bool:
        if self.doc.doc is None:
            return False
        try:
            index = max(0, min(position - 1, self.doc.page_count))
            self.doc.doc.new_page(width=width, height=height, pno=index)
            self.doc.refresh()
            self.doc.is_modified = True
            return True
        except Exception:
            logger.exception("Failed to insert blank page")
            return False

    def rotate_pages(self, page_numbers: List[int], degrees: int) -> bool:
        if self.doc.doc is None:
            return False
        try:
            for page_num in page_numbers:
                self.doc.rotate_page(page_num, degrees)
            self.doc.refresh()
            return True
        except Exception:
            logger.exception("Failed to rotate pages")
            return False

    def reorder_pages(self, new_order: List[int]) -> bool:
        if self.doc.doc is None or sorted(new_order) != list(range(1, self.doc.page_count + 1)):
            return False
        try:
            current_order = list(range(1, self.doc.page_count + 1))
            for target_pos, page_num in enumerate(new_order):
                current_pos = current_order.index(page_num)
                if current_pos != target_pos:
                    self.doc.move_page(current_pos, target_pos)
                    current_order.pop(current_pos)
                    current_order.insert(target_pos, page_num)
            self.doc.refresh()
            self.doc.is_modified = True
            return True
        except Exception:
            logger.exception("Failed to reorder pages")
            return False

    def crop_pages(self, page_numbers: List[int], rect) -> bool:
        if self.doc.doc is None:
            return False
        try:
            for page_num in page_numbers:
                page = self.doc.get_page(page_num)
                if page is not None:
                    page.set_cropbox(rect)
            self.doc.is_modified = True
            return True
        except Exception:
            logger.exception("Failed to crop pages")
            return False
