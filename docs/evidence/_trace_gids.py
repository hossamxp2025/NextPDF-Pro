import pymupdf as fitz
from fontTools.ttLib import TTFont

path = r'C:\Users\DELL\Downloads\statement_2026-11-01_2026-11-16 (2).pdf'
doc = fitz.open(path)
page = doc[0]

# build gid -> unicode using font cmap
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
for x, m in maps.items():
    arab = [u for u in m.values() if 0x0600 <= u <= 0x06FF]
    print(f"font {x}: gid->uni entries={len(m)} arabic entries={len(arab)} (plus presentation forms={len([u for u in m.values() if 0xFB50<=u<=0xFEFF])})")

trace = page.get_texttrace()
print("\ntexttrace spans:", len(trace))
shown = 0
for span in trace:
    font = span.get('font', '')
    chars = span.get('chars', [])
    line = []
    for ch in chars[:40]:
        gid = ch.get('gid')
        u = ch.get('c')
        mapped = None
        for x, m in maps.items():
            if gid in m:
                mapped = m[gid]
                break
        line.append(f"gid={gid} pdfU+{ord(u):04X} -> fontU+{(mapped if mapped is not None else 0):04X}{'' if mapped is None else ' '+chr(mapped)}")
    print(f"\nfont={font}")
    for l in line:
        print("   ", l)
    shown += 1
    if shown >= 2:
        break

doc.close()
