"""Import the app with the PyInstaller-excluded modules made unavailable."""
import sys, importlib.abc, importlib.machinery
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")

BLOCKED = {"cv2", "numpy", "pytesseract", "onnxruntime", "pymupdf4llm",
           "pymupdf.layout", "scipy", "matplotlib", "tkinter"}


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name in BLOCKED or any(name.startswith(b + ".") for b in BLOCKED):
            raise ImportError(f"blocked by build excludes: {name}")
        return None


sys.meta_path.insert(0, Blocker())

import pymupdf
print("pymupdf", pymupdf.__version__)
import src.main  # noqa: F401
from src.engine.ocr_engine import OCREngine
engine = OCREngine("ara+eng")
print("ocr available:", engine.is_available(), "tessdata:", engine.tessdata)
import src.engine.conversion, src.engine.pdf_creation, src.engine.text_engine  # noqa: F401
import src.ui.main_window, src.release_verification  # noqa: F401

# Real OCR without the excluded stack.
d = pymupdf.open(); p = d.new_page(width=420, height=140)
p.insert_text((30, 80), "PACKAGE SHRINK OK", fontsize=24)
text, boxes = engine.ocr_page(p)
print("recognised:", " ".join(text.split())[:60], "| boxes:", len(boxes))
print("ALL IMPORTS AND OCR OK WITHOUT EXCLUDED MODULES")
