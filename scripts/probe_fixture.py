import pymupdf as fitz
from src.config import FONTS_DIR

FONT = str(FONTS_DIR / "NotoNaskhArabic-Regular.ttf")
doc = fitz.open()
page = doc.new_page(width=600, height=400)
writer = fitz.TextWriter(page.rect)
writer.append((40, 90), "مرحبا بالعالم", font=fitz.Font(fontfile=FONT))
writer.append((40, 140), "INVOICE TOTAL", font=fitz.Font("helv"))
writer.write_text(page)
for block in page.get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        print([repr(s["text"]) for s in line["spans"]])
print("joined:", repr(page.get_text()))
