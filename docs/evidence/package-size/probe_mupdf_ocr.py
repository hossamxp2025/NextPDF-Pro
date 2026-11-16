"""Does MuPDF's built-in Tesseract work here with traineddata alone?"""
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.engine.text_engine import TextEngine, TextStyle
from src.engine.fonts import get_font_registry

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
TESSDATA = r"C:\Users\DELL\NextPDF-Pro\resources\tesseract\tessdata"
AR = "إجمالي المبلغ المستحق 15,750.00 ريال سعودي"
EN = "Invoice INV-2026/0042 TOTAL DUE"

# Build a scan: render text, rasterise, wrap the image in a text-free PDF.
eng = TextEngine(get_font_registry())
src = pymupdf.open(); p = src.new_page(width=595, height=300)
eng.insert_text(p, pymupdf.Rect(40, 40, 555, 90), EN, TextStyle(size=20))
eng.insert_text(p, pymupdf.Rect(40, 110, 555, 170), AR, TextStyle(size=20))
pix = p.get_pixmap(dpi=200, alpha=False)
scan = pymupdf.open(); sp = scan.new_page(width=595, height=300)
sp.insert_image(sp.rect, pixmap=pix)
scan_path = os.path.join(out, "scan.pdf"); scan.save(scan_path); src.close(); scan.close()
d = pymupdf.open(scan_path)
print("scan has no text layer:", repr(d[0].get_text().strip()) == "''")

def report(label, page, needles):
    text = page.get_text()
    hits = {n: len(page.search_for(n)) for n in needles}
    print(f"  [{label}] chars={len(text.strip())} hits={hits}")
    print(f"      {text.strip()[:140]!r}")

needles = ["المبلغ", "ريال", "Invoice", "TOTAL"]

# 1) textpage OCR (recognition only)
t = time.time()
try:
    tp = d[0].get_textpage_ocr(flags=0, language="ara+eng", dpi=200, full=True, tessdata=TESSDATA)
    txt = d[0].get_text(textpage=tp)
    print(f"get_textpage_ocr OK in {time.time()-t:.1f}s: {txt.strip()[:160]!r}")
except Exception as e:
    print("get_textpage_ocr FAILED:", repr(e))

# 2) pdfocr_tobytes (full searchable page)
t = time.time()
try:
    pix2 = d[0].get_pixmap(dpi=200, alpha=False)
    blob = pix2.pdfocr_tobytes(language="ara+eng", tessdata=TESSDATA)
    o = pymupdf.open("pdf", blob)
    print(f"pdfocr_tobytes OK in {time.time()-t:.1f}s, {len(blob)} bytes, pages={o.page_count}")
    report("pdfocr", o[0], needles)
    o.save(os.path.join(out, "mupdf_ocr.pdf"))
except Exception as e:
    print("pdfocr_tobytes FAILED:", repr(e))

# 3) eng only, to separate Arabic-model issues from engine issues
try:
    pix3 = d[0].get_pixmap(dpi=200, alpha=False)
    o2 = pymupdf.open("pdf", pix3.pdfocr_tobytes(language="eng", tessdata=TESSDATA))
    report("pdfocr eng", o2[0], ["Invoice", "TOTAL"])
except Exception as e:
    print("eng-only FAILED:", repr(e))

# 4) what pytesseract gives today, for comparison
try:
    import pytesseract
    from PIL import Image
    import io as _io
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\DELL\NextPDF-Pro\resources\tesseract\tesseract.exe"
    os.environ["TESSDATA_PREFIX"] = TESSDATA
    img = Image.open(_io.BytesIO(d[0].get_pixmap(dpi=200, alpha=False).tobytes("png")))
    t = time.time()
    print(f"pytesseract in {time.time()-t:.1f}s:",
          repr(pytesseract.image_to_string(img, lang="ara+eng", config="--psm 3").strip()[:160]))
except Exception as e:
    print("pytesseract comparison FAILED:", repr(e))
