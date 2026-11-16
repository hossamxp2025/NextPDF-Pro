"""Measure the rebuilt Word output against the PDF it came from.

Usage: python docs/evidence/word-layout/probe_word_structure.py <statement.pdf>
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
from src.engine.conversion import export_pdf
from docx import Document
from docx.oxml.ns import qn

if len(sys.argv) < 2:
    raise SystemExit("Pass the path of a PDF to measure.")
SRC = sys.argv[1]
OUT = os.path.join(HERE, "rebuilt.docx")
data = open(SRC, "rb").read()
export_pdf(data, OUT, [1, 2], "docx_editable")
print("size:", os.path.getsize(OUT))

d = Document(OUT)
print("paragraphs:", len([p for p in d.paragraphs if p.text.strip()]),
      "(total", len(d.paragraphs), ")")
print("tables:", len(d.tables))
s = d.sections[0]
print("section: %.0f x %.0f  orient=%s" % (s.page_width.pt, s.page_height.pt, s.orientation))

for ti, t in enumerate(d.tables):
    print(f"\n== table {ti}: {len(t.rows)} rows x {len(t.columns)} cols")
    print("   bidiVisual:", t._tbl.tblPr.find(qn("w:bidiVisual")) is not None)
    print("   widths:", [round(c.width.pt, 1) if c.width else None for c in t.rows[0].cells])
    for r in list(t.rows)[:3]:
        cells = []
        for c in r.cells:
            shd = c._tc.find(qn("w:tcPr"))
            fill = None
            if shd is not None:
                node = shd.find(qn("w:shd"))
                if node is not None:
                    fill = node.get(qn("w:fill"))
            cells.append((c.text, fill))
        print("   ", cells)
    run = next((rr for cc in t.rows[0].cells for pp in cc.paragraphs for rr in pp.runs), None)
    if run:
        print("   header run font:", run.font.name, run.font.size.pt, run.bold,
              run.font.color.rgb)

print("\nparagraphs kept:")
for p in [p for p in d.paragraphs if p.text.strip()][:14]:
    r = p.runs[0]
    print("  ", repr(p.text[:46]), r.font.name, r.font.size.pt if r.font.size else None)
