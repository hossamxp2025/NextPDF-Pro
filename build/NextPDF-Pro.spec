# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for NextPDF Pro 1.1.0 (single-file Windows build)."""

import os

from PyInstaller.utils.hooks import collect_submodules

import pymupdf as fitz

APP_NAME = "NextPDF-Pro"

# In a spec file PyInstaller sets SPECPATH; fall back to this file's directory.
SPEC_DIR = os.path.abspath(globals().get("SPECPATH") or os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(SPEC_DIR)

# PyMuPDF's own PyInstaller hook collects the MuPDF shared libraries into
# pymupdf/.  An earlier explicit copy here placed a second copy at the archive
# root, which shipped mupdfcpp64.dll twice (25 MB wasted).  The duplicate is
# gone; the packaged --self-test verifies the libraries are still present.
pymupdf_binaries = []
fitz_path = os.path.dirname(fitz.__file__)

datas = [
    (os.path.join(PROJECT_ROOT, "resources", "icons"), "resources/icons"),
    (os.path.join(PROJECT_ROOT, "resources", "fonts"), "resources/fonts"),
    (os.path.join(PROJECT_ROOT, "resources", "translations"), "resources/translations"),
    # Language data only: recognition runs on the Tesseract linked into MuPDF,
    # so no tesseract.exe or its dependency DLLs are shipped.
    (os.path.join(PROJECT_ROOT, "resources", "tessdata"), "resources/tessdata"),
]

# Submodules that drag heavy optional stacks the application never calls:
# pymupdf.layout pulls onnxruntime and its model (~45 MB).
pymupdf_modules = [m for m in collect_submodules("pymupdf")
                   if not m.startswith("pymupdf.layout")]

a = Analysis(
    [os.path.join(PROJECT_ROOT, "src", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=pymupdf_binaries,
    datas=datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtPrintSupport",
        "PySide6.QtSvg",
        "pymupdf",
        "fitz",
        "PIL",
        "openpyxl",
        "docx",
        "uharfbuzz",
        "fontTools",
        "fontTools.ttLib",
        "fontTools.subset",
    ] + pymupdf_modules + collect_submodules("fontTools"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Nothing in src imports these; they were pulled in by the old OCR path
    # (pytesseract/OpenCV) and by pymupdf.layout, and cost ~270 MB unpacked.
    excludes=[
        "cv2",
        "numpy",
        "pytesseract",
        "onnxruntime",
        "pymupdf4llm",
        "pymupdf.layout",
        "scipy",
        "matplotlib",
        "tkinter",
    ],
    noarchive=False,
)

# The pymupdf hook also copies pymupdf/layout's ONNX models (26 MB) as data
# files, which `excludes` does not touch.  Nothing loads them once the layout
# module itself is excluded.
_DROP_DATA_PREFIXES = ("pymupdf/layout/",)
a.datas = [item for item in a.datas
           if not item[0].replace("\\", "/").startswith(_DROP_DATA_PREFIXES)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, "resources", "icons", "NextPDF-Pro.ico"),
    version=os.path.join(SPEC_DIR, "version_info.txt"),
)
