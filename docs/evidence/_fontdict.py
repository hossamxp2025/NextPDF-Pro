import pymupdf as fitz

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)

for xref in (3, 7):
    print(f"=== font object xref {xref} ===")
    print(doc.xref_object(xref))
    # descendant fonts
    obj = doc.xref_object(xref)
    # find ToUnicode
    print()

doc.close()
