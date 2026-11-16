import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz

print("=== broken fixture: dict spans ===")
doc = fitz.open("docs/evidence/_fixture_broken.pdf")
page = doc[0]
for block in page.get_text("dict")["blocks"]:
    if block.get("type") != 0: continue
    for line in block.get("lines", []):
        print(" line bbox:", [round(v,1) for v in line["bbox"]])
        for span in line["spans"]:
            print("   span bbox:", [round(v,1) for v in span["bbox"]], "font:", span["font"], "text:", repr(span["text"]))
doc.close()

print("\n=== borderless table: find_tables(text) ===")
doc = fitz.open("docs/evidence/_fixture_table.pdf")
page = doc[0]
finder = page.find_tables(strategy="text", min_words_vertical=3, use_layout=False)
for t in finder.tables:
    print("rows", t.row_count, "cols", t.col_count)
    for i, row in enumerate(t.rows):
        print(f"  r{i} bbox={[round(v,1) for v in row.bbox]}")
        print("      cells:", [ [round(v,1) for v in c] if c else None for c in row.cells])
doc.close()
