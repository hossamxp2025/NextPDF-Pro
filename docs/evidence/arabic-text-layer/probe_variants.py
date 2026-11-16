import sys, os, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\DELL\NextPDF-Pro")
import pymupdf
from src.engine.text_engine import TextEngine, TextStyle
from src.engine.fonts import get_font_registry

reg = get_font_registry(); eng = TextEngine(reg)
variants = ["شكراً لتعاملكم", "شكرا لتعاملكم", "شكراً", "لتعاملكم", "Thank you شكرا", "Thank you — شكرا",
            "Thank you — شكراً لتعاملكم", "ًا", "مكم", "إجمالي المبلغ المستحق 15,750.00 ريال سعودي",
            "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "القاهرة، مصر — 2026/11/16", "الله", "لا إله إلا الله",
            "Mixed English and عربي together 42", "ﻣﺮﺣﺒﺎ"]
for fam in sys.argv[1:]:
    print("==", fam)
    for v in variants:
        d = pymupdf.open(); p = d.new_page()
        eng.insert_text(p, pymupdf.Rect(60, 60, 540, 120), v, TextStyle(family=fam, size=14))
        b = d.tobytes(garbage=4); d.close()
        r = pymupdf.open("pdf", b); t = r[0].get_text().strip().replace("\n", " ")
        ok = unicodedata.normalize("NFKC", t) == unicodedata.normalize("NFKC", v)
        print(f"  {'OK ' if ok else 'BAD'} {v!r:40} -> {t!r}")
        r.close()
