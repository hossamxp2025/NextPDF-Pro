"""Render created PDFs to images so the visible result can be inspected."""
import sys
import pymupdf as fitz
from pathlib import Path

root = Path("build/_probe_create")
out = Path("docs/evidence")
out.mkdir(parents=True, exist_ok=True)
for name in sys.argv[1:]:
    source = root / name
    with fitz.open(source) as doc:
        page = doc[0]
        pix = page.get_pixmap(dpi=110)
        target = out / ("created_" + name.replace(".", "_") + ".png")
        pix.save(target)
        print(target, pix.width, pix.height)
