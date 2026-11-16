import sys, os, io, unicodedata
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from fontTools.ttLib import TTFont

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)

def gid_to_unicode(buf):
    f = TTFont(io.BytesIO(buf), lazy=True)
    cmap = f.getBestCmap() or {}; order = f.getGlyphOrder()
    gid_of = {n: i for i, n in enumerate(order)}; g2u = {}
    for u, g in cmap.items():
        gid = gid_of.get(g)
        if gid is not None and gid not in g2u: g2u[gid] = u
    f.close(); return g2u

def page_maps(page):
    maps = {}
    for info in page.get_fonts(full=True):
        xref, ext, typ, basefont, name, enc = info[:6]
        if enc not in ("Identity-H", "Identity-V"): continue
        if "/ToUnicode" in doc.xref_object(xref): continue
        try: _n,_e,_t,buf = doc.extract_font(xref)
        except Exception: continue
        if buf:
            m = gid_to_unicode(buf)
            if m: maps[basefont] = m
    return maps

LTR = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
NUMPUNC = set("-.,/:"); MIRROR = {')':'(', '(':')', ']':'[', '[':']', '}':'{', '{':'}', '»':'«', '«':'»'}
def v2l(s):
    rev = s[::-1]; out, i, n = [], 0, len(rev)
    while i < n:
        if rev[i] in LTR:
            j = i
            while j < n and (rev[j] in LTR or (rev[j] in NUMPUNC and j+1<n and rev[j+1] in LTR)): j += 1
            k = j
            while k > i and rev[k-1] in NUMPUNC: k -= 1
            out.append(rev[i:k][::-1]); out.append(rev[k:j][::-1]); i = j
        else: out.append(rev[i]); i += 1
    r = "".join(out); r = "".join(MIRROR.get(c,c) for c in r)
    return unicodedata.normalize("NFKC", r)

def cell_text(raw, rect, maps):
    rr = rect + (0,-3,0,3); picked = []
    for ch in raw:
        cx = (ch["bbox"][0]+ch["bbox"][2])/2; cy = (ch["bbox"][1]+ch["bbox"][3])/2
        if rr.contains(fitz.Point(cx, cy)):
            code = ord(ch["c"]); m = maps.get(ch["font"])
            char = chr(m[code]) if (m and code in m) else ch["c"]
            picked.append((ch["origin"][1], ch["origin"][0], char))
    if not picked: return ""
    picked.sort(); bl = {}
    for y,x,c in picked: bl.setdefault(round(y,1), []).append((x,c))
    return v2l("\n".join("".join(c for _,c in sorted(g)) for _,g in sorted(bl.items()))).strip()

page = doc[0]; maps = page_maps(page)
raw2 = []
for b in page.get_text("rawdict")["blocks"]:
    if b.get("type") != 0: continue
    for line in b.get("lines", []):
        for span in line["spans"]:
            for ch in span["chars"]:
                ch["font"] = span["font"]; raw2.append(ch)

finder = page.find_tables(strategy="text", min_words_vertical=3, use_layout=False)
t = finder.tables[0]
print(f"rows={t.row_count} cols={t.col_count}")
for ri, row in enumerate(t.rows):
    vals = [cell_text(raw2, fitz.Rect(c), maps) if c else "" for c in row.cells]
    n = sum(1 for v in vals if v)
    y = round(row.bbox[1], 1)
    print(f"r{ri:02d} y={y:6.1f} nonempty={n} | " + " | ".join(v.replace(chr(10), '/') for v in vals))
doc.close()
