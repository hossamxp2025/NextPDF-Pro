import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from src.engine import conversion

doc = fitz.open("docs/evidence/_fixture_table.pdf")
page = doc[0]
repair = conversion._TextRepair(doc)
print("map fonts:", list(repair.maps_for(page)))

finder = page.find_tables(use_layout=False, strategy="text", min_words_vertical=3)
t = finder.tables[0]
rects = [fitz.Rect(r.bbox) for r in t.rows]
print("row rects:")
for i, r in enumerate(rects):
    print(f"  {i}: y {r.y0:.1f}-{r.y1:.1f} centre {(r.y0+r.y1)/2:.1f}")

raw = []
for b in page.get_text("rawdict")["blocks"]:
    if b.get("type") != 0: continue
    for line in b.get("lines", []):
        for span in line["spans"]:
            for ch in span["chars"]:
                ch["font"] = span["font"]; raw.append(ch)

centres = [(r.y0+r.y1)/2 for r in rects]
def owner(ch):
    cy = (ch["bbox"][1]+ch["bbox"][3])/2
    best = None
    for i,(rect,c) in enumerate(zip(rects, centres)):
        if rect.y0-1 <= cy <= rect.y1+1:
            d = abs(c-cy)
            if best is None or d < best[0]: best = (d,i)
    return best[1] if best else None

for ch in raw[:12]:
    print("char", repr(ch["c"]), "cy", round((ch["bbox"][1]+ch["bbox"][3])/2,1), "owner", owner(ch))

print("\n_detected_tables:")
tables = conversion._detected_tables(page, repair)
for tb in tables:
    print("rows", len(tb), "cols", len(tb[0]))
    for row in tb:
        print("  ", row)
doc.close()
