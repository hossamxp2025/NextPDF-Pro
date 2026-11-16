import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz

for label, path in (("embedded", "docs/evidence/_fixture_broken.pdf"),
                    ("no-font", "docs/evidence/_fixture_nofont.pdf")):
    doc = fitz.open(path); page = doc[0]
    print("===", label, "===")
    print("get_text:", repr(page.get_text().strip()))
    for span in page.get_texttrace():
        print("span font:", span.get("font"))
        for ch in span["chars"][:12]:
            uni, gid = ch[0], ch[1]
            print(f"   uni=U+{uni:04X} gid={gid} chr(gid)=U+{gid:04X} {chr(gid)!r}")
    doc.close()
    print()
