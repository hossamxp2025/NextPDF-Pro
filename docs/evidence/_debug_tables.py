import sys, os, traceback
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from src.engine import conversion

src = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(src)
repair = conversion._TextRepair(doc)

for pno in (0, 1):
    page = doc[pno]
    print(f"=== page {pno+1} ===")
    try:
        tables = conversion._detected_tables(page, repair)
        print("detected:", [(len(t), len(t[0]) if t else 0) for t in tables])
        if tables:
            print("header:", tables[0][0])
            print("row1  :", tables[0][1] if len(tables[0]) > 1 else None)
    except Exception as e:
        print("EXCEPTION:", type(e).__name__, e)
        traceback.print_exc()
doc.close()
