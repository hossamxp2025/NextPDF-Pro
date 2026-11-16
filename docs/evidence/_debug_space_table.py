import sys, os, io
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from fontTools.ttLib import TTFont
from src.engine import conversion

# space gid check
doc = fitz.open("docs/evidence/_fixture_broken.pdf")
page = doc[0]
f = page.get_fonts(full=True)[0]
buf = doc.extract_font(f[0])[3]
m = conversion._gid_to_unicode(buf)
print("gid 0..8 ->", {k: m.get(k) for k in range(9)})
print("gid 3 in map:", 3 in m)
doc.close()

# font cmap for space
tt = TTFont("resources/fonts/NotoSansArabic-Regular.ttf", lazy=True)
cmap = tt.getBestCmap()
order = tt.getGlyphOrder()
gid_of = {n:i for i,n in enumerate(order)}
for code in (32, 3, 0x0643, 0x0634, 0x0641):
    name = cmap.get(code)
    print(f"U+{code:04X} -> glyph {name!r} gid {gid_of.get(name)}")
tt.close()

# variant table without shading
import pymupdf as fitz2
def make(path, shade):
    doc = fitz2.open(); page = doc.new_page(width=595, height=400)
    headers = ["Date", "Description", "Amount"]
    rows = [["2026-11-01","Opening balance","1,200.00"],
            ["2026-11-02","Groceries","85.50"],
            ["2026-11-03","Salary","3,000.00"],
            ["2026-11-04","Fuel","120.75"]]
    cols=[40,200,380]; top=60; lh=28
    if shade:
        for i in range(len(rows)+1):
            y0=top+i*lh
            if i%2==0:
                page.draw_rect(fitz2.Rect(30,y0,560,y0+lh), color=None, fill=(0.92,0.92,0.92), width=0)
    for c,h in zip(cols,headers): page.insert_text((c, top+19), h, fontsize=12)
    for ri,row in enumerate(rows,1):
        for c,v in zip(cols,row): page.insert_text((c, top+ri*lh+19), v, fontsize=11)
    doc.save(path); doc.close()

for shade in (False, True):
    p = f"docs/evidence/_tbl_{'shade' if shade else 'plain'}.pdf"
    make(p, shade)
    d = fitz2.open(p); pg = d[0]
    for strat in ({"strategy":"text"}, {"horizontal_strategy":"text","vertical_strategy":"lines"}):
        try:
            ft = pg.find_tables(use_layout=False, min_words_vertical=3, **strat)
        except Exception as e:
            print("err", e); continue
        print(f"shade={shade} {strat}: tables={len(ft.tables)}", [(t.row_count,t.col_count) for t in ft.tables])
    d.close()
