import sys, os
sys.path.insert(0, os.getcwd())
from tests.pdf_fixtures import build_broken_encoding_pdf, build_borderless_table_pdf
from src.engine.conversion import export_pdf

out = "docs/evidence"
p_ok = os.path.join(out, "_fixture_broken.pdf")
p_bad = os.path.join(out, "_fixture_nofont.pdf")
p_tbl = os.path.join(out, "_fixture_table.pdf")

build_broken_encoding_pdf(p_ok, "كشف حساب بنكي")
build_broken_encoding_pdf(p_bad, "كشف حساب بنكي", embed_font=False)
build_borderless_table_pdf(p_tbl)

# 1) embedded broken font -> repaired
data = open(p_ok, "rb").read()
target = os.path.join(out, "_out_broken.docx")
export_pdf(data, target, [1], "docx_editable")
from docx import Document
d = Document(target)
text = " ".join(p.text for p in d.paragraphs if p.text.strip())
print("REPAIRED docx text:", repr(text))
print("  has expected Arabic:", "كشف حساب بنكي" in text)

# 2) missing font -> refuse
data = open(p_bad, "rb").read()
try:
    export_pdf(data, os.path.join(out, "_out_nofont.docx"), [1], "docx_editable")
    print("NO-FONT: FAILED TO REFUSE")
except ValueError as e:
    print("NO-FONT refused:", e)

# 3) borderless table
data = open(p_tbl, "rb").read()
target = os.path.join(out, "_out_table.xlsx")
export_pdf(data, target, [1], "xlsx")
from openpyxl import load_workbook
wb = load_workbook(target)
ws = wb.worksheets[0]
print("TABLE dims:", ws.dimensions)
for row in ws.iter_rows(values_only=True):
    print("  ", row)
