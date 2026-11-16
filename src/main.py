#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextPDF Pro - Professional PDF Editor for Windows
Entry point for the application.
"""

import sys
import os
import logging

# Compatibility: try importing pymupdf first, fall back to fitz
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator, QLocale, QLibraryInfo
from PySide6.QtGui import QIcon, QFont

# Package-style imports (src is a package with __init__.py)
from src.config import settings, APP_NAME, APP_VERSION, APP_ORGANIZATION, APP_DESCRIPTION, get_translator, BUILD_ID, FONTS_DIR, ICONS_DIR
from src.ui.main_window import MainWindow
from src.ui.theme_manager import ThemeManager

# Configure logging - use user-writable data directory (LOCALAPPDATA)
from src.config import LOG_FILE as CONFIG_LOG_FILE

# Try to create log directory and file; fall back to console-only if not possible
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    CONFIG_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_handlers.append(logging.FileHandler(str(CONFIG_LOG_FILE), encoding="utf-8"))
except Exception:
    # If we cannot create the log file, continue with console-only logging
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=log_handlers
)

logger = logging.getLogger("NextPDF")


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def setup_translations(app, language_code):
    """Setup application translations."""
    # Set layout direction based on language
    if language_code == "ar":
        app.setLayoutDirection(Qt.RightToLeft)
    else:
        app.setLayoutDirection(Qt.LeftToRight)
    
    logger.info(f"Translation system initialized: {language_code}")


def setup_fonts(app):
    """Setup application fonts with Arabic support."""
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)


def _run_self_test() -> int:
    """Headless end-to-end check used to validate a packaged build.

    Creates a PDF, inserts shaped Arabic and Latin text with the bundled fonts,
    saves it, reopens it and verifies the embedded font and ink.  Returns a
    process exit code and writes a report file (windowed builds have no
    console, so the file is the reliable evidence).
    """
    import tempfile

    from src.models.document import PDFDocument
    from src.engine.text_editor import TextEditor

    failures = []
    lines = []

    def check(name, condition, detail=""):
        line = f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" - {detail}" if detail else "")
        lines.append(line)
        try:
            print(line)
        except Exception:
            pass
        if not condition:
            failures.append(name)

    fonts = [p.name for p in FONTS_DIR.glob("*.ttf")] if FONTS_DIR.exists() else []
    check("bundled fonts present",
          {"NotoSansArabic-Regular.ttf", "NotoSans-Regular.ttf", "DejaVuSans.ttf",
           "NotoNaskhArabic-Regular.ttf"} <= set(fonts), str(fonts))
    try:
        import uharfbuzz, fontTools  # noqa: F401  (ToUnicode rebuild dependencies)
        check("shaping libraries importable", True)
    except Exception as exc:
        check("shaping libraries importable", False, repr(exc))
    check("icon present", (ICONS_DIR / "NextPDF-Pro.ico").exists())

    workdir = tempfile.mkdtemp(prefix="nextpdf_selftest_")
    source = os.path.join(workdir, "selftest.pdf")
    output = os.path.join(workdir, "selftest_out.pdf")
    try:
        with fitz.open() as raw:
            page = raw.new_page(width=595, height=842)
            page.insert_text(fitz.Point(60, 100), "Self test original", fontsize=14)
            raw.save(source)

        document = PDFDocument()
        check("load PDF", document.load(source), document.last_error or "")
        editor = TextEditor(document)
        result = editor.add_text(1, 300, 300, "اختبار ذاتي NextPDF", font_size=14)
        check("insert Arabic+Latin", bool(result.success), result.message)
        check("save PDF", document.save(output, incremental=False))

        with fitz.open(output) as reopened:
            page = reopened[0]
            font_names = [f[3] for f in page.get_fonts()]
            check("font embedded", any("Noto Sans Arabic" in n for n in font_names), str(font_names))
            text = page.get_text()
            check("Arabic text layer logical", "\u0627\u062E\u062A\u0628\u0627\u0631 \u0630\u0627\u062A\u064A" in text and "NextPDF" in text, repr(text[:80]))
            check("Arabic searchable", len(page.search_for("\u0630\u0627\u062A\u064A")) > 0)
            pix = page.get_pixmap(dpi=72, clip=fitz.Rect(150, 295, 300, 330))
            check("Arabic ink saved", any(b < 200 for b in pix.samples))
            check("reopen readable", "Self test original" in text)
    except Exception as exc:  # pragma: no cover - reported as failure
        check("self test exception", False, repr(exc))
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)

    lines.append(f"RESULT: {'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    report_path = os.environ.get("NEXTPDF_SELFTEST_REPORT") or os.path.join(
        tempfile.gettempdir(), "nextpdf_selftest_report.txt"
    )
    try:
        with open(report_path, "w", encoding="utf-8") as report:
            report.write("\n".join(lines) + "\n")
        try:
            print(f"Report: {report_path}")
        except Exception:
            pass
    except OSError:
        pass
    return 0 if not failures else 1


def _run_gui_smoke() -> int:
    """Create the real MainWindow and open a PDF inside the packaged app."""
    import tempfile

    lines = []
    failed = False

    def check(name, condition, detail=""):
        nonlocal failed
        line = f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" - {detail}" if detail else "")
        lines.append(line)
        try:
            print(line)
        except Exception:
            pass
        if not condition:
            failed = True

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.processEvents()
    check("window created", bool(window.windowTitle()), window.windowTitle())
    check("ribbon built", window.ribbon is not None)

    workdir = tempfile.mkdtemp(prefix="nextpdf_smoke_")
    source = os.path.join(workdir, "smoke.pdf")
    try:
        with fitz.open() as raw:
            raw.new_page(width=595, height=842)
            raw.save(source)
        check("open document", window._open_file_path(source))
        check("viewer tab", window.tab_widget.count() == 1, str(window.tab_widget.count()))
        check("viewer page", window._get_current_viewer().current_page == 1)
    finally:
        for context in list(window._contexts):
            context.document.is_modified = False
        window.hide()
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)

    lines.append(f"RESULT: {'PASS' if not failed else 'FAIL'}")
    report_path = os.environ.get("NEXTPDF_SMOKE_REPORT") or os.path.join(
        tempfile.gettempdir(), "nextpdf_smoke_report.txt"
    )
    try:
        with open(report_path, "w", encoding="utf-8") as report:
            report.write("\n".join(lines) + "\n")
    except OSError:
        pass
    return 0 if not failed else 1


def main():
    """Main entry point."""
    if "--create-job" in sys.argv:
        from src.creation_job import run
        return run(sys.argv[sys.argv.index("--create-job") + 1])
    if "--verify-release" in sys.argv:
        from src.release_verification import run
        return run(sys.argv[sys.argv.index("--verify-release") + 1])
    if "--ocr-job" in sys.argv:
        from src.ocr_job import run
        return run(sys.argv[sys.argv.index("--ocr-job") + 1])
    if "--conversion-job" in sys.argv:
        from src.conversion_job import run
        return run(sys.argv[sys.argv.index("--conversion-job") + 1])
    if "--version" in sys.argv:
        print(f"{APP_NAME} {APP_VERSION} (build {BUILD_ID})")
        return 0
    if "--self-test" in sys.argv:
        return _run_self_test()
    if "--smoke-gui" in sys.argv:
        return _run_gui_smoke()

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setOrganizationDomain("nextpdf.example.com")
    
    # Set application icon
    app_icon_path = resource_path("resources/icons/NextPDF-Pro.ico")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    
    # Setup translations
    language = settings.get("language", "ar")
    setup_translations(app, language)
    setup_fonts(app)
    
    # Apply modern theme
    theme_manager = ThemeManager(app)
    theme_manager.set_language(language)
    theme_manager.apply_theme()
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info(f"{APP_NAME} v{APP_VERSION} (Build {BUILD_ID}) started")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main())
