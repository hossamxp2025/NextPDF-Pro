import ast, collections, os, sys
root = r"C:\Users\DELL\NextPDF-Pro"
toc = ast.literal_eval(open(os.path.join(root, r"build\pyinstaller_build\NextPDF-Pro\PKG-00.toc")).read())
items = next(x for x in toc if isinstance(x, list) and x and isinstance(x[0], tuple))
tot = collections.Counter()
big = []
for entry in items:
    name, path = entry[0], entry[1]
    size = os.path.getsize(path) if path and os.path.isfile(path) else 0
    parts = name.replace("\\", "/").split("/")
    top = parts[0] if len(parts) > 1 else "(root files)"
    if top in ("resources",) and len(parts) > 1:
        top = "resources/" + parts[1]
    tot[top] += size
    big.append((size, name))
print(f"{'component':32s}      MB")
for k, v in tot.most_common(20):
    print(f"{k:32s} {v/1048576:8.1f}")
print(f"{'TOTAL':32s} {sum(tot.values())/1048576:8.1f}\n")
print("largest single files:")
for size, name in sorted(big, reverse=True)[:18]:
    print(f"  {size/1048576:7.1f} MB  {name}")
