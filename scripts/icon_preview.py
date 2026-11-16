"""Lay out the real icon PNGs at their true pixel sizes (no upscaling)."""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "resources", "icons")
SIZES = [16, 24, 32, 48, 64, 128, 256]

light = Image.new("RGB", (760, 360), "#F1F5F9")
dark = Image.new("RGB", (760, 200), "#0F172A")
for canvas, text in ((light, "#334155"), (dark, "#E2E8F0")):
    draw = ImageDraw.Draw(canvas)
    x = 24
    for size in SIZES:
        if size > 128 and canvas is dark:
            continue
        icon = Image.open(os.path.join(ICONS, f"NextPDF-Pro-{size}.png")).convert("RGBA")
        assert icon.size == (size, size), icon.size
        canvas.paste(icon, (x, 24), icon)
        draw.text((x, 28 + max(size, 128)), f"{size}px", fill=text)
        x += size + 32
light.save(os.path.join(ROOT, "docs", "evidence", "icon_preview_light.png"))
dark.save(os.path.join(ROOT, "docs", "evidence", "icon_preview_dark.png"))
print("previews written")
