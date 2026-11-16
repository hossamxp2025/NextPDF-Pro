import pymupdf as fitz
import io

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)
page = doc[0]

print("get_fonts(full=True):")
for f in page.get_fonts(full=True):
    print(" ", f)

# extract each font
for f in page.get_fonts(full=True):
    xref = f[0]
    try:
        name, ext, typ, buf = doc.extract_font(xref)
        print(f"\nfont xref={xref} name={name!r} ext={ext!r} type={typ!r} bytes={len(buf)}")
        if buf:
            out = f"docs/evidence/font_{xref}.{ext or 'bin'}"
            with open(out, 'wb') as fh:
                fh.write(buf)
            print("  saved:", out)
    except Exception as e:
        print("  extract failed:", e)

doc.close()
