import pymupdf as fitz
import unicodedata
from src.config import FONTS_DIR
import re

SAMPLES = [
    "مرحبا بالعالم",
    "رقم الفاتورة INV-2026-105",
    "المجموع 15,750 ريال",
    "التاريخ 14/11/2026",
    "شركة المستقبل للتقنية",
]

def extract(text):
    doc = fitz.open()
    page = doc.new_page(width=900, height=300)
    page.insert_htmlbox(
        fitz.Rect(20, 20, 880, 280),
        f"<p dir='rtl' style='font-size:22px'>{text}</p>",
        css="@font-face {font-family:A;src:url('NotoNaskhArabic-Regular.ttf');} body{font-family:A;}",
        archive=fitz.Archive(str(FONTS_DIR)),
    )
    return page.get_text().strip()

ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

def to_logical(visual):
    norm = unicodedata.normalize("NFKC", visual)
    norm = "".join(c for c in norm if ord(c) >= 32)
    # Reverse whole line (RTL paragraph), then restore LTR runs.
    rev = norm[::-1]
    # Find LTR tokens (ASCII letters/digits plus internal - / . , :) in reversed string
    tokens = list(re.finditer(r"[A-Za-z0-9]+(?:[./:,\-][A-Za-z0-9]+)*", rev))
    out = []
    last = 0
    for m in tokens:
        out.append(rev[last:m.start()])
        out.append(m.group()[::-1])
        last = m.end()
    out.append(rev[last:])
    return "".join(out)

for s in SAMPLES:
    v = extract(s)
    l = to_logical(v)
    print("source:", s)
    print("visual:", repr(v))
    print("logical:", repr(l))
    print("MATCH:", l == s)
    print()
