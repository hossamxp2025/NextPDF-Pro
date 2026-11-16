"""Build a PDF from user documents and images.

This is deliberately explicit about its engine: PDFs are merged, images are
placed at their natural aspect ratio, and text-bearing formats are reflowed
through MuPDF's HTML story engine. Reflow is not a page-faithful Office render.
"""
import html
import io
import os
import tempfile
from pathlib import Path

import pymupdf as fitz

from src.config import FONTS_DIR

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff",
                        ".webp", ".txt", ".md", ".html", ".htm", ".csv",
                        ".docx", ".xlsx", ".pptx"}

# Noto Sans Arabic is the only bundled Arabic face whose text layer can be
# rebuilt reliably (see src/engine/fonts.py); Latin glyphs it lacks fall back
# to MuPDF's built-in fonts, whose own ToUnicode maps are correct.
CSS = """
@font-face {font-family: Arabic; src: url('NotoSansArabic-Regular.ttf'); font-weight: normal;}
@font-face {font-family: Arabic; src: url('NotoSansArabic-Bold.ttf'); font-weight: bold;}
body {font-family: Arabic, sans-serif; font-size: 11pt; color: #111111;}
h1, h2, h3 {font-family: Arabic, sans-serif;}
table {border-collapse: collapse; width: 100%;}
td, th {border: 1px solid #888888; padding: 4px; font-size: 10pt;}
pre {white-space: pre-wrap; font-family: Arabic, sans-serif;}
[dir='rtl'] {text-align: right;}
"""

_TAG_RE = __import__("re").compile(r"<[^>]+>")


def _is_arabic(text):
    return any("\u0600" <= char <= "\u06ff" for char in text or "")


def _direction(text):
    return "rtl" if _is_arabic(text) else "ltr"


def _escape(text):
    return html.escape(text or "")


def _image_archive(archive, prefix, blob):
    name = f"{prefix}.png"
    archive.add(blob, name)
    return name


def _pdf_from_html(markup, archive=None):
    """Render HTML into a one-or-more-page PDF and return its bytes."""
    story = fitz.Story(html=markup, user_css=CSS, archive=archive or fitz.Archive(str(FONTS_DIR)))
    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (48, 48, -48, -48)
    more = True
    pages = 0
    while more and pages < 2000:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
        pages += 1
    writer.close()
    return _repair_text_layer(buffer.getvalue(), markup)


def _repair_text_layer(pdf_bytes, markup):
    """Rebuild the ToUnicode maps Story wrote so the Arabic is searchable.

    The markup's visible text (tags stripped, entities decoded) refines the
    ligature clusters; the font's own tables cover everything else.
    """
    from src.engine.text_engine import get_text_engine
    texts = [html.unescape(_TAG_RE.sub(" ", markup))]
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        get_text_engine().repair_text_layer(doc, texts)
        return doc.tobytes(garbage=1)
    finally:
        doc.close()


def _image_pdf(path, progress):
    """One page per image frame; TIFF and GIF keep every frame."""
    extension = os.path.splitext(path)[1].lower()
    output = fitz.open()
    try:
        if extension in {".tif", ".tiff", ".gif"}:
            from PIL import Image
            with Image.open(path) as image:
                total = max(1, getattr(image, "n_frames", 1))
                for index in range(total):
                    image.seek(index)
                    buffer = io.BytesIO()
                    image.convert("RGBA").save(buffer, format="PNG")
                    _place_image(output, buffer.getvalue())
                    if progress:
                        progress(index + 1, total)
        else:
            _place_image(output, Path(path).read_bytes())
            if progress:
                progress(1, 1)
        return output.tobytes()
    finally:
        output.close()


def _place_image(output, blob):
    """Place an image at its pixel size (96 dpi) inside an A4-or-larger page."""
    try:
        pix = fitz.Pixmap(blob)
    except (ValueError, RuntimeError):
        from PIL import Image
        buffer = io.BytesIO()
        with Image.open(io.BytesIO(blob)) as image:
            image.convert("RGBA").save(buffer, format="PNG")
        blob = buffer.getvalue()
        pix = fitz.Pixmap(blob)
    width = pix.width * 72 / 96
    height = pix.height * 72 / 96
    scale = min(1.0, 523 / max(width, 1), 740 / max(height, 1))
    rect = fitz.Rect(36, 36, 36 + width * scale, 36 + height * scale)
    page = output.new_page(width=max(595, rect.x1 + 36), height=max(842, rect.y1 + 36))
    page.insert_image(rect, stream=blob, keep_proportion=True)


def _text_pdf(path, progress):
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1256"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", "replace")
    paragraphs = "".join(
        f"<p dir='{_direction(line)}'>{_escape(line) if line.strip() else '&nbsp;'}</p>"
        for line in text.splitlines()
    )
    if progress:
        progress(1, 1)
    return _pdf_from_html(f"<div>{paragraphs}</div>")


def _html_pdf(path, progress):
    markup = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    if progress:
        progress(1, 1)
    return _pdf_from_html(markup)


