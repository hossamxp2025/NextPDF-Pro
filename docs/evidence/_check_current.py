import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from src.engine import conversion

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)

# 1) does _logical_text accept the garbage?
page = doc[0]
first = page.get_text().split("\n")[0]
print("first line:", repr(first))
try:
    out = conversion._logical_text(first)
    print("_logical_text ACCEPTED ->", repr(out))
except Exception as e:
    print("_logical_text REFUSED ->", type(e).__name__, e)

# 2) current table detection
for pno in (0, 1):
    p = doc[pno]
    try:
        tables = conversion._detected_tables(p)
        print(f"page {pno+1}: _detected_tables -> {len(tables)} table(s)", [len(t) for t in tables])
    except Exception as e:
        print(f"page {pno+1}: _detected_tables raised {type(e).__name__}: {e}")
    # raw find_tables per strategy
    for strat in ("lines", "text"):
        try:
            f = p.find_tables(strategy=strat, min_words_vertical=3, use_layout=False)
            print(f"  strategy={strat}: {len(f.tables)} tables", [(t.row_count, t.col_count) for t in f.tables])
        except Exception as e:
            print(f"  strategy={strat}: error {e}")

# 3) drawings count (are there ruling lines?)
for pno in (0, 1):
    p = doc[pno]
    print(f"page {pno+1}: drawings={len(p.get_drawings())}")

doc.close()
