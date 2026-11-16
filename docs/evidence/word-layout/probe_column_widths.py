"""Compare each column's detected boundary with the widest text inside it.

Usage: python docs/evidence/word-layout/probe_column_widths.py <statement.pdf>
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
import pymupdf as fitz
from src.engine.conversion import _detected_tables, _TextRepair, _median

if len(sys.argv) < 2:
    raise SystemExit("Pass the path of a PDF to measure.")
doc = fitz.open(sys.argv[1])
page = doc[0]
t = _detected_tables(page, _TextRepair(doc))[0]
cols = max(len(r) for r in t)
print("usable width (page-72):", round(page.rect.width - 72, 1))
print(f"{'col':>3} {'measured':>9} {'content':>8} {'slack':>7}  sample")
tm = tc = 0.0
for c in range(cols):
    measured = _median([fitz.Rect(r[c]).width for r in t.cell_rects
                        if c < len(r) and r[c] is not None])
    content = max([b[c][1] - b[c][0] for b in t.cell_bounds
                   if c < len(b) and b[c] is not None] or [0])
    tm += measured
    tc += content
    sample = max((row[c] for row in t if c < len(row)), key=len, default="")
    print(f"{c:>3} {measured:9.1f} {content:8.1f} {measured-content:7.1f}  {sample[:22]}")
print("totals: measured", round(tm, 1), " content", round(tc, 1))
doc.close()