def _docx_pdf(path, progress):
    from docx import Document
    document = Document(path)
    archive = fitz.Archive(str(FONTS_DIR))
    chunks = []
    image_index = 0
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = "h2" if (paragraph.style and "Heading" in paragraph.style.name) else "p"
        chunks.append(f"<{style} dir='{_direction(text)}'>{_escape(text)}</{style}>")
    for shape in document.inline_shapes:
        try:
            rid = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            blob = document.part.related_parts[rid].blob
        except (KeyError, AttributeError):
            continue
        name = _image_archive(archive, f"docx{image_index}", blob)
        chunks.append(f"<p><img src='{name}' style='max-width:100%'/></p>")
        image_index += 1
    for table in document.tables:
        rows = []
        for row in table.rows:
            cells = "".join(f"<td>{_escape(cell.text)}</td>" for cell in row.cells)
            rows.append(f"<tr>{cells}</tr>")
        chunks.append(f"<table>{''.join(rows)}</table>")
    if progress:
        progress(1, 1)
    return _pdf_from_html(f"<div>{''.join(chunks)}</div>", archive)


def _xlsx_pdf(path, progress):
    from openpyxl import load_workbook
    book = load_workbook(path, data_only=True, read_only=True)
    chunks = []
    try:
        for index, sheet in enumerate(book.worksheets, 1):
            chunks.append(f"<h2 dir='{_direction(sheet.title)}'>{_escape(sheet.title)}</h2>")
            rows = []
            for row in sheet.iter_rows(values_only=True):
                cells = "".join(f"<td>{_escape('' if value is None else str(value))}</td>" for value in row)
                rows.append(f"<tr>{cells}</tr>")
            chunks.append(f"<table>{''.join(rows)}</table>")
            if progress:
                progress(index, len(book.worksheets))
    finally:
        book.close()
    return _pdf_from_html(f"<div>{''.join(chunks)}</div>")


def _pptx_pdf(path, progress):
    from pptx import Presentation
    presentation = Presentation(path)
    archive = fitz.Archive(str(FONTS_DIR))
    chunks = []
    image_index = 0
    for index, slide in enumerate(presentation.slides, 1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                texts.append(shape.text_frame.text)
            if shape.shape_type == 13 and hasattr(shape, "image"):
                name = _image_archive(archive, f"pptx{image_index}", shape.image.blob)
                chunks.append(f"<p><img src='{name}' style='max-width:100%'/></p>")
                image_index += 1
        joined = "\n".join(texts)
        chunks.append(f"<h2 dir='{_direction(joined)}'>{_escape('Slide')} {index}</h2>")
        for text in texts:
            for line in text.splitlines():
                chunks.append(f"<p dir='{_direction(line)}'>{_escape(line)}</p>")
        if progress:
            progress(index, len(presentation.slides))
    return _pdf_from_html(f"<div>{''.join(chunks)}</div>", archive)


def create_pdf(paths, target, progress=None):
    """Create ``target`` from ``paths``; returns the list of accepted sources."""
    if not paths:
        raise ValueError("No source files were selected")
    merged = fitz.open()
    accepted = []
    try:
        for index, path in enumerate(paths, 1):
            extension = os.path.splitext(path)[1].lower()
            if extension not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Unsupported source format: {extension}")
            if extension == ".pdf":
                with fitz.open(path) as source:
                    if source.is_encrypted and not source.authenticate(""):
                        raise ValueError("Encrypted PDF requires a password")
                    merged.insert_pdf(source)
            elif extension in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}:
                with fitz.open(stream=_image_pdf(path, progress), filetype="pdf") as part:
                    merged.insert_pdf(part)
            elif extension in {".txt", ".md"}:
                with fitz.open(stream=_text_pdf(path, progress), filetype="pdf") as part:
                    merged.insert_pdf(part)
            elif extension in {".html", ".htm"}:
                with fitz.open(stream=_html_pdf(path, progress), filetype="pdf") as part:
                    merged.insert_pdf(part)
            elif extension == ".csv":
                import csv
                rows = list(csv.reader(Path(path).read_text(encoding="utf-8-sig").splitlines()))
                markup = "<table>" + "".join(
                    "<tr>" + "".join(f"<td>{_escape(cell)}</td>" for cell in row) + "</tr>"
                    for row in rows) + "</table>"
                with fitz.open(stream=_pdf_from_html(markup), filetype="pdf") as part:
                    merged.insert_pdf(part)
            elif extension == ".docx":
                with fitz.open(stream=_docx_pdf(path, progress), filetype="pdf") as part:
                    merged.insert_pdf(part)
            elif extension == ".xlsx":
                with fitz.open(stream=_xlsx_pdf(path, progress), filetype="pdf") as part:
                    merged.insert_pdf(part)
            elif extension == ".pptx":
                with fitz.open(stream=_pptx_pdf(path, progress), filetype="pdf") as part:
                    merged.insert_pdf(part)
            accepted.append(path)
            if progress:
                progress(index, len(paths))
        if merged.page_count == 0:
            raise ValueError("The selected sources produced no pages")
        merged.set_metadata({"producer": "NextPDF Pro", "creator": "NextPDF Pro"})
        try:
            merged.subset_fonts()
        except Exception:
            pass
        # Publish atomically: a failed run must never leave a partial PDF behind.
        staging = tempfile.NamedTemporaryFile(
            prefix=".nextpdf-create-", suffix=".pdf",
            dir=os.path.dirname(os.path.abspath(target)), delete=False)
        staging.close()
        try:
            merged.save(staging.name, garbage=3, deflate=True)
            os.replace(staging.name, target)
        finally:
            if os.path.exists(staging.name):
                os.unlink(staging.name)
    finally:
        merged.close()
    return accepted
