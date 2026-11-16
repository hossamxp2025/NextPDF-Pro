import sys, os
sys.path.insert(0, os.getcwd())
from src.engine.conversion import export_pdf

src = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
data = open(src, 'rb').read()
out = os.path.join('docs', 'evidence')

for fmt in ('docx_editable', 'pptx_editable', 'xlsx'):
    target = os.path.join(out, 'stmt_result.' + ('docx' if fmt.startswith('docx') else 'pptx' if fmt.startswith('pptx') else 'xlsx'))
    try:
        export_pdf(data, target, [1, 2], fmt)
        print(fmt, 'OK ->', target, os.path.getsize(target), 'bytes')
    except Exception as e:
        print(fmt, 'FAILED:', type(e).__name__, e)

# inspect docx
try:
    from docx import Document
    d = Document(os.path.join(out, 'stmt_result.docx'))
    print('\n--- DOCX first paragraphs ---')
    for p in d.paragraphs[:15]:
        if p.text.strip():
            print(repr(p.text))
except Exception as e:
    print('docx read failed', e)

# inspect xlsx
try:
    from openpyxl import load_workbook
    wb = load_workbook(os.path.join(out, 'stmt_result.xlsx'))
    for ws in wb.worksheets:
        print(f'\n--- XLSX {ws.title} dims={ws.dimensions} rtl={ws.sheet_view.rightToLeft} ---')
        for row in ws.iter_rows(min_row=1, max_row=8, values_only=True):
            print(row)
except Exception as e:
    print('xlsx read failed', e)
