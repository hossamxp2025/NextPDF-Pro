from fontTools.ttLib import TTFont

for xref in (3, 7):
    path = f"docs/evidence/font_{xref}.ttf"
    try:
        f = TTFont(path, lazy=True)
    except Exception as e:
        print(f"font {xref}: cannot open: {e}")
        continue
    print(f"=== font {xref} ({path}) ===")
    print("  tables:", sorted(f.keys()))
    print("  numGlyphs:", f['maxp'].numGlyphs)
    cmap = f.getBestCmap() if 'cmap' in f else None
    if cmap:
        print("  cmap entries:", len(cmap))
        items = sorted(cmap.items())[:5]
        print("  sample unicode->glyph:", items)
        # reverse: glyph -> unicode
        rev = {}
        for u, g in cmap.items():
            rev.setdefault(g, u)
        print("  reverse glyph->unicode count:", len(rev))
    else:
        print("  NO cmap table")
    # Does font have GSUB / Arabic shaping?
    for tag in ('GSUB', 'GPOS', 'GDEF'):
        print(f"  {tag}:", 'present' if tag in f else 'absent')
    f.close()
