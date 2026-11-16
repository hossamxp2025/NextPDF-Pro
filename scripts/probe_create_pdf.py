"""Exercise create_pdf across every supported source type and inspect the result."""
import os
import pymupdf as fitz
from pathlib import Path

from src.engine.pdf_creation import create_pdf, SUPPORTED_EXTENSIONS

OUT = Path("build/_probe_create")
OUT.mkdir(parents=True, exist_ok=True)


def make_pdf(path, pages=2, text="HELLO PDF"):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 100), f"{text} {i + 1}")
    doc.save(path)
    doc.close()


def make_png(path, color=(255, 0, 0), size=(160, 120)):
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, *size))
    pix.set_rect(pix.irect, color)
    pix.save(path)


def make_multiframe_tiff(path):
    from PIL import Image
    images = [Image.new("RGB", (120, 90), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    images[0].save(path, save_all=True, append_images=images[1:])


def make_docx(path):
    from docx import Document
    doc = Document()
    doc.add_heading("Heading One", 0)
    doc.add_paragraph("عربي فقرة للاختبار")
    doc.add_paragraph("English paragraph")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.cell(1, 0).text = "1"
    table.cell(1, 1).text = "2"
    doc.save(path)


def make_xlsx(path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "بيانات"
    ws.append(["Name", "Amount"])
    ws.append(["INV-1", 15750])
    wb.create_sheet("Second").append(["x"])
    wb.save(path)


def make_pptx(path):
    from pptx import Presentation
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Slide Title"
    prs.save(path)


cases = {}
make_pdf(OUT / "a.pdf")
make_png(OUT / "b.png")
make_multiframe_tiff(OUT / "c.tiff")
(OUT / "d.txt").write_text("سطر عربي\nEnglish line\n", encoding="utf-8")
(OUT / "e.html").write_text("<html><body><h1>Title</h1><p>مرحبا</p></body></html>", encoding="utf-8")
(OUT / "f.csv").write_text("Name,Amount\nINV-1,15750\n", encoding="utf-8")
make_docx(OUT / "g.docx")
make_xlsx(OUT / "h.xlsx")
make_pptx(OUT / "i.pptx")

for name in ("a.pdf", "b.png", "c.tiff", "d.txt", "e.html", "f.csv", "g.docx", "h.xlsx", "i.pptx"):
    source = OUT / name
    target = OUT / (name + ".out.pdf")
    before = source.read_bytes()
    try:
        accepted = create_pdf([str(source)], str(target))
        with fitz.open(target) as doc:
            text = "".join(page.get_text() for page in doc)
            print(f"{name:8} pages={doc.page_count} images={sum(len(p.get_images()) for p in doc)} "
                  f"chars={len(text.strip())} unchanged={source.read_bytes() == before}")
            print("         text:", repr(text.strip()[:80]))
    except Exception as exc:
        print(f"{name:8} ERROR {type(exc).__name__}: {exc}")
