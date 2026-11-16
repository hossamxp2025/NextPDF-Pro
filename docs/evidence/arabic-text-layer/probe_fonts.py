"""Which bundled families give searchable Arabic after the ToUnicode rebuild?"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.engine.text_engine import TextEngine, TextStyle
from src.engine.fonts import get_font_registry

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
reg = get_font_registry()
print("families:", reg.family_names())
eng = TextEngine(reg)
AR = "إجمالي المبلغ المستحق 15,750.00 ريال سعودي"
for fam in reg.family_names():
    d = pymupdf.open(); p = d.new_page()
    res = eng.insert_text(p, pymupdf.Rect(60, 60, 540, 120), AR, TextStyle(family=fam, size=14))
    res2 = eng.insert_text(p, pymupdf.Rect(60, 140, 540, 200), "Mixed English and عربي together 42", TextStyle(family=fam, size=14))
    path = os.path.join(out, f"{fam.replace(' ', '_')}.pdf")
    d.save(path, garbage=4, deflate=True); d.close()
    r = pymupdf.open(path); pg = r[0]
    t = pg.get_text()
    pres = sum(1 for c in t if "\uFB50" <= c <= "\uFDFF" or "\uFE70" <= c <= "\uFEFF")
    hits = {q: len(pg.search_for(q)) for q in ["المبلغ", "15,750.00", "سعودي", "English", "عربي"]}
    fonts = [(f[3], f[2]) for f in pg.get_fonts()]
    print(f"{fam:18s} ok={res.success}/{res2.success} pres={pres} hits={hits} fonts={fonts}")
    print("   ", repr(t.strip())[:140])
    r.close()
