"""Anchoring after the fix: add at a point, and replace a line in place."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.models.document import PDFDocument
from src.engine.text_editor import TextEditor

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
src = os.path.join(out, "src.pdf")
with pymupdf.open() as d:
    d.new_page().insert_text((60, 80), "Invoice INV-2026/0042", fontsize=12); d.save(src)

CASES = [("إجمالي المبلغ المستحق 15,750.00 ريال سعودي", 400.0, 250.0, "rtl"),
         ("Added by NextPDF 2026", 300.0, 300.0, "ltr"),
         ("مرحبا بالعالم 15,750 ريال", 400.0, 250.0, "rtl")]
for text, cx, cy, d_ in CASES:
    doc = PDFDocument(); doc.load(src); ed = TextEditor(doc)
    r = ed.add_text(1, cx, cy, text, font_size=14)
    assert r.success, r.message
    p = os.path.join(out, "add.pdf"); doc.save(p)
    pg = pymupdf.open(p)[0]
    sp = [s for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]
          if text.split()[0][:3] in s["text"] or any("\u0600" <= c <= "\u06ff" for c in s["text"]) == (d_ == "rtl")]
    sp = [s for s in sp if s["text"].strip()]
    anchor = max(s["bbox"][2] for s in sp) if d_ == "rtl" else min(s["bbox"][0] for s in sp)
    top = min(s["bbox"][1] for s in sp)
    print(f"add {d_}: anchor_x={anchor:7.2f} (want {cx})  dx={anchor-cx:+.2f} | top={top:7.2f} (want {cy}) dy={top-cy:+.2f}")

# replace in place
doc = PDFDocument(); doc.load(src); ed = TextEditor(doc)
ed.add_text(1, 400, 250, "إجمالي المبلغ المستحق 15,750.00 ريال سعودي", font_size=14)
p1 = os.path.join(out, "added.pdf"); doc.save(p1)
doc = PDFDocument(); doc.load(p1); ed = TextEditor(doc)
run = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
old = tuple(round(v, 2) for v in run.bbox)
res = ed.replace_text_run(run.run_id, "إجمالي المبلغ المستحق 18,500.00 ريال سعودي")
print("replace:", res.success, res.message)
p2 = os.path.join(out, "edited.pdf"); doc.save(p2)
new = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
nb = tuple(round(v, 2) for v in new.bbox)
print(f"old bbox={old}\nnew bbox={nb}\ndx1={nb[2]-old[2]:+.2f} dy0={nb[1]-old[1]:+.2f}")
pg = pymupdf.open(p2)[0]
print("search 18,500:", len(pg.search_for("18,500.00")), "old:", len(pg.search_for("15,750.00")))
# longer and shorter replacements
for t in ["إجمالي المبلغ المستحق 18,500.00 ريال سعودي فقط لا غير وشكرا", "قصير"]:
    doc = PDFDocument(); doc.load(p1); ed = TextEditor(doc)
    run = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
    o = tuple(round(v, 2) for v in run.bbox)
    r2 = ed.replace_text_run(run.run_id, t)
    pp = os.path.join(out, "v.pdf"); doc.save(pp)
    n = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
    print(f"{t[:18]!r:22} ok={r2.success} dx1={n.bbox[2]-o[2]:+.2f} dy0={n.bbox[1]-o[1]:+.2f} text_ok={t in pymupdf.open(pp)[0].get_text()}")
