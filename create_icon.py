#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regenerate NextPDF Pro icon assets from resources/icons/NextPDF-Pro.svg.

Renders 16/24/32/48/64/128/256 px PNGs with Qt's SVG renderer and packs them
into a true multi-resolution Windows ICO.  Run from the project root:

    python create_icon.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(PROJECT_ROOT, "resources", "icons")
SVG_PATH = os.path.join(ICONS, "NextPDF-Pro.svg")
SIZES = [16, 24, 32, 48, 64, 128, 256, 512]


def main() -> int:
    if not os.path.exists(SVG_PATH):
        print(f"Missing {SVG_PATH}")
        return 1

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    renderer = QSvgRenderer(SVG_PATH)
    if not renderer.isValid():
        print(f"Invalid SVG: {SVG_PATH}")
        return 1

    frames = []
    for size in SIZES:
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        renderer.render(painter)
        painter.end()
        path = os.path.join(ICONS, f"NextPDF-Pro-{size}.png")
        image.save(path)
        if size <= 256:
            frames.append(path)
        if size == 256:
            image.save(os.path.join(ICONS, "NextPDF-Pro.png"))
        print(f"wrote {path}")

    # Pillow is only needed for packing the ICO; it is not a runtime dependency.
    try:
        from PIL import Image
    except ImportError:
        print("Pillow is required to pack the ICO: python -m pip install pillow")
        return 1

    ico_path = os.path.join(ICONS, "NextPDF-Pro.ico")
    pack_ico(frames, ico_path)
    print(f"wrote {ico_path} ({os.path.getsize(ico_path)} bytes)")
    return 0


def pack_ico(frames, target):
    """Pack the genuinely rendered PNG frames into a multi-resolution ICO.

    Pillow's ICO writer resamples a single image; this writes each frame at its
    native size so 16 px stays crisp instead of being a downscaled 256 px blur.
    """
    import struct

    payloads = []
    for frame in frames:
        with open(frame, "rb") as handle:
            payloads.append((int(os.path.basename(frame).split("-")[-1].split(".")[0]), handle.read()))
    payloads.sort(key=lambda item: item[0])
    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = 6 + 16 * len(payloads)
    directory = b""
    for size, data in payloads:
        directory += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32,
                                 len(data), offset)
        offset += len(data)
    with open(target, "wb") as handle:
        handle.write(header + directory + b"".join(data for _, data in payloads))


if __name__ == "__main__":
    sys.exit(main())
