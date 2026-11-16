import json, collections

with open('docs/evidence/statement_diagnosis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for d in data['details']:
    t = d['text']
    chars = [c for c in t if ord(c) >= 32]
    total = len(chars)
    def inr(c, lo, hi):
        return lo <= ord(c) <= hi
    ascii_ = [c for c in chars if inr(c, 32, 126)]
    arabic = [c for c in chars if 0x0600 <= ord(c) <= 0x06FF]
    latin1 = [c for c in chars if 0x00A0 <= ord(c) <= 0x00FF]
    ext = [c for c in chars if 0x0100 <= ord(c) <= 0x024F]
    other = [c for c in chars if not (32 <= ord(c) <= 126 or 0x0600 <= ord(c) <= 0x06FF
                                      or 0x00A0 <= ord(c) <= 0x00FF or 0x0100 <= ord(c) <= 0x024F)]
    print(f"Page {d['page']}: chars={total}")
    for name, lst in (("ascii", ascii_), ("arabic", arabic), ("latin1", latin1), ("ext", ext), ("other", other)):
        pct = (100.0 * len(lst) / total) if total else 0
        print(f"  {name:7s} count={len(lst):5d}  {pct:6.2f}%")
    ext_codes = sorted(set(ord(c) for c in ext))
    print("  ext unique:", " ".join(f"U+{c:04X}" for c in ext_codes[:15]))
    print("  other unique:", " ".join(f"U+{c:04X}" for c in sorted(set(ord(c) for c in other))[:10]))
    # first line preview
    first = t.split("\n")[0]
    print("  first-line repr:", repr(first[:60]))
    print()
