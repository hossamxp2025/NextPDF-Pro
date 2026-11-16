import pymupdf as fitz
from src.config import FONTS_DIR

FONT = str(FONTS_DIR / "NotoNaskhArabic-Regular.ttf")

def probe(label, builder):
    doc = fitz.open()
    page = doc.new_page(width=700, height=200)
    builder(page)
    print(label, "=>", repr(page.get_text().strip()))

probe("textwriter", lambda p: fitz.TextWriter(p.rect).append(
    (40, 120), "مرحبا بالعالم", font=fitz.Font(fontfile=FONT)) or None)

def tw(p):
    writer = fitz.TextWriter(p.rect)
    writer.append((40, 120), "مرحبا بالعالم", font=fitz.Font(fontfile=FONT))
    writer.write_text(p)
probe("textwriter2", tw)

def raw(p):
    font = fitz.Font(fontfile=FONT)
    p.insert_text((40, 120), "مرحبا بالعالم", fontname="X0", fontfile=FONT, render_mode=3)
probe("insert_text-render3", raw)
