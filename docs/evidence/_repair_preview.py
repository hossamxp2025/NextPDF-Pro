import pymupdf as fitz
from fontTools.ttLib import TTFont

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)
page = doc[0]

def gid_unicode_map(fontpath):
    f = TTFont(fontpath, lazy=True)
    cmap = f.getBestCmap()
    order = f.getGlyphOrder()
    gid_of = {name: i for i, name in enumerate(order)}
    g2u = {}
    for u, gname in cmap.items():
        g = gid_of.get(gname)
        if g is not None:
            g2u[g] = u
    f.close()
    return g2u

maps = {3: gid_unicode_map('docs/evidence/font_3.ttf'),
        7: gid_unicode_map('docs/evidence/font_7.ttf')}

trace = page.get_texttrace()
out_lines = []
for span in trace:
    font = span.get('font', '')
    fmap = maps.get(3 if 'Reg' in font else 7, maps[3])
    text = ''
    for ch in span['chars']:
        uni, gid, origin, bbox = ch
        mapped = fmap.get(gid)
        if mapped is None:
            text += chr(uni) if uni != 65533 else '\ufffd'
        else:
            text += chr(mapped)
    out_lines.append((round(span['bbox'][1], 1), span['bbox'][0], font, text))

# sort by y then x
out_lines.sort(key=lambda t: (t[0], t[1]))
print("Repaired text preview (first 60 lines):")
for y, x, font, text in out_lines[:60]:
    print(f"  y={y:7.1f} x={x:7.1f} [{font}] {text!r}")

# coverage stats
total = mapped = 0
for span in trace:
    font = span.get('font', '')
    fmap = maps.get(3 if 'Reg' in font else 7, maps[3])
    for ch in span['chars']:
        total += 1
        if ch[1] in fmap:
            mapped += 1
print(f"\nGID coverage: {mapped}/{total} = {100.0*mapped/total:.1f}%")

doc.close()
