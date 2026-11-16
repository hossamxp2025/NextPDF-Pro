# -*- coding: utf-8 -*-
"""Synthetic PDF fixtures for conversion regression tests.

None of these fixtures contain real user data. They reproduce the two defects
seen in the field:

* ``build_broken_encoding_pdf`` writes a Type0/Identity-H font with **no**
  ToUnicode map, so a text extractor without CID knowledge returns glyph ids
  dressed up as Latin Extended code points (the "garbage symbols" bug).
* ``build_borderless_table_pdf`` lays out a table with shaded rows but no
  ruling lines, which ``find_tables(strategy="lines")`` cannot see.
"""
import io
import os

from fontTools.ttLib import TTFont

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "resources", "fonts")
ARABIC_FONT = os.path.join(FONT_DIR, "NotoSansArabic-Regular.ttf")


def _unicode_to_gid(font_path):
    """Return unicode -> glyph id for the font's best cmap."""
    font = TTFont(font_path, lazy=True)
    try:
        cmap = font.getBestCmap() or {}
        order = font.getGlyphOrder()
        gid_of = {name: index for index, name in enumerate(order)}
        mapping = {}
        for code, name in cmap.items():
            gid = gid_of.get(name)
            if gid is not None:
                mapping.setdefault(code, gid)
        return mapping
    finally:
        font.close()


def _build_pdf(objects, root=1):
    """Assemble numbered objects (1-based list of bytes) into a PDF."""
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % index)
        out.write(body)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n" % (len(objects) + 1))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (len(objects) + 1, root, xref))
    return out.getvalue()


def build_broken_encoding_pdf(path, logical_text, embed_font=True,
                              font_path=ARABIC_FONT):
    """Write ``logical_text`` as visual-order glyph ids with no ToUnicode map.

    The stored string is the reverse of ``logical_text`` (RTL visual order), so a
    correct repair must reverse it back. With ``embed_font=False`` the font
    program is absent and no repair is possible, which must make the text export
    refuse rather than emit garbage.
    """
    gid_of = _unicode_to_gid(font_path)
    with open(font_path, "rb") as handle:
        font_bytes = handle.read()

    visual = logical_text[::-1]
    codes = []
    for char in visual:
        gid = gid_of.get(ord(char))
        if gid is None:
            raise ValueError("font %s has no glyph for %r" % (font_path, char))
        codes.append("%04X" % gid)
    hex_string = "".join(codes).encode("ascii")

    content = b"BT /F1 16 Tf 40 780 Td <" + hex_string + b"> Tj ET"

    descriptor = (b"<< /Type /FontDescriptor /FontName /BrokenFace /Flags 4 "
                  b"/FontBBox [0 -200 1000 900] /ItalicAngle 0 "
                  b"/Ascent 900 /Descent -200 /CapHeight 700 /StemV 80")
    if embed_font:
        descriptor += b" /FontFile2 7 0 R"
    descriptor += b" >>"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
         b"/Resources << /Font << /F1 4 0 R >> >> /Contents 6 0 R >>"),
        (b"<< /Type /Font /Subtype /Type0 /BaseFont /BrokenFace "
         b"/Encoding /Identity-H /DescendantFonts [5 0 R] >>"),
        (b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /BrokenFace "
         b"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
         b"/FontDescriptor 8 0 R /CIDToGIDMap /Identity /DW 1000 >>"),
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        (b"<< /Length %d /Length1 %d >>\nstream\n"
         % (len(font_bytes), len(font_bytes)) + font_bytes + b"\nendstream"),
        descriptor,
    ]
    with open(path, "wb") as stream:
        stream.write(_build_pdf(objects))
    return path


def build_borderless_table_pdf(path):
    """Three-column table with shaded rows and no ruling lines."""
    import pymupdf as fitz

    headers = ["Date", "Description", "Amount"]
    rows = [
        ["2026-11-01", "Opening balance", "1,200.00"],
        ["2026-11-02", "Groceries", "85.50"],
        ["2026-11-03", "Salary", "3,000.00"],
        ["2026-11-04", "Fuel", "120.75"],
    ]
    doc = fitz.open()
    page = doc.new_page(width=595, height=400)
    columns = [40, 200, 380]
    top = 60
    line_height = 28
    for index in range(len(rows) + 1):
        y0 = top + index * line_height
        if index % 2 == 0:
            page.draw_rect(fitz.Rect(30, y0, 560, y0 + line_height),
                           color=None, fill=(0.92, 0.92, 0.92), width=0)
    for column, label in zip(columns, headers):
        page.insert_text((column, top + 19), label, fontsize=12)
    for row_index, row in enumerate(rows, 1):
        for column, value in zip(columns, row):
            page.insert_text((column, top + row_index * line_height + 19),
                             value, fontsize=11)
    doc.save(path)
    doc.close()
    return path
