import sys, os, unicodedata
sys.path.insert(0, os.getcwd())
import pymupdf as fitz
from fontTools.ttLib import TTFont

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)
page = doc[0]

def gid_unicode_map(fp):
    f = TTFont(fp, lazy=True)
    cmap = f.getBestCmap(); order = f.getGlyphOrder()
    gid_of = {name: i for i, name in enumerate(order)}
    m = {}
    for u, g in cmap.items():
        gid = gid_of.get(g)
        if gid is not None and gid not in m:
            m[gid] = u
    f.close(); return m

maps = {3: gid_unicode_map('docs/evidence/font_3.ttf'),
        7: gid_unicode_map('docs/evidence/font_7.ttf')}

LTR_EXTRA = set("-,./:%()+")

def is_ltr(ch):
    return ch.isascii() and (ch.isalnum() or ch in LTR_EXTRA)

def visual_to_logical(s):
    rev = s[::-1]
    out = []
    i, n = 0, len(rev)
    while i < n:
        if is_ltr(rev[i]):
            j = i
            while j < n and is_ltr(rev[j]):
                j += 1
            out.append(rev[i:j][::-1])
            i = j
        else:
            out.append(rev[i]); i += 1
    return unicodedata.normalize("NFKC", "".join(out))

trace = page.get_texttrace()
lines = []
for span in trace:
    fmap = maps.get(3 if 'Reg' in span['font'] else 7, maps[3])
    text = ''.join(chr(fmap.get(ch[1], ch[0])) if ch[1] in fmap else (chr(ch[0]) if ch[0] != 65533 else '')
                   for ch in span['chars'])
    lines.append((round(span['bbox'][1], 1), round(span['bbox'][0], 1), text))

lines.sort()
seen = set()
for y, x, t in lines:
    key = (y, t)
    if key in seen: continue
    seen.add(key)
    print(f"y={y:6.1f} | {visual_to_logical(t)}")
    if len(seen) > 30: break
doc.close()
