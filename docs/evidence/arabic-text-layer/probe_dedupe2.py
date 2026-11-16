import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.engine.text_engine import TextEngine, TextStyle, parse_tounicode
from src.engine.fonts import get_font_registry

reg = get_font_registry(); eng = TextEngine(reg)
AR = "إجمالي المبلغ المستحق 15,750.00 ريال سعودي"
MX = "Mixed English and عربي together 42"
d = pymupdf.open(); p = d.new_page()
eng.insert_text(p, pymupdf.Rect(60, 60, 540, 120), AR, TextStyle(family="Amiri", size=14))
eng.insert_text(p, pymupdf.Rect(60, 140, 540, 200), MX, TextStyle(family="Amiri", size=14))
for f in p.get_fonts(full=True):
    print("font tuple:", f)
for xo in p.get_xobjects():
    print("xobject:", xo, "Font/F0 ->", d.xref_get_key(xo[0], "Resources/Font/F0"))
    print("  stream head:", d.xref_stream(xo[0])[:200])
for xref in (6, 16):
    try:
        tu = d.xref_get_key(xref, "ToUnicode"); print(xref, "ToUnicode", tu, "FontFile len:",)
        m = parse_tounicode(d.xref_stream(int(tu[1].split()[0])).decode("latin-1"))
        print("   6239 ->", repr(m.get(6239)), " 1564 ->", repr(m.get(1564)))
        df = d.xref_get_key(xref, "DescendantFonts"); print("   desc:", df)
    except Exception as e:
        print(xref, "err", e)
print("page text in-memory:", repr(p.get_text())[:120])
d.save(sys.argv[1], garbage=4, deflate=True)
r = pymupdf.open(sys.argv[1]); print("reopened:", repr(r[0].get_text())[:120])
