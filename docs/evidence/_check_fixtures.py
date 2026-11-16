import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from tests.pdf_fixtures import build_broken_encoding_pdf, build_borderless_table_pdf

out = os.path.join("docs", "evidence")
os.makedirs(out, exist_ok=True)

p1 = os.path.join(out, "_fixture_broken.pdf")
p2 = os.path.join(out, "_fixture_nofont.pdf")
p3 = os.path.join(out, "_fixture_table.pdf")

build_broken_encoding_pdf(p1, "كشف حساب بنكي")
build_broken_encoding_pdf(p2, "كشف حساب بنكي", embed_font=False)
build_borderless_table_pdf(p3)

for label, path in (("embedded", p1), ("no-font", p2), ("table", p3)):
    doc = fitz.open(path)
    page = doc[0]
    print(f"--- {label} ---")
    print("  fonts:", [(f[0], f[3], f[5]) for f in page.get_fonts(full=True)])
    print("  text :", repr(page.get_text().strip()[:80]))
    doc.close()
