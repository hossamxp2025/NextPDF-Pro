"""Inspect actual vector grid discovery independently of spreadsheet writing."""
import pymupdf as fitz
doc = fitz.open()
page = doc.new_page(width=400, height=300)
for x in (40, 180, 320):
    page.draw_line((x, 40), (x, 160))
for y in (40, 80, 120, 160):
    page.draw_line((40, y), (320, y))
for r, values in enumerate((("Item", "Amount"), ("INV-2026-105", "15750"), ("Second", "2026"))):
    for c, value in enumerate(values):
        page.insert_text((50+c*140,65+r*40),value,fontsize=12)
finder = page.find_tables(vertical_strategy="explicit",horizontal_strategy="explicit",
                          vertical_lines=[40,180,320],horizontal_lines=[40,80,120,160])
for table in finder.tables:
    print(table.extract())
    print([row.cells for row in table.rows])
