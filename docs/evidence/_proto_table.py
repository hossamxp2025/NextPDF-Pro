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
NUMPUNC = set("-.,/:")
MIRROR = {')':'(', '(':')', ']':'[', '[':']', '}':'{', '{':'}', '»':'«', '«':'»'}

def visual_to_logical(s):
    rev = s[::-1]
    out, i, n = [], 0, len(rev)
    while i < n:
        if rev[i] in LTR:
            j = i
            while j < n and (rev[j] in LTR or (rev[j] in NUMPUNC and j+1 < n and rev[j+1] in LTR)):
                j += 1
            k = j
            while k > i and rev[k-1] in NUMPUNC: k -= 1
            out.append(rev[i:k][::-1]); out.append(rev[k:j][::-1]); i = j
        else:
            out.append(rev[i]); i += 1
    r = "".join(out)
    r = "".join(MIRROR.get(c, c) for c in r)
    return unicodedata.normalize("NFKC", r)

def cell_text(raw, rect, maps):
    rr = rect + (0, -3, 0, 3)
    picked = []
    for ch in raw:
        cx = (ch["bbox"][0] + ch["bbox"][2]) / 2
        cy = (ch["bbox"][1] + ch["bbox"][3]) / 2
        if rr.contains(fitz.Point(cx, cy)):
            code = ord(ch["c"])
            m = maps.get(ch["font"])
            char = chr(m[code]) if (m and code in m) else ch["c"]
            picked.append((ch["origin"][1], ch["origin"][0], char))
    if not picked: return ""
    picked.sort()
    baselines = {}
    for y, x, c in picked:
        baselines.setdefault(round(y, 1), []).append((x, c))
    joined = "\n".join("".join(c for _, c in sorted(g)) for _, g in sorted(baselines.items()))
    return visual_to_logical(joined).strip()

for pno in (0, 1):
    page = doc[pno]
    maps = page_maps(page)
    raw = [ch for b in page.get_text("rawdict")["blocks"] if b.get("type") == 0
           for line in b.get("lines", []) for span in line["spans"]
           for ch in span["chars"] if True]
    # attach font per char
    raw2 = []
    for b in page.get_text("rawdict")["blocks"]:
        if b.get("type") != 0: continue
        for line in b.get("lines", []):
            for span in line["spans"]:
                for ch in span["chars"]:
                    ch["font"] = span["font"]; raw2.append(ch)
    print(f"===== page {pno+1} =====")
    for strat_kw in ({"strategy": "text"}, {"horizontal_strategy": "text", "vertical_strategy": "lines"}):
        try:
            finder = page.find_tables(min_words_vertical=3, use_layout=False, **strat_kw)
        except Exception as e:
            print("  err", e); continue
        label = strat_kw.get("strategy") or "h=text,v=lines"
        print(f" strategy={label}: {len(finder.tables)} table(s)")
        for t in finder.tables:
            print(f"   rows={t.row_count} cols={t.col_count}")
            rows = []
            for row in t.rows:
                vals = []
                for cell in row.cells:
                    if cell is None: vals.append(""); continue
                    vals.append(cell_text(raw2, fitz.Rect(cell), maps))
                rows.append(vals)
            nonempty = sum(1 for r in rows for v in r if v)
            print(f"   nonempty={nonempty}/{len(rows)*len(rows[0])}")
            # median gutter
            def char_bounds(cell_rect):
                xs = [ch["bbox"][0] for ch in raw2 if fitz.Rect(cell_rect).contains(
                    fitz.Point((ch["bbox"][0]+ch["bbox"][2])/2, (ch["bbox"][1]+ch["bbox"][3])/2))]
                xs2 = [ch["bbox"][2] for ch in raw2 if fitz.Rect(cell_rect).contains(
                    fitz.Point((ch["bbox"][0]+ch["bbox"][2])/2, (ch["bbox"][1]+ch["bbox"][3])/2))]
                return (min(xs), max(xs2)) if xs else None

            gut = []
            for c in range(len(rows[0]) - 1):
                lefts, rights = [], []
                for row in t.rows:
                    right_cell, left_cell = row.cells[c], row.cells[c+1]
                    if not right_cell or not left_cell:
                        continue
                    lb = char_bounds(left_cell)
                    rb = char_bounds(right_cell)
                    if lb and rb:
                        lefts.append(lb[0]); rights.append(rb[1])
                if lefts and rights:
                    gut.append(round(statistics.median(lefts) - statistics.median(rights), 1))
            print("   median gutters:", gut)
            print("   header row:", rows[0])
            print("   row1:", rows[1] if len(rows) > 1 else None)
            # rtl reversed header
            print("   header RTL:", list(reversed(rows[0])))
            break
    print()
doc.close()
