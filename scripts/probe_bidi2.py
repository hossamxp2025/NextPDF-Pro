import pymupdf as fitz
import unicodedata
import re
from src.config import FONTS_DIR

FONT = str(FONTS_DIR / "NotoNaskhArabic-Regular.ttf")
SAMPLES = [
    "مرحبا بالعالم",
    "رقم الفاتورة INV-2026-105",
    "المجموع 15,750 ريال",
    "التاريخ 14/11/2026",
    "شركة المستقبل للتقنية",
]
PRESENT = lambda c: 0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF
JUNK = lambda c: 0x80 <= ord(c) <= 0x2FF and not (0x600 <= ord(c) <= 0x6FF)

def render(text):
    doc = fitz.open()
    page = doc.new_page(width=800, height=200)
    writer = fitz.TextWriter(page.rect)
    writer.append((40, 120), text, font=fitz.Font(fontfile=FONT))
    writer.write_text(page)
    return page.get_text().strip()

def reorder(visual):
    lines = visual.split("\n")
    results = []
    for line in lines:
        rev = line[::-1]
        out, last = [], 0
        for m in re.finditer(r"[A-Za-z0-9]+(?:[./:,\-][A-Za-z0-9]+)*", rev):
            out.append(rev[last:m.start()])
            out.append(m.group()[::-1])
            last = m.end()
        out.append(rev[last:])
        results.append("".join(out))
    return "\n".join(results)

for s in SAMPLES:
    v = render(s)
    n = unicodedata.normalize("NFKC", v)
    junk = [hex(ord(c)) for c in n if JUNK(c)]
    print("source :", s)
    print("visual :", repr(v))
    print("nfkc   :", repr(n))
    print("junk   :", junk)
    print("logical:", repr(reorder(n)))
    print("MATCH  :", reorder(n) == s)
    print()
