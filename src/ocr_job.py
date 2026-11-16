"""Private subprocess entry: OCR never shares GUI state.

Inputs/outputs are confined to the parent-created temporary job directory.
No PDF text or user paths are interpreted as shell commands.  Recognition
uses the Tesseract linked into MuPDF, so no external process is launched and
no DLL directory has to be registered.
"""
import json
import os
import sys
from pathlib import Path
from src.models.document import PDFDocument
from src.engine.ocr_engine import OCREngine, find_tessdata
from src.job_result import guarded_run, progress

def _run(request_path):
    # يستفيد منه أي كود طرف ثالث يقرأ المتغير؛ المحرك نفسه يمرر المسار صراحةً.
    bundled_tessdata = find_tessdata()
    if bundled_tessdata:
        os.environ["TESSDATA_PREFIX"] = bundled_tessdata

    request = Path(request_path).resolve()
    options = json.loads(request.read_text(encoding="utf-8"))
    if options["language"] not in {"ara", "eng", "ara+eng"}:
        raise ValueError("Unsupported OCR language")
    if options["format"] not in {"pdf", "txt"}:
        raise ValueError("Unsupported OCR output")
    document = PDFDocument()
    if not document.load(str(request.parent / "input.pdf")):
        raise ValueError("Cannot read OCR input")
    try:
        pages = options["pages"]
        if not pages or len(pages) != len(set(pages)) or any(
            type(n) is not int or not 1 <= n <= document.page_count for n in pages
        ):
            raise ValueError("Invalid OCR page selection")
        engine = OCREngine(options["language"])
        if not engine.is_available():
            raise RuntimeError("OCR engine is unavailable")
        output = request.parent / ("output." + options["format"])
        if options["format"] == "pdf":
            if not engine.create_searchable_pdf(document, str(output), pages=pages,
                                                 progress_callback=progress):
                raise RuntimeError("OCR PDF validation failed")
        else:
            texts = []
            for i, number in enumerate(pages, 1):
                page = document.get_page(number)
                text = page.get_text()
                if not text.strip():
                    text, _ = engine.ocr_page(page)
                if not text.strip():
                    raise RuntimeError("OCR returned no readable text")
                texts.append(text)
                progress(i, len(pages))
            output.write_text("\n\f\n".join(texts), encoding="utf-8")
    finally:
        document.close()
    return 0


def run(request_path):
    return guarded_run(request_path, _run)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
