"""Explicit, limited PDF exports; source is an immutable document snapshot.

Text exports use the PDF's logical text layer. Shaped presentation-form Arabic
is refused rather than silently reversed. Image exports preserve appearance;
HTML is a text reflow, not layout reconstruction. SVG preserves vector layout.
"""
import html
import io
import json
import csv
import re
import unicodedata
from pathlib import Path
import pymupdf as fitz
from PIL import Image

SUPPORTED = {"png", "jpg", "tiff", "webp", "txt", "html", "md", "svg", "json",
             "docx", "docx_editable", "pptx", "pptx_editable", "xlsx", "csv"}

ARABIC_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
                 (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def _is_arabic(char):
    code = ord(char)
    return any(start <= code <= end for start, end in ARABIC_RANGES)


def _is_presentation_form(text):
    return any(0xFB50 <= ord(char) <= 0xFDFF or 0xFE70 <= ord(char) <= 0xFEFF
               for char in text)


# Scripts that a plain Arabic/English document never contains.  A PDF whose
# text layer is a bare glyph-id dump leaks these code points, because the raw
# CID is returned as if it were Unicode.  Latin-1 accents are excluded so real
# French/Spanish text is never mistaken for damage.
_CID_DUMP_RANGES = ((0x0100, 0x024F), (0x0300, 0x036F), (0x0370, 0x03FF),
                    (0x0400, 0x04FF), (0x0530, 0x058F), (0x0590, 0x05FF),
                    (0x10A0, 0x10FF))
_REPLACEMENT_CHAR = 0xFFFD

# Characters whose left-to-right order must survive a visual -> logical flip.
_LTR_CHARS = frozenset("0123456789"
                       "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                       "abcdefghijklmnopqrstuvwxyz")
_LTR_INNER = frozenset("-.,/:")
_MIRRORED = {")": "(", "(": ")", "]": "[", "[": "]", "}": "{", "{": "}",
             "»": "«", "«": "»"}


def _looks_like_cid_dump(text):
    """True when text is mostly code points no Arabic/English PDF would use."""
    visible = [char for char in text if char.isprintable() and not char.isspace()]
    if len(visible) < 4:
        return False
    suspicious = 0
    for char in visible:
        code = ord(char)
        if code == _REPLACEMENT_CHAR or any(
                start <= code <= end for start, end in _CID_DUMP_RANGES):
            suspicious += 1
    return suspicious / len(visible) >= 0.30


def _visual_line(line):
    """Flip one stored visual-order line back to logical order.

    Reversing the whole line restores Arabic order, but it also reverses the
    runs of digits and Latin text that were already left-to-right (a date would
    become ``6202-11-61``).  Each such run is reversed a second time, and
    mirrored brackets are corrected.
    """
    reversed_line = line[::-1]
    pieces = []
    index, length = 0, len(reversed_line)
    while index < length:
        if reversed_line[index] in _LTR_CHARS:
            end = index
            while end < length and (reversed_line[end] in _LTR_CHARS or (
                    reversed_line[end] in _LTR_INNER and end + 1 < length
                    and reversed_line[end + 1] in _LTR_CHARS)):
                end += 1
            stop = end
            while stop > index and reversed_line[stop - 1] in _LTR_INNER:
                stop -= 1
            pieces.append(reversed_line[index:stop][::-1])
            pieces.append(reversed_line[stop:end][::-1])
            index = end
        else:
            pieces.append(reversed_line[index])
            index += 1
    flipped = "".join(pieces)
    return unicodedata.normalize("NFKC", "".join(_MIRRORED.get(c, c) for c in flipped))


def _visual_to_logical(text):
    return "\n".join(_visual_line(line) for line in text.split("\n"))


def _gid_to_unicode(font_bytes):
    """Map glyph id -> Unicode through the embedded font's own cmap."""
    if not font_bytes:
        return {}
    try:
        from fontTools.ttLib import TTFont
        font = TTFont(io.BytesIO(font_bytes), lazy=True)
    except Exception:
        return {}
    try:
        cmap = font.getBestCmap() or {}
        order = font.getGlyphOrder()
        gid_of = {name: index for index, name in enumerate(order)}
        mapping = {}
        for code, name in cmap.items():
            gid = gid_of.get(name)
            if gid is not None and gid not in mapping:
                mapping[gid] = code
        return mapping
    except Exception:
        return {}
    finally:
        try:
            font.close()
        except Exception:
            pass


class _TextRepair:
    """Recover real Unicode from fonts that ship no ToUnicode map.

    A Type0/Identity-H font without /ToUnicode makes a text extractor return
    ``chr(cid)``.  The CID equals the glyph id, so the embedded font program's
    cmap turns it back into the original code point.  Nothing is invented: when
    the font is missing or too many glyphs are unmapped the caller is told, and
    the export is refused rather than written corrupted.
    """

    def __init__(self, doc):
        self.doc = doc
        self._pages = {}

    def maps_for(self, page):
        number = page.number
        if number in self._pages:
            return self._pages[number]
        fonts = {}
        for info in page.get_fonts(full=True):
            xref, _ext, _type, basefont = info[0], info[1], info[2], info[3]
            encoding = info[5] if len(info) > 5 else ""
            if encoding not in ("Identity-H", "Identity-V"):
                continue
            try:
                if "/ToUnicode" in self.doc.xref_object(xref):
                    continue
                _name, _ext, _type, font_bytes = self.doc.extract_font(xref)
            except Exception:
                continue
            mapping = _gid_to_unicode(font_bytes)
            if not mapping:
                continue
            fonts[basefont] = mapping
            fonts.setdefault(basefont.split("+")[-1], mapping)
        self._pages[number] = fonts
        return fonts

    def _map(self, page, characters):
        """characters: iterable of (char, font_name).  Returns text, used, ratio."""
        fonts = self.maps_for(page)
        pieces = []
        used = False
        total = missing = 0
        for char, font_name in characters:
            mapping = fonts.get(font_name or "")
            if mapping:
                used = True
                code = ord(char)
                if code in mapping:
                    char = chr(mapping[code])
                elif char.isprintable() and not char.isspace():
                    missing += 1
            if char.isprintable() and not char.isspace():
                total += 1
            pieces.append(char)
        return "".join(pieces), used, (missing / total if total else 0.0)

    def line_text(self, page, spans):
        """Repair a whole visual-order line; spans may split a single line."""
        ordered = sorted(spans, key=lambda span: span.get("bbox", [0, 0, 0, 0])[0])
        fonts = self.maps_for(page)
        pieces = []
        used = False
        total = missing = 0
        for span in ordered:
            mapping = fonts.get(span.get("font", ""))
            for char in span.get("text", ""):
                code = ord(char)
                if mapping:
                    used = True
                    if code in mapping:
                        char = chr(mapping[code])
                    elif char.isprintable() and not char.isspace():
                        missing += 1
                if char.isprintable() and not char.isspace():
                    total += 1
                pieces.append(char)
        text = "".join(pieces)
        if not used:
            return _logical_text(text)
        if total and missing / total > 0.10:
            raise ValueError("This PDF embeds a font without a usable Unicode "
                             "map; editable export would corrupt the text. "
                             "Use layout mode.")
        if any(_is_arabic(char) for char in text) or _is_presentation_form(text):
            return _visual_to_logical(text)
        if _looks_like_cid_dump(text):
            raise ValueError("This PDF has no usable Unicode text map; editable "
                             "export would corrupt the text. Use layout mode.")
        return text

    def cell_text(self, page, chars):
        ordered = sorted(chars, key=lambda ch: (round(ch["origin"][1], 1),
                                                ch["origin"][0]))
        lines = {}
        pieces = []
        for char in ordered:
            pieces.append((char["c"], char.get("font", "")))
        mapped, used, ratio = self._map(page, pieces)
        if not used:
            return None
        if ratio > 0.10:
            raise ValueError("This PDF embeds a font without a usable Unicode "
                             "map; table export would corrupt the text. "
                             "Use layout mode.")
        index = 0
        for char in ordered:
            lines.setdefault(round(char["origin"][1], 1), []).append(mapped[index])
            index += 1
        text = "\n".join("".join(group) for _, group in sorted(lines.items()))
        return _visual_to_logical(text).strip()


def _logical_text(text):
    """Return text that can be re-typed logically, or refuse a damaged layer.

    Proper office PDFs store logical Unicode, which is passed through unchanged.
    Some generators store shaped Arabic in visual order with a valid ToUnicode
    map; for a line that is purely Arabic prose, reversing the line restores
    logical order exactly.  A PDF whose font has no ToUnicode map yields a bare
    glyph-id dump (Latin Extended, Cyrillic, Hebrew ...) which no amount of
    reversal can repair, so those lines are refused instead of emitting
    corrupted text.
    """
    cleaned = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
    if _looks_like_cid_dump(cleaned):
        raise ValueError("This PDF has no usable Unicode text map (damaged "
                         "encoding); editable export would corrupt it. "
                         "Use layout mode.")
    if not _is_presentation_form(cleaned):
        return cleaned
    # A broken ToUnicode map leaks accented Latin characters into the line.
    if any(0x80 <= ord(char) <= 0x9F or 0xC0 <= ord(char) <= 0x24F for char in cleaned):
        raise ValueError("Arabic text uses a damaged visual encoding; "
                         "editable export would corrupt it. Use layout mode.")
    normalized = unicodedata.normalize("NFKC", cleaned)
    if any(char.isascii() and char.isalnum() for char in normalized):
        raise ValueError("This Arabic line mixes Latin or digits in visual order; "
                         "editable export would corrupt it. Use layout mode.")
    logical = "\n".join(line[::-1] for line in normalized.split("\n"))
    if not any(_is_arabic(char) for char in logical):
        raise ValueError("Arabic text could not be reconstructed. Use layout mode.")
    return logical


def _font_family(name):
    base = re.split(r"[-+,]", name or "")[0]
    if base in {"helv", "Helvetica"}:
        return "Arial"
    if base in {"tiro", "Times"}:
        return "Times New Roman"
    if base in {"cour", "Courier"}:
        return "Courier New"
    if base.startswith("Noto"):
        return "Segoe UI"
    return base or "Arial"


def _embedded_family(doc, xref):
    """The family name the embedded font program declares about itself."""
    try:
        _name, _ext, _type, data = doc.extract_font(xref)
    except Exception:
        return None
    if not data:
        return None
    try:
        from fontTools.ttLib import TTFont
        font = TTFont(io.BytesIO(data), lazy=True)
    except Exception:
        return None
    try:
        records = {}
        for record in font["name"].names:
            if record.nameID in (16, 1):
                try:
                    text = record.toUnicode().strip()
                except Exception:
                    continue
                if text:
                    records.setdefault(record.nameID, text)
        return records.get(16) or records.get(1)
    except Exception:
        return None
    finally:
        try:
            font.close()
        except Exception:
            pass


class _FontNames:
    """PDF font name -> a family name Word can actually resolve.

    A generator is free to call its fonts ``FontReg`` and ``FontBold``.  Word
    cannot find such a family, so every run falls back to the default font and
    the document stops resembling the PDF.  The embedded font program carries
    its real family name in its own ``name`` table, which is read once per page
    and used instead.  Nothing is guessed: a font that declares no name, or is
    not embedded at all, keeps the mapping ``_font_family`` already applied.
    """

    def __init__(self, doc):
        self.doc = doc
        self._pages = {}

    def map_for(self, page):
        number = page.number
        if number not in self._pages:
            mapping = {}
            for info in page.get_fonts(full=True):
                basefont = info[3] or ""
                family = _embedded_family(self.doc, info[0])
                if family:
                    mapping[basefont] = family
                    mapping.setdefault(basefont.split("+")[-1], family)
            self._pages[number] = mapping
        return self._pages[number]

    def family(self, page, span_font):
        if page is not None:
            resolved = self.map_for(page).get(span_font or "")
            if resolved:
                return resolved
        return _font_family(span_font)


def _run_from_span(span, text, font_family=None):
    return {
        "text": text,
        "font": font_family or _font_family(span.get("font", "")),
        "size": round(float(span.get("size", 11)), 1),
        "bold": bool(span.get("flags", 0) & 16),
        "italic": bool(span.get("flags", 0) & 2),
        "color": span.get("color", 0),
    }


def _line_runs(line, page=None, repair=None, names=None):
    spans = [span for span in line.get("spans", []) if span.get("text")]
    if not spans:
        return []

    def family(span):
        if names is None:
            return None
        return names.family(page, span.get("font", ""))

    if repair is not None and page is not None:
        fonts = repair.maps_for(page)
        if any(fonts.get(span.get("font", "")) for span in spans):
            # A visual-order line can be split across spans. Reversing each
            # span on its own would scramble word order, so the whole line is
            # repaired once and carried by the dominant span's style.
            text = repair.line_text(page, spans)
            dominant = max(spans, key=lambda span: len(span.get("text", "")))
            return [_run_from_span(dominant, text, family(dominant))]
    return [_run_from_span(span, _logical_text(span["text"]), family(span))
            for span in spans]


def _page_lines(page, repair=None):
    """Lines of a page; damaged pages join fragments on the same baseline.

    A generator can emit one visual line as several ``line`` objects (a gap
    between two glyph runs).  Repairing each fragment separately would reverse
    the word order, so fragments that sit on the same baseline and are
    horizontally adjacent are joined before the line is repaired.
    """
    lines = [line for block in page.get_text("dict")["blocks"]
             if block.get("type") == 0 for line in block.get("lines", [])]
    if repair is None or not repair.maps_for(page):
        return lines
    lines.sort(key=lambda line: ((line["bbox"][1] + line["bbox"][3]) / 2, line["bbox"][0]))
    merged = []
    for line in lines:
        centre = (line["bbox"][1] + line["bbox"][3]) / 2
        if merged:
            last = merged[-1]
            last_centre = (last["bbox"][1] + last["bbox"][3]) / 2
            gap = line["bbox"][0] - last["bbox"][2]
            if abs(last_centre - centre) <= 3 and -2 <= gap <= 24:
                last["bbox"] = (last["bbox"][0],
                                min(last["bbox"][1], line["bbox"][1]),
                                max(last["bbox"][2], line["bbox"][2]),
                                max(last["bbox"][3], line["bbox"][3]))
                last["spans"] = last["spans"] + list(line.get("spans", []))
                continue
        merged.append({"bbox": tuple(line["bbox"]), "spans": list(line.get("spans", []))})
    return merged


def _export_editable_docx(doc, pages, target, progress):
    """Real editable text with its structure: Word tables, paragraphs, images.

    A detected table becomes a real Word table carrying its column widths, cell
    shading, fonts, sizes and colours; the page lines it already accounts for
    are not repeated as paragraphs.  Everything else stays a paragraph, in page
    order, and an image is placed at the point in that order where it sits on
    the page.

    Layout is reconstructed, not reproduced: Word reflows text, so absolute
    positions and overlapping elements are not preserved.  Arabic paragraphs,
    cells and tables are marked RTL.
    """
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.section import WD_ORIENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def mark_rtl(paragraph, run=None):
        pPr = paragraph._p.get_or_add_pPr()
        pPr.append(OxmlElement("w:bidi"))
        if run is not None:
            rPr = run._element.get_or_add_rPr()
            rtl = OxmlElement("w:rtl")
            rPr.append(rtl)
            fonts = rPr.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                rPr.append(fonts)
            fonts.set(qn("w:cs"), run.font.name or "Arial")

    def tight(paragraph):
        """PDF lines carry their own spacing; Word must not add more."""
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(1)
        return paragraph

    def align(paragraph, physical, bidi):
        """Set a physical edge, allowing for Word mirroring it under ``w:bidi``.

        Measured with Word 16: in a paragraph carrying ``w:bidi``, ``w:jc``
        right lands against the left margin and left against the right one, so
        the requested edge is swapped before it is written.
        """
        if bidi:
            physical = {WD_ALIGN_PARAGRAPH.RIGHT: WD_ALIGN_PARAGRAPH.LEFT,
                        WD_ALIGN_PARAGRAPH.LEFT: WD_ALIGN_PARAGRAPH.RIGHT
                        }.get(physical, physical)
        paragraph.alignment = physical

    def style_run(run, data):
        run.font.name = data["font"]
        run.font.size = Pt(max(1.0, float(data["size"])))
        run.bold = bool(data["bold"])
        run.italic = bool(data["italic"])
        rgb = int(data["color"])
        run.font.color.rgb = RGBColor((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)

    def shading(colour):
        element = OxmlElement("w:shd")
        element.set(qn("w:val"), "clear")
        element.set(qn("w:color"), "auto")
        element.set(qn("w:fill"), colour)
        return element

    def shade(cell, colour):
        cell._tc.get_or_add_tcPr().append(shading(colour))

    def shade_paragraph(paragraph, colour):
        """Carry the band a line sits on.

        A title printed in white on a dark header band would otherwise be white
        on white: invisible, and reported by the reader as missing text.
        """
        paragraph._p.get_or_add_pPr().append(shading(colour))

    def write_table(rows, page, fills, usable_width):
        columns = max(len(row) for row in rows)
        rtl = _rows_are_rtl(rows)
        # Borderless columns are read left-to-right across the page.  A Word
        # table marked bidiVisual draws its first column on the right, so an
        # Arabic table must be written in reversed order to land as it looks.
        order = list(range(columns))
        if rtl and rows.borderless:
            order.reverse()
        widths = _column_widths(rows.cell_rects, columns, rows.cell_bounds,
                                usable_width)
        table = output.add_table(rows=len(rows), cols=columns)
        table.style = "Table Grid"
        table.autofit = False
        margins = OxmlElement("w:tblCellMar")
        for side in ("left", "right"):
            element = OxmlElement("w:" + side)
            element.set(qn("w:w"), "28")  # 1.4pt; Word's 5.4pt default steals width
            element.set(qn("w:type"), "dxa")
            margins.append(element)
        table._tbl.tblPr.append(margins)
        table.alignment = WD_TABLE_ALIGNMENT.RIGHT if rtl else WD_TABLE_ALIGNMENT.LEFT
        if rtl:
            table._tbl.tblPr.append(OxmlElement("w:bidiVisual"))
        for row_index, values in enumerate(rows):
            for position, column in enumerate(order):
                cell = table.cell(row_index, position)
                text = values[column] if column < len(values) else ""
                rect = _cell_at(rows.cell_rects, row_index, column)
                data = _cell_at(rows.cell_styles, row_index, column) or {}
                paragraph = tight(cell.paragraphs[0])
                arabic = any(_is_arabic(char) for char in text)
                if text:
                    run = paragraph.add_run(text)
                    style_run(run, {
                        "font": names.family(page, data.get("font", "")),
                        "size": data.get("size", 9),
                        "bold": data.get("bold", False),
                        "italic": data.get("italic", False),
                        "color": data.get("color", 0)})
                    if arabic:
                        mark_rtl(paragraph, run)
                paragraph.alignment = (WD_ALIGN_PARAGRAPH.RIGHT if arabic or rtl
                                       else WD_ALIGN_PARAGRAPH.LEFT)
                colour = _fill_hex(fills, rect)
                if colour:
                    shade(cell, colour)
                if widths[column]:
                    cell.width = Pt(widths[column])

    output = Document()
    repair = _TextRepair(doc)
    names = _FontNames(doc)
    first = doc[pages[0] - 1]
    section = output.sections[0]
    if first.rect.width > first.rect.height:
        section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Pt(first.rect.width)
    section.page_height = Pt(first.rect.height)
    section.left_margin = section.right_margin = Pt(36)
    section.top_margin = section.bottom_margin = Pt(36)
    usable_width = float(first.rect.width) - 72.0
    for index, number in enumerate(pages, 1):
        page = doc[number - 1]
        if index > 1:
            output.add_page_break()
        fills = _page_fills(page)
        try:
            tables = [table for table in _detected_tables(page, repair)
                      if table.bbox is not None]
        except ValueError:
            # The table reader could not trust this page's encoding.  The line
            # reader below applies the same check and refuses the export if the
            # text is unrecoverable, so nothing corrupted is ever written.
            tables = []
        items = [(table.bbox.y0, table.bbox.x0, 1, table) for table in tables]
        for line in _page_lines(page, repair):
            box = fitz.Rect(line["bbox"])
            centre = fitz.Point((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
            if any(table.bbox.contains(centre) for table in tables):
                continue
            runs = _line_runs(line, page, repair, names)
            if runs:
                items.append((box.y0, box.x0, 2, (runs, box)))
        for image in page.get_images(full=True):
            try:
                info = doc.extract_image(image[0])
                rects = page.get_image_rects(image[0])
            except (ValueError, RuntimeError):
                continue
            if not info.get("image"):
                continue
            rect = fitz.Rect(rects[0]) if rects else None
            top = rect.y0 if rect is not None else page.rect.y1
            left = rect.x0 if rect is not None else 0.0
            items.append((top, left, 0, (info, rect)))
        for _top, _left, kind, payload in _reading_order(items):
            if kind == 1:
                write_table(payload, page, fills, usable_width)
                tight(output.add_paragraph())
            elif kind == 0:
                info, rect = payload
                paragraph = tight(output.add_paragraph())
                if rect is not None:
                    paragraph.alignment = {
                        "left": WD_ALIGN_PARAGRAPH.LEFT,
                        "right": WD_ALIGN_PARAGRAPH.RIGHT,
                    }.get(_anchor(rect, page.rect), WD_ALIGN_PARAGRAPH.CENTER)
                    width = Pt(min(rect.width, usable_width))
                else:
                    width = Pt(min(120.0, usable_width))
                paragraph.add_run().add_picture(io.BytesIO(info["image"]), width=width)
            else:
                runs, box = payload
                arabic = any(_is_arabic(char) for char in
                             "".join(run["text"] for run in runs))
                paragraph = output.add_paragraph()
                # w:shd and w:bidi must precede w:spacing and w:jc in w:pPr, so
                # they are written before python-docx inserts those two.
                colour = _fill_hex(fills, box)
                if colour:
                    shade_paragraph(paragraph, colour)
                for data in runs:
                    style_run(paragraph.add_run(data["text"]), data)
                if arabic:
                    mark_rtl(paragraph, paragraph.runs[-1] if paragraph.runs else None)
                tight(paragraph)
                anchor = _anchor(box, page.rect)
                edge = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                        "right": WD_ALIGN_PARAGRAPH.RIGHT}.get(
                    anchor, WD_ALIGN_PARAGRAPH.RIGHT if arabic
                    else WD_ALIGN_PARAGRAPH.LEFT)
                align(paragraph, edge, arabic)
        if progress:
            progress(index, len(pages))
    output.save(target)


def _export_editable_pptx(doc, pages, target, progress):
    """One slide per page, each text line a real positioned text box plus images."""
    from pptx import Presentation
    from pptx.util import Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

    output = Presentation()
    output.slide_width = Pt(doc[pages[0] - 1].rect.width)
    output.slide_height = Pt(doc[pages[0] - 1].rect.height)
    repair = _TextRepair(doc)
    names = _FontNames(doc)
    for index, number in enumerate(pages, 1):
        page = doc[number - 1]
        slide = output.slides.add_slide(output.slide_layouts[6])
        for image in page.get_images(full=True):
            try:
                info = doc.extract_image(image[0])
                rects = page.get_image_rects(image[0])
            except (ValueError, RuntimeError):
                continue
            if not info.get("image") or not rects:
                continue
            rect = rects[0]
            slide.shapes.add_picture(io.BytesIO(info["image"]), Pt(rect.x0), Pt(rect.y0),
                                     Pt(rect.width), Pt(rect.height))
        for line in _page_lines(page, repair):
            runs = _line_runs(line, page, repair, names)
            if not runs:
                continue
            bbox = line["bbox"]
            width = max(24.0, bbox[2] - bbox[0] + 6)
            height = max(10.0, bbox[3] - bbox[1] + 4)
            box = slide.shapes.add_textbox(Pt(bbox[0] - 2), Pt(bbox[1] - 2), Pt(width), Pt(height))
            frame = box.text_frame
            frame.word_wrap = False
            frame.margin_left = frame.margin_right = Emu(0)
            frame.margin_top = frame.margin_bottom = Emu(0)
            frame.vertical_anchor = MSO_ANCHOR.TOP
            paragraph = frame.paragraphs[0]
            rtl = any(_is_arabic(char) for char in "".join(r["text"] for r in runs))
            if rtl:
                paragraph._p.get_or_add_pPr().set("rtl", "1")
                paragraph.alignment = PP_ALIGN.RIGHT
            for data in runs:
                run = paragraph.add_run()
                run.text = data["text"]
                run.font.size = Pt(data["size"])
                run.font.bold = data["bold"]
                run.font.italic = data["italic"]
                run.font.name = data["font"]
                rgb = data["color"]
                run.font.color.rgb = RGBColor((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)
        if progress:
            progress(index, len(pages))
    output.save(target)


def _cell_value(text, typed=True):
    text = (text or "").strip()
    if re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", text):
        return float(text) if "." in text else int(text)
    if re.fullmatch(r"-?[0-9]{1,3}(,[0-9]{3})+(\.[0-9]+)?", text):
        plain = text.replace(",", "")
        return float(plain) if "." in plain else int(plain)
    if typed:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            try:
                from datetime import date
                return date.fromisoformat(text)
            except ValueError:
                return text
        match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
        if match and 1 <= int(match.group(1)) <= 31 and 1 <= int(match.group(2)) <= 12:
            try:
                from datetime import date
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                return text
    return text


class _TableRows(list):
    """Rows of one detected table, plus how the table was found.

    ``borderless`` marks tables recovered from aligned text without ruling
    lines.  Their columns follow reading order left-to-right on the page, so a
    right-to-left table must be reversed before it is written.  A ruled grid is
    drawn where it is read, and its column order is already correct.

    ``bbox``, ``cell_rects`` and ``cell_styles`` carry the geometry and the
    dominant span style of every cell.  The spreadsheet exports ignore them;
    the Word export needs them to rebuild column widths, shading and fonts, and
    to know which page lines the table already accounts for.
    """

    borderless = False
    bbox = None
    cell_rects = ()
    cell_styles = ()
    cell_bounds = ()


def _rows_are_rtl(rows):
    return any(_is_arabic(char) for row in rows for value in row for char in (value or ""))


def _export_tables(doc, pages, target, output_format, progress):
    repair = _TextRepair(doc)
    tables = []
    for i, number in enumerate(pages, 1):
        page = doc[number - 1]
        detected = _detected_tables(page, repair)
        if detected:
            tables.extend(detected)
            if progress:
                progress(i, len(pages))
            continue
        xs, ys = set(), set()
        for drawing in page.get_drawings():
            for item in drawing["items"]:
                if item[0] != "l":
                    continue
                a, b = item[1], item[2]
                if abs(a.x - b.x) < 0.1 and abs(a.y - b.y) > 10:
                    xs.add(round(a.x, 2))
                if abs(a.y - b.y) < 0.1 and abs(a.x - b.x) > 10:
                    ys.add(round(a.y, 2))
        if len(xs) < 3 or len(ys) < 3:
            continue
        xs, ys = sorted(xs), sorted(ys)
        # Supported case: a single fully ruled rectangular grid. Refuse broken
        # rules and merged cells rather than inferring arbitrary text columns.
        vertical, horizontal = [], []
        for drawing in page.get_drawings():
            for item in drawing["items"]:
                if item[0] == "l":
                    a, b = item[1], item[2]
                    if abs(a.x-b.x) < 0.1:
                        vertical.append((round(a.x, 2), min(a.y,b.y), max(a.y,b.y)))
                    if abs(a.y-b.y) < 0.1:
                        horizontal.append((round(a.y, 2), min(a.x,b.x), max(a.x,b.x)))
        if not all(any(x == vx and lo <= ys[0]+0.1 and hi >= ys[-1]-0.1 for vx,lo,hi in vertical) for x in xs):
            continue
        if not all(any(y == hy and lo <= xs[0]+0.1 and hi >= xs[-1]-0.1 for hy,lo,hi in horizontal) for y in ys):
            continue
        raw_chars = []
        for block in page.get_text("rawdict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line["spans"]:
                    for char in span["chars"]:
                        char["font"] = span["font"]
                        raw_chars.append(char)
        rows = []
        for top, bottom in zip(ys, ys[1:]):
            row = []
            for left, right in zip(xs, xs[1:]):
                    rect = fitz.Rect(left, top, right, bottom)
                    chars = [char for char in raw_chars if rect.contains(
                        fitz.Point((char["bbox"][0]+char["bbox"][2])/2,
                                   (char["bbox"][1]+char["bbox"][3])/2))]
                    row.append(_cell_text(page, chars, rect, repair))
            rows.append(row)
        if sum(any(value.strip() for value in row) for row in rows) >= 2:
            tables.append(rows)
        if progress:
            progress(i, len(pages))
    if not tables:
        raise ValueError("No supported tables were found")
    if output_format == "csv":
        if len(tables) != 1:
            raise ValueError("CSV requires exactly one supported table")
        rows = tables[0]
        if getattr(rows, "borderless", False) and _rows_are_rtl(rows):
            rows = [list(reversed(row)) for row in rows]
        with open(target, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            for row in rows:
                values = [_cell_value(value, typed=False) for value in row]
                writer.writerow(["'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
                                 else value for value in values])
        return
    from openpyxl import Workbook
    from openpyxl.styles import Border, Side
    book = Workbook()
    book.remove(book.active)
    for index, rows in enumerate(tables, 1):
        rtl = _rows_are_rtl(rows)
        if rtl and getattr(rows, "borderless", False):
            # Borderless columns run left-to-right on the page; a right-to-left
            # table must be written in logical column order so headers keep
            # their place.  A ruled grid is already in reading order.
            rows = [list(reversed(row)) for row in rows]
        sheet = book.create_sheet(f"Table {index}")
        sheet.sheet_view.rightToLeft = rtl
        for r, row in enumerate(rows, 1):
            for c, text in enumerate(row, 1):
                value = _cell_value(text)
                cell = sheet.cell(r, c, value)
                if isinstance(value, str):
                    cell.data_type = "s"  # Never interpret PDF text as a formula.
                elif hasattr(value, "year"):
                    cell.number_format = ("yyyy-mm-dd" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", (text or "").strip())
                                          else "dd/mm/yyyy")
                cell.border = Border(**{side: Side(style="thin") for side in ("left", "right", "top", "bottom")})
    book.save(target)
    book.close()


def _median(values):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _trim_row_indices(rows):
    """Indices of the rows that really belong to a borderless table.

    Statement generators shade alternating rows, which makes PyMuPDF add an
    empty row between every real row and sometimes fold the page header into the
    grid.  The real table starts at the first row whose cells are all populated;
    everything above it belongs to the page header.  Indices are returned rather
    than rows so the parallel geometry and style lists stay aligned.
    """
    if not rows:
        return []
    width = max(len(row) for row in rows)
    start = 0
    for index, row in enumerate(rows):
        if sum(1 for value in row if value) >= width:
            start = index
            break
    else:
        threshold = max(2, int(width * 0.6))
        start = next((index for index, row in enumerate(rows)
                      if sum(1 for value in row if value) >= threshold), 0)
    return [index for index in range(start, len(rows))
            if any(value for value in rows[index])]


def _dominant_style(chars):
    """The style most of a cell's glyphs share, or None for an empty cell."""
    if not chars:
        return None
    counts = {}
    for char in chars:
        key = (round(float(char.get("size", 11)), 1), int(char.get("flags", 0)),
               int(char.get("color", 0)), char.get("font", ""))
        counts[key] = counts.get(key, 0) + 1
    (size, flags, colour, font), _ = max(counts.items(), key=lambda item: item[1])
    return {"size": size, "bold": bool(flags & 16), "italic": bool(flags & 2),
            "color": colour, "font": font}


def _union_rect(cell_rects):
    union = None
    for row in cell_rects:
        for cell in row:
            if cell is None:
                continue
            rect = fitz.Rect(cell)
            union = rect if union is None else union | rect
    return union


_ROW_TOLERANCE = 3.0


def _item_text(item):
    """Text an export item contributes, for deciding the page direction."""
    _top, _left, kind, payload = item
    if kind == 2:
        return "".join(run["text"] for run in payload[0])
    if kind == 1:
        return "".join(value or "" for row in payload for value in row)
    return ""


def _reading_order(items):
    """Page items in reading order, right-to-left on a predominantly Arabic page.

    Items are ``(top, left, kind, payload)`` with ``kind`` 0 image, 1 table,
    2 text line.  Side-by-side boxes (summary cards, a label beside its value)
    share a baseline; sorting them by ``left`` alone puts an Arabic page in
    reverse, so each band of items within ``_ROW_TOLERANCE`` of one another is
    ordered right-to-left when the page's own text is mostly Arabic.
    """
    arabic = latin = 0
    for item in items:
        for char in _item_text(item):
            if _is_arabic(char):
                arabic += 1
            elif char.isalpha():
                latin += 1
    rtl = arabic > latin
    ordered = sorted(items, key=lambda item: (item[0], item[2], item[1]))
    if not rtl:
        return ordered
    result, band = [], []
    for item in ordered:
        if band and (item[0] - band[0][0] > _ROW_TOLERANCE or item[2] != band[0][2]):
            result.extend(sorted(band, key=lambda entry: -entry[1]))
            band = []
        band.append(item)
    result.extend(sorted(band, key=lambda entry: -entry[1]))
    return result


def _anchor(box, page_rect):
    """Which page edge a block of content is anchored to, or None if it spans.

    A line pinned to one side of the page keeps that side in Word; a line that
    reaches across the page, or sits in the middle, has no anchor to keep and
    falls back to the direction of its own script.
    """
    third = page_rect.width / 3.0
    at_left = box.x0 <= page_rect.x0 + third
    at_right = box.x1 >= page_rect.x1 - third
    if at_left and not at_right:
        return "left"
    if at_right and not at_left:
        return "right"
    return None


def _cell_at(matrix, row, column):
    if row >= len(matrix):
        return None
    values = matrix[row]
    return values[column] if column < len(values) else None


# Word may not have the PDF's font installed and substitutes a wider one, so a
# column is never given exactly the width its glyphs occupied on the page.
SUBSTITUTION_ALLOWANCE = 0.12
CELL_PADDING = 6.0


def _column_widths(cell_rects, column_count, cell_bounds=(), usable_width=None):
    """Width to give every column in Word, in points.

    Two numbers describe a column: the boundary the detector drew, which sits
    midway between columns, and the widest glyph run actually inside it.  The
    boundary can be narrower than its own text (a date column measured at 39pt
    wraps ``01-11-2026`` onto two lines), so each column is given at least what
    its content needs, and the table is then fitted to the page by taking space
    from the columns that have slack above that minimum.
    """
    measured, needed = [], []
    for column in range(column_count):
        boundaries = [fitz.Rect(row[column]).width for row in cell_rects
                      if column < len(row) and row[column] is not None]
        content = [bounds[column][1] - bounds[column][0] for bounds in cell_bounds
                   if column < len(bounds) and bounds[column] is not None]
        measured.append(_median(boundaries) if boundaries else 0.0)
        widest = max(content) if content else 0.0
        needed.append(widest * (1 + SUBSTITUTION_ALLOWANCE) + CELL_PADDING
                      if widest else 0.0)
    widths = [max(pair) for pair in zip(measured, needed)]
    total = sum(widths)
    if not usable_width or total <= 0:
        return widths
    if total <= usable_width:
        factor = usable_width / total
        return [width * factor for width in widths]
    slack = total - sum(needed)
    excess = total - usable_width
    if 0 < excess <= slack:
        factor = (slack - excess) / slack
        return [need + (width - need) * factor
                for width, need in zip(widths, needed)]
    factor = usable_width / total
    return [width * factor for width in widths]


def _page_fills(page):
    """Filled rectangles usable as cell shading, smallest first.

    Page-wide bands are skipped: they are the page background or a header
    stripe, not a cell fill.
    """
    page_area = max(1.0, page.rect.width * page.rect.height)
    fills = []
    for drawing in page.get_drawings():
        colour = drawing.get("fill")
        if not colour or drawing.get("fill_opacity", 1) in (0, None):
            continue
        rect = fitz.Rect(drawing["rect"])
        area = rect.width * rect.height
        if area <= 0 or area > page_area * 0.6:
            continue
        fills.append((area, rect, tuple(float(value) for value in colour)))
    fills.sort(key=lambda item: item[0])
    return fills


def _fill_hex(fills, rect):
    """Shading colour under a cell, or None when it is unshaded or white."""
    if rect is None:
        return None
    rect = fitz.Rect(rect)
    centre = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
    for _area, box, colour in fills:
        if box.contains(centre):
            if min(colour) > 0.98:
                return None
            return "%02X%02X%02X" % tuple(
                max(0, min(255, int(round(value * 255)))) for value in colour)
    return None


def _gutter_ok(boxes, column_count):
    """Reject a borderless guess whose columns overlap on the median row."""
    gaps = []
    for column in range(column_count - 1):
        lefts, rights = [], []
        for row in boxes:
            left, right = row[column + 1], row[column]
            if left is None or right is None:
                continue
            lefts.append(left[0])
            rights.append(right[1])
        if lefts and rights:
            gaps.append(_median(lefts) - _median(rights))
    if not gaps:
        return False
    return (_median(gaps) >= 6
            and sum(1 for gap in gaps if gap > 0) >= len(gaps) * 0.75)


def _cell_text(page, chars, rect, repair=None, fallback=True):
    """Cell text, repairing glyph-id dumps when the font is embedded."""
    if not chars:
        if not fallback:
            return ""
        text = page.get_textbox(rect).strip()
        if repair is not None and _looks_like_cid_dump(text):
            return ""  # sliver cell inside a damaged page; no glyph centre lands here
        return _logical_text(text)
    if repair is not None:
        repaired = repair.cell_text(page, chars)
        if repaired is not None:
            return repaired
    text = page.get_textbox(rect).strip()
    # Plain Latin grid cells are ordered by baselines and x.  Do not apply this
    # geometry sort to Arabic logical runs.
    if not any(_is_arabic(char["c"]) for char in chars):
        baselines = {}
        for char in chars:
            baselines.setdefault(round(char["origin"][1], 1), []).append(char)
        text = "\n".join(
            "".join(char["c"] for char in sorted(group,
                                                 key=lambda ch: ch["origin"][0])).strip()
            for _, group in sorted(baselines.items()))
    return _logical_text(text)


def _detected_tables(page, repair=None):
    """Local table regions, not a page-wide Cartesian product of every rule.

    PyMuPDF joins interrupted rules and detects multiple independent tables.
    Ruled grids are tried first; a borderless statement (shaded rows, aligned
    columns, no lines) is then read with the text strategy, and finally with
    text columns over ruled horizontals.  Only rectangular unmerged grids are
    accepted, and a borderless guess must keep a real median gutter between
    columns. No OCR cells are invented.
    """
    if not page.get_text().strip():
        return []
    raw_chars = []
    for block in page.get_text("rawdict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line["spans"]:
                for char in span["chars"]:
                    char["font"] = span["font"]
                    char["size"] = span.get("size", 11)
                    char["flags"] = span.get("flags", 0)
                    char["color"] = span.get("color", 0)
                    raw_chars.append(char)
    attempts = (
        {"strategy": "lines", "min_words_vertical": 3},
        {"strategy": "text", "min_words_vertical": 3},
        {"horizontal_strategy": "text", "vertical_strategy": "lines",
         "min_words_vertical": 3},
    )
    for options in attempts:
        borderless = options.get("strategy") == "text" or "horizontal_strategy" in options
        try:
            finder = page.find_tables(use_layout=False, **options)
        except Exception:
            continue
        result = []
        for table in finder.tables:
            if table.col_count < 2 or table.row_count < 2:
                continue
            if any(cell is None for row in table.rows for cell in row.cells):
                continue  # merged/missing cell boundaries cannot be reconstructed safely
            row_rects = [fitz.Rect(row.bbox) for row in table.rows]
            row_centres = [(rect.y0 + rect.y1) / 2 for rect in row_rects]

            def row_owner(char):
                """Each glyph belongs to exactly one row, nearest its centre."""
                cy = (char["bbox"][1] + char["bbox"][3]) / 2
                best = None
                for index, (rect, centre) in enumerate(zip(row_rects, row_centres)):
                    if rect.y0 - 1 <= cy <= rect.y1 + 1:
                        distance = abs(centre - cy)
                        if best is None or distance < best[0]:
                            best = (distance, index)
                return best[1] if best is not None else None

            rows, boxes, rects, styles, bounds_by_row = [], [], [], [], []
            for row_index, row in enumerate(table.rows):
                values, bounds, cells, cell_styles = [], [], [], []
                for cell in row.cells:
                    rect = fitz.Rect(cell)
                    char_rect = rect + (0, -3, 0, 3)
                    chars = [ch for ch in raw_chars if char_rect.contains(fitz.Point(
                        (ch["bbox"][0] + ch["bbox"][2]) / 2,
                        (ch["bbox"][1] + ch["bbox"][3]) / 2))
                        and row_owner(ch) == row_index]
                    values.append(_cell_text(page, chars, rect, repair, fallback=False))
                    bounds.append((min(ch["bbox"][0] for ch in chars),
                                   max(ch["bbox"][2] for ch in chars)) if chars else None)
                    cells.append(rect)
                    cell_styles.append(_dominant_style(chars))
                if any(values):
                    rows.append(values)
                    boxes.append(bounds)
                    rects.append(cells)
                    styles.append(cell_styles)
                    bounds_by_row.append(bounds)
            if len(rows) < (3 if borderless else 2):
                continue
            if borderless:
                if not _gutter_ok(boxes, table.col_count):
                    continue
                keep = _trim_row_indices(rows)
                if len(keep) < 2:
                    continue
                rows = [rows[index] for index in keep]
                rects = [rects[index] for index in keep]
                styles = [styles[index] for index in keep]
                bounds_by_row = [bounds_by_row[index] for index in keep]
            table_rows = _TableRows(rows)
            table_rows.borderless = borderless
            table_rows.cell_rects = rects
            table_rows.cell_styles = styles
            table_rows.cell_bounds = bounds_by_row
            table_rows.bbox = _union_rect(rects)
            result.append(table_rows)
        if result:
            return result
    return []


def _export_office_images(doc, pages, target, output_format, dpi, progress):
    """Appearance-only mode: all page content becomes an image, never editable text."""
    if output_format == "docx":
        from docx import Document
        from docx.shared import Pt
        from docx.enum.section import WD_SECTION
        output = Document()
    else:
        from pptx import Presentation
        from pptx.util import Pt
        output = Presentation()
        output.slide_width = Pt(doc[pages[0] - 1].rect.width)
        output.slide_height = Pt(doc[pages[0] - 1].rect.height)
    for index, number in enumerate(pages, 1):
        page = doc[number - 1]
        image = io.BytesIO(page.get_pixmap(dpi=dpi, alpha=False).tobytes("png"))
        if output_format == "docx":
            section = output.sections[0] if index == 1 else output.add_section(WD_SECTION.NEW_PAGE)
            section.page_width, section.page_height = Pt(page.rect.width), Pt(page.rect.height)
            section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Pt(12)
            output.add_picture(image, width=Pt(page.rect.width - 24), height=Pt(page.rect.height - 24))
        else:
            slide = output.slides.add_slide(output.slide_layouts[6])
            scale = min(output.slide_width / page.rect.width, output.slide_height / page.rect.height)
            width, height = int(page.rect.width * scale), int(page.rect.height * scale)
            slide.shapes.add_picture(image, int((output.slide_width-width)/2), int((output.slide_height-height)/2), width, height)
        if progress:
            progress(index, len(pages))
    output.save(target)


def page_image_path(target, position: int, total: int) -> str:
    """Where page *position* (1-based within the selection) is written.

    One selected page keeps the name the user chose.  Several pages cannot
    share one PNG, JPEG or WEBP file, so each gets a numbered name beside it:
    ``report.png`` becomes ``report-001.png``, ``report-002.png`` and so on.
    """
    path = Path(target)
    if total <= 1:
        return str(path)
    return str(path.with_name(f"{path.stem}-{position:03d}{path.suffix}"))


def _export_images(doc, pages, target, output_format, dpi, progress):
    """Render the selected pages to raster images.

    TIFF holds every page in one file.  The other raster formats hold one
    page each, so a selection of several pages writes several files and the
    caller is told how many by the returned list.
    """
    written = []
    pillow_format = {"jpg": "JPEG", "tiff": "TIFF"}.get(
        output_format, output_format.upper())
    options = {"quality": 90} if output_format in {"jpg", "webp"} else {}
    images = []
    try:
        for index, number in enumerate(pages, 1):
            pix = doc[number - 1].get_pixmap(dpi=dpi, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if output_format == "tiff":
                images.append(image)
            else:
                path = page_image_path(target, index, len(pages))
                image.save(path, format=pillow_format, **options)
                image.close()
                written.append(path)
            if progress:
                progress(index, len(pages))
        if output_format == "tiff":
            if len(images) > 1:
                options.update(save_all=True, append_images=images[1:],
                               compression="tiff_deflate")
            images[0].save(target, format=pillow_format, **options)
            written.append(str(target))
    finally:
        for image in images:
            image.close()
    return written


def _markdown_escape(text: str) -> str:
    """Keep the writer's characters from being read as Markdown syntax."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def _markdown_inline(runs) -> str:
    """One line of text with the emphasis its spans carry."""
    parts = []
    for run in runs:
        text = _markdown_escape(run["text"])
        stripped = text.strip()
        if not stripped:
            parts.append(text)
            continue
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        marker = ""
        if run.get("bold"):
            marker += "**"
        if run.get("italic"):
            marker += "*"
        parts.append(f"{lead}{marker}{stripped}{marker[::-1]}{trail}")
    return "".join(parts).strip()


def _heading_level(size: float, body_size: float, bold: bool) -> int:
    """How many ``#`` a line of this size deserves, or 0 for body text.

    Size is the only honest signal a PDF gives: it carries no outline levels.
    A line has to stand clearly above the page's body size to become a
    heading, so ordinary text is never promoted.
    """
    if body_size <= 0:
        return 0
    ratio = size / body_size
    if ratio >= 1.6:
        return 1
    if ratio >= 1.3:
        return 2
    if ratio >= 1.15:
        return 3
    if bold and ratio >= 1.05:
        return 4
    return 0


def _markdown_table(rows, rtl: bool) -> list:
    """A detected table as a pipe table; the header row is its first row."""
    width = max(len(row) for row in rows)
    lines = []
    for index, row in enumerate(rows):
        values = [_markdown_escape((value or "").replace("\n", " ").strip())
                  for value in row]
        values += [""] * (width - len(values))
        if rtl:
            values = list(reversed(values))
        lines.append("| " + " | ".join(values) + " |")
        if index == 0:
            lines.append("| " + " | ".join(["---"] * width) + " |")
    return lines


def _export_markdown(doc, pages, target, progress, language="ara+eng"):
    """Markdown with the structure the page actually shows.

    Headings come from font size relative to the page's body size, detected
    tables become pipe tables, and bold or italic spans keep their emphasis.
    Nothing is invented: a page with one text size produces no headings.
    """
    repair = _TextRepair(doc)
    out = []
    recognised_pages = []
    for index, number in enumerate(pages, 1):
        page = doc[number - 1]
        if index > 1:
            out.append("---")
            out.append("")
        if not page.get_text().strip():
            # A scanned page has no lines and no tables to read, so the
            # recognised text is written as plain paragraphs and the page is
            # marked, rather than passed off as extracted structure.
            recognised = recognise_page(page, language)
            if not recognised.strip():
                raise ValueError("No text layer, and recognition could not "
                                 "read this page")
            recognised_pages.append(number)
            for paragraph in recognised.split("\n"):
                if paragraph.strip():
                    out.append(_markdown_escape(paragraph.strip()))
                    out.append("")
            if progress:
                progress(index, len(pages))
            continue
        try:
            tables = [table for table in _detected_tables(page, repair)
                      if table.bbox is not None]
        except ValueError:
            tables = []
        items = [(table.bbox.y0, table.bbox.x0, 1, table) for table in tables]
        sizes = []
        for line in _page_lines(page, repair):
            box = fitz.Rect(line["bbox"])
            centre = fitz.Point((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
            if any(table.bbox.contains(centre) for table in tables):
                continue
            runs = _line_runs(line, page, repair)
            if not runs or not "".join(run["text"] for run in runs).strip():
                continue
            sizes.extend(run["size"] for run in runs)
            items.append((box.y0, box.x0, 2, (runs, box)))
        body_size = _median(sizes) if sizes else 0.0
        for _top, _left, kind, payload in _reading_order(items):
            if kind == 1:
                rows = [list(row) for row in payload if any(
                    (value or "").strip() for value in row)]
                if not rows:
                    continue
                out.extend(_markdown_table(
                    rows, payload.borderless and _rows_are_rtl(rows)))
                out.append("")
                continue
            runs, _box = payload
            text = _markdown_inline(runs)
            if not text:
                continue
            size = max(run["size"] for run in runs)
            bold = all(run.get("bold") for run in runs)
            level = _heading_level(size, body_size, bold)
            out.append("#" * level + " " + text if level else text)
            out.append("")
        if progress:
            progress(index, len(pages))
    while out and not out[-1]:
        out.pop()
    if recognised_pages:
        numbers = ", ".join(str(number) for number in recognised_pages)
        out.append("")
        out.append(f"<!-- Text on page(s) {numbers} was read by recognition, "
                   f"not extracted from the file. -->")
    Path(target).write_text("\n".join(out) + "\n", encoding="utf-8")


def recognise_page(page, language="ara+eng"):
    """Read a page that carries no text layer, using the bundled engine.

    Returns the recognised text, or an empty string when recognition is
    unavailable or found nothing.  The caller decides what to do with that;
    recognised text is never silently presented as if it came from the file.
    """
    try:
        from src.engine.ocr_engine import OCREngine

        engine = OCREngine(language)
        if not engine.is_available():
            return ""
        text, _boxes = engine.ocr_page(page)
        return text or ""
    except Exception:
        logger.exception("Automatic recognition failed")
        return ""


def _text_of_page(page, language, scanned):
    """The page's own text, or recognised text for a scanned page.

    *scanned* is a list the caller passes in; the 1-based numbers of the
    pages that had to be recognised are appended to it, so the export can
    say so instead of pretending the text was extracted.
    """
    text = page.get_text()
    if text.strip():
        return text
    recognised = recognise_page(page, language)
    if recognised.strip():
        scanned.append(page.number + 1)
        return recognised
    raise ValueError("No text layer, and recognition could not read this page")


def export_pdf(data, target, pages, output_format, progress=None, dpi=150,
               language="ara+eng"):
    if output_format not in SUPPORTED or not 72 <= dpi <= 600:
        raise ValueError("Unsupported conversion options")
    if language not in {"ara", "eng", "ara+eng"}:
        raise ValueError("Unsupported conversion options")
    with fitz.open(stream=data, filetype="pdf") as doc:
        if not pages or len(set(pages)) != len(pages) or any(
            type(n) is not int or not 1 <= n <= doc.page_count for n in pages
        ):
            raise ValueError("Invalid page selection")
        if output_format == "svg" and len(pages) != 1:
            raise ValueError("This output format requires one selected page")
        if output_format in {"xlsx", "csv"}:
            _export_tables(doc, pages, target, output_format, progress)
            return
        if output_format in {"docx", "pptx"}:
            _export_office_images(doc, pages, target, output_format, dpi, progress)
            return
        if output_format == "docx_editable":
            _export_editable_docx(doc, pages, target, progress)
            return
        if output_format == "pptx_editable":
            _export_editable_pptx(doc, pages, target, progress)
            return
        if output_format in {"png", "jpg", "tiff", "webp"}:
            _export_images(doc, pages, target, output_format, dpi, progress)
            return
        if output_format == "md":
            _export_markdown(doc, pages, target, progress, language)
            return
        if output_format == "svg":
            Path(target).write_text(doc[pages[0] - 1].get_svg_image(), encoding="utf-8")
            if progress:
                progress(1, 1)
            return
        entries = []
        scanned = []
        for index, number in enumerate(pages, 1):
            page = doc[number - 1]
            text = _text_of_page(page, language, scanned)
            if any("\ufb50" <= ch <= "\ufdff" or "\ufe70" <= ch <= "\ufeff" for ch in text):
                raise ValueError("Arabic text requires logical OCR before text conversion")
            entries.append({"page": number, "width": page.rect.width,
                            "height": page.rect.height, "text": text,
                            "source": "recognised" if number in scanned else "text layer"})
            if progress:
                progress(index, len(pages))
        if output_format == "json":
            result = json.dumps({"mode": "logical-text", "pages": entries},
                                ensure_ascii=False, indent=2)
        elif output_format == "html":
            chunks = []
            for entry in entries:
                direction = "rtl" if any("\u0600" <= c <= "\u06ff" for c in entry["text"]) else "ltr"
                chunks.append(
                    f'<section dir="{direction}" data-source="{entry["source"]}">'
                    f'<pre>{html.escape(entry["text"])}</pre></section>')
            result = '<!doctype html><html><head><meta charset="utf-8"><title>PDF text export</title></head><body>' + "\n".join(chunks) + "</body></html>"
        else:
            result = "\n\n".join(entry["text"] for entry in entries)
        Path(target).write_text(result, encoding="utf-8")
