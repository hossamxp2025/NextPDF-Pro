import sys, os, io, unicodedata, statistics
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from fontTools.ttLib import TTFont

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)

def gid_to_unicode(buf):
    f = TTFont(io.BytesIO(buf), lazy=True)
    cmap = f.getBestCmap() or {}
    order = f.getGlyphOrder()
    gid_of = {n: i for i, n in enumerate(order)}
    g2u = {}
    for u, g in cmap.items():
        gid = gid_of.get(g)
        if gid is not None and gid not in g2u:
            g2u[gid] = u
    f.close()
    return g2u

def page_maps(page):
    maps = {}
    for info in page.get_fonts(full=True):
        xref, ext, typ, basefont, name, enc = info[:6]
        if enc not in ("Identity-H", "Identity-V"):
            continue
        if "/ToUnicode" in doc.xref_object(xref):
            continue
        try:
            _n, _e, _t, buf = doc.extract_font(xref)
        except Exception:
            continue
        if not buf:
            continue
        m = gid_to_unicode(buf)
        if m:
            maps[basefont] = m
    return maps

LTR = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
NUMPUNC = set("-.,/:")

def visual_to_logical(s):
    rev = s[::-1]
    out, i, n = [], 0, len(rev)
    while i < n:
        if rev[i] in LTR:
            j = i
            while j < n and (rev[j] in LTR or (rev[j] in NUMPUNC and j + 1 < n and rev[j+1] in LTR)):
                j += 1
            # trim trailing punctuation
            k = j
            while k > i and rev[k-1] in NUMPUNC:
                k -= 1
            out.append(rev[i:k][::-1])
            out.append(rev[k:j][::-1])
            i = j
        else:
            out.append(rev[i]); i += 1
    return unicodedata.normalize("NFKC", "".join(out))

for pno in (0, 1):
    page = doc[pno]
    maps = page_maps(page)
    print(f"===== page {pno+1}: repaired fonts={list(maps)} =====")
    d = page.get_text("dict")
    seen = set()
    for block in d["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts = []
            for span in line["spans"]:
                t = span["text"]
                m = maps.get(span["font"])
                if m:
                    conv = "".join(chr(m[ord(c)]) if ord(c) in m else c for c in t)
                    t = visual_to_logical(conv)
                else:
                    t = t
                parts.append(t)
            text = "".join(parts).strip()
            if not text:
                continue
            key = (round(line["bbox"][1], 0), text)
            if key in seen:
                continue
            seen.add(key)
            print(f"  y={line['bbox'][1]:6.1f} x={line['bbox'][0]:6.1f} | {text}")
    print()

doc.close()
