#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create test PDF files for UI testing."""

from PIL import Image
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parents[1])

# Create test image for image insertion tests
img = Image.new('RGB', (200, 150), color='#2563EB')
img.save('resources/icons/test-image.png')
print(f'Test image created: {os.path.getsize("resources/icons/test-image.png")} bytes')

# Create test PDF with Arabic text
try:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 50), "إجمالي المبلغ المستحق 15,750.00 ريال سعودي", fontsize=14)
    doc.save('test-arabic.pdf')
    doc.close()
    print(f'Arabic test PDF created: test-arabic.pdf')
except ImportError:
    print("PyMuPDF not available, skipping PDF creation")
except Exception as e:
    print(f"Error creating PDF: {e}")
