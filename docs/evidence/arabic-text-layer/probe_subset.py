"""No dedupe: measure font bloat and whether subset_fonts keeps searchability."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.engine.text_engine import TextEngine, TextStyle
from src.engine.fonts import get_font_registry

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
reg = get_font_registry(); eng = TextEngine(reg)
eng._dedupe_fonts = lambda page, fb: None
texts = ["إجمالي المبلغ المستحق 15,750.00 ريال سعودي", "Mixed English and عربي together 42",
         "الفاتورة رقم 2026/0042", "تاريخ الاستحقاق: 30 نوفمبر", "Thank you — شكراً لتعاملكم"]
d = pymupdf.open(); p = d.new_page()
for i, t in enumerate(texts):
    eng.insert_text(p, pymupdf.Rect(60, 60 + i * 70, 540, 120 + i * 70), t, TextStyle(family="Amiri", size=14))
eng.insert_text(p, pymupdf.Rect(60, 420, 540, 480), "DejaVu line: نص تجريبي", TextStyle(family="DejaVu Sans", size=14))
fonts = p.get_fonts(full=True)
print("fonts:", [(f[0], f[3]) for f in fonts])
for f in fonts:
    desc = d.xref_get_key(f[0], "DescendantFonts")
    dx = int(desc[1].strip("[]").split()[0])
    fd = d.xref_get_key(dx, "FontDescriptor"); fdx = int(fd[1].split()[0])
    ff = d.xref_get_key(fdx, "FontFile2")
    if ff[0] == "xref":
        print("  fontfile", f[0], "len", len(d.xref_stream(int(ff[1].split()[0]))))

def check(path, label):
    r = pymupdf.open(path); pg = r[0]
    t = pg.get_text()
    bad = sum(1 for c in t if ord(c) < 32 and c not in "\n\t")
    hits = {q: len(pg.search_for(q)) for q in ["المبلغ", "English", "عربي", "الفاتورة", "نوفمبر", "شكراً", "تجريبي"]}
    print(f"{label}: size={os.path.getsize(path)} fonts={len(pg.get_fonts())} ctrl_chars={bad} hits={hits}")
    print("   ", repr(t.strip())[:200])
    r.close()

p1 = os.path.join(out, "plain.pdf"); d.save(p1, garbage=4, deflate=True); check(p1, "plain")
try:
    rc = d.subset_fonts(verbose=False)
    print("subset_fonts ->", rc)
    p2 = os.path.join(out, "subset.pdf"); d.save(p2, garbage=4, deflate=True); check(p2, "subset")
    pymupdf.open(p2)[0].get_pixmap(dpi=90, clip=pymupdf.Rect(50, 50, 550, 490)).save(os.path.join(out, "subset.png"))
except Exception as e:
    print("subset_fonts failed:", repr(e))
