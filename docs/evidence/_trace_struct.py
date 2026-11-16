import pymupdf as fitz

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)
page = doc[0]
trace = page.get_texttrace()
span = trace[0]
print("span keys:", list(span.keys()))
for k, v in span.items():
    if k != 'chars':
        print(f"  {k} = {v!r}")
ch = span['chars'][0]
print("char entry:", ch, "len:", len(ch))
for i, part in enumerate(ch):
    print(f"  [{i}] {type(part).__name__}: {part!r}")
doc.close()
