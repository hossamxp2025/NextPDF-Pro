import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from src.engine import conversion

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)

for pno in (0, 1):
    page = doc[pno]
    print(f"===== page {pno+1} =====")
    raw_chars = [char for block in page.get_text("rawdict")["blocks"]
                 for line in block.get("lines", [])
                 for span in line["spans"] for char in span["chars"]]
    finder = page.find_tables(strategy="text", min_words_vertical=3, use_layout=False)
    for ti, table in enumerate(finder.tables):
        print(f" table {ti}: rows={table.row_count} cols={table.col_count}")
        none_cells = sum(1 for row in table.rows for cell in row.cells if cell is None)
        print(f"  none_cells={none_cells}")
        rows, boxes = [], []
        for row in table.rows:
            values, bounds = [], []
            for cell in row.cells:
                if cell is None:
                    values.append(None); bounds.append(None); continue
                rect = fitz.Rect(cell)
                char_rect = rect + (0, -3, 0, 3)
                chars = [ch for ch in raw_chars if char_rect.contains(fitz.Point(
                    (ch["bbox"][0] + ch["bbox"][2]) / 2,
                    (ch["bbox"][1] + ch["bbox"][3]) / 2))]
                text = page.get_textbox(rect).strip()
                values.append(text)
                bounds.append((min(ch["bbox"][0] for ch in chars), max(ch["bbox"][2] for ch in chars)) if chars else None)
            rows.append(values); boxes.append(bounds)
        empties = sum(1 for row in rows for v in row if not v)
        none_bounds = sum(1 for row in boxes for b in row if b is None)
        print(f"  empty_values={empties}  none_bounds={none_bounds}  row_count_kept={len(rows)}")
        gutters = []
        for c in range(len(rows[0]) - 1):
            vals = [min(row[c+1][0] for row in boxes if row[c+1] is not None) - max(row[c][1] for row in boxes if row[c] is not None)]
            gutters.append(round(vals[0], 1) if vals else None)
        print("  gutters:", gutters)
        print("  first row values:", rows[0][:9])
doc.close()
