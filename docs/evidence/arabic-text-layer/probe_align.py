"""Where do glyphs land inside an insert_htmlbox rect, per direction/align?"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.engine.text_engine import TextEngine, TextStyle
from src.engine.fonts import get_font_registry

eng = TextEngine(get_font_registry())
BOX = pymupdf.Rect(100, 100, 500, 160)
cases = [("إجمالي المبلغ 15,750.00 ريال", "rtl"), ("Invoice total 15,750.00 USD", "ltr")]
for text, d in cases:
    for align in ("left", "right", "center", "auto"):
        doc = pymupdf.open(); page = doc.new_page()
        st = TextStyle(size=14, direction=d, align=align)
        res = eng.insert_text(page, BOX, text, st, shrink_to_fit=False)
        blocks = page.get_text("blocks")
        x0 = min(b[0] for b in blocks); x1 = max(b[2] for b in blocks)
        y0 = min(b[1] for b in blocks); y1 = max(b[3] for b in blocks)
        print(f"{d} align={align:7s} glyphs x[{x0:7.2f},{x1:7.2f}] y[{y0:6.2f},{y1:6.2f}] "
              f"| box x[{BOX.x0},{BOX.x1}] y[{BOX.y0},{BOX.y1}] "
              f"| left_pad={x0-BOX.x0:6.2f} right_pad={BOX.x1-x1:6.2f} top_pad={y0-BOX.y0:5.2f}")
        doc.close()
# measure() vs real glyph width
for text, d in cases:
    st = TextStyle(size=14, direction=d)
    w, h = eng.measure(text, st, width=10000)
    doc = pymupdf.open(); page = doc.new_page()
    eng.insert_text(page, pymupdf.Rect(50, 50, 550, 110), text, st, shrink_to_fit=False)
    blocks = page.get_text("blocks")
    real_w = max(b[2] for b in blocks) - min(b[0] for b in blocks)
    real_h = max(b[3] for b in blocks) - min(b[1] for b in blocks)
    print(f"{d}: measure=({w:.2f},{h:.2f}) real=({real_w:.2f},{real_h:.2f})")
    doc.close()
