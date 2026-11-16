#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create a test PDF file with Arabic and English text for manual testing.
"""

import os
import sys
import fitz

def create_test_pdf(output_path="test_arabic.pdf"):
    """Create a test PDF with Arabic and English content."""
    doc = fitz.open()
    
    # Page 1: Arabic and English text
    page = doc.new_page()
    
    # English text
    page.insert_text(fitz.Point(50, 50), "Hello World", fontsize=14)
    page.insert_text(fitz.Point(50, 80), "Total Amount: 15,750.00 USD", fontsize=12)
    
    # Arabic text (the mandatory test case)
    page.insert_text(fitz.Point(50, 120), "إجمالي المبلغ المستحق 15,750.00 ريال سعودي", fontsize=14)
    page.insert_text(fitz.Point(50, 150), "تاريخ الفاتورة: 12 نوفمبر 2024", fontsize=12)
    
    # Mixed Arabic/English
    page.insert_text(fitz.Point(50, 180), "رقم الفاتورة: INV-2024-001", fontsize=12)
    
    # Page 2: More content
    page2 = doc.new_page()
    page2.insert_text(fitz.Point(50, 50), "第二页 / صفحة ثانية", fontsize=14)
    page2.insert_text(fitz.Point(50, 80), "محتوى إضافي للاختبار", fontsize=12)
    
    doc.save(output_path)
    doc.close()
    
    print(f"Test PDF created: {output_path}")
    print(f"Pages: 2")
    print(f"Test case: 'إجمالي المبلغ المستحق 15,750.00 ريال سعودي'")
    print(f"Change to: 'إجمالي المبلغ المستحق 18,500.00 ريال سعودي'")


if __name__ == "__main__":
    create_test_pdf()