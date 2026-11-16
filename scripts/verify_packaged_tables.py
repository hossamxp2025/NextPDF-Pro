"""Table-layout matrix through the actual frozen conversion entry point."""
import json
import subprocess
import sys
from pathlib import Path
import pymupdf as fitz
from openpyxl import load_workbook

exe = Path(sys.argv[1]).resolve()
directory = Path(sys.argv[2]).resolve()
directory.mkdir(parents=True, exist_ok=True)
checks = []
for layout in ('complete', 'partial', 'borderless', 'multiple', 'pages', 'unsupported'):
    work = directory / layout
    work.mkdir(exist_ok=True)
    with fitz.open() as doc:
        for page_index in range(2 if layout == 'pages' else 1):
            page = doc.new_page(width=600, height=650)
            for offset in ([0, 260] if layout == 'multiple' else [0]):
                if layout not in {'borderless', 'unsupported'}:
                    for y in (40, 80, 120, 160, 200):
                        page.draw_line((40, y + offset), (420, y + offset))
                    for x in (40, 230, 420):
                        if layout == 'partial':
                            page.draw_line((x, 40 + offset), (x, 99 + offset))
                            page.draw_line((x, 101 + offset), (x, 200 + offset))
                        else:
                            page.draw_line((x, 40 + offset), (x, 200 + offset))
                for r, values in enumerate([('Item', 'Amount'), ('Invoice', '125.50'),
                                           ('Currency', '$1,250.00'), ('Date', '2026-11-15')]):
                    for c, text in enumerate(values):
                        shift = r * 25 if layout == 'unsupported' and c else 0
                        page.insert_text((50 + 190 * c + shift, 65 + 40 * r + offset), text)
            if layout == 'unsupported':
                # Jagged columns with no shared column boundaries.
                page.draw_line((40, 40), (420, 200))
        doc.save(work / 'input.pdf')
    request = work / 'request.json'
    request.write_text(json.dumps({'format': 'xlsx', 'pages': [1, 2] if layout == 'pages' else [1]}))
    source = (work / 'input.pdf').read_bytes()
    process = subprocess.run([str(exe), '--conversion-job', str(request)], cwd=directory, timeout=120)
    result = json.loads((work / 'result.json').read_text())
    if layout == 'unsupported':
        ok = process.returncode == 1 and not result['ok'] and not (work / 'output.xlsx').exists()
    else:
        ok = process.returncode == 0 and result['ok']
        if ok:
            book = load_workbook(work / 'output.xlsx')
            try:
                ok = (len(book.worksheets) == (2 if layout in {'multiple', 'pages'} else 1)
                      and book.active['B2'].value == 125.5
                      and book.active['B3'].value == '$1,250.00'
                      and book.active['B4'].value.year == 2026)
            finally:
                book.close()
    ok = ok and (work / 'input.pdf').read_bytes() == source
    checks.append({'layout': layout, 'status': 'PASS' if ok else 'FAIL'})
(directory / 'report.json').write_text(json.dumps(checks, indent=2))
print(json.dumps(checks, indent=2))
sys.exit(0 if all(item['status'] == 'PASS' for item in checks) else 1)
