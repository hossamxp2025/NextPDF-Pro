import pymupdf as fitz
import unicodedata
from src.config import FONTS_DIR

doc = fitz.open()
page = doc.new_page(width=500, height=200)
page.insert_htmlbox(
    fitz.Rect(40, 40, 460, 160),
    "<p dir='rtl'>مرحبا بالعالم INV-2026</p>",
    css="@font-face {font-family:A;src:url('NotoNaskhArabic-Regular.ttf');} body{font-family:A;font-size:22px;}",
    archive=fitz.Archive(str(FONTS_DIR)),
)
text = page.get_text()
print("raw:", repr(text))
print("nfkc:", repr(unicodedata.normalize("NFKC", text)))
span = page.get_text("dict")["blocks"][0]["lines"][0]["spans"][0]
print("keys:", sorted(span.keys()))
print("font:", span["font"], "size:", span["size"], "flags:", span["flags"], "color:", span["color"])
