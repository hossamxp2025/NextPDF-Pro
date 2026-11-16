#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Text engine for NextPDF Pro.

Real text insertion/replacement inside PDF content, with correct Arabic
shaping and bidirectional layout:

  * Layout and shaping: MuPDF Story via ``Page.insert_htmlbox`` (HarfBuzz
    shaping, RTL/LTR paragraphs, wrapping, alignment, bold/italic).
  * Searchability: MuPDF writes a ToUnicode CMap that is unusable for modern
    OpenType Arabic fonts. After every insertion the CMap of each touched font
    is rebuilt from a HarfBuzz shaping of the inserted text (glyph id -> logical
    characters) merged with the previous CMap, so text extraction, search and
    copy return logical Unicode in reading order.
  * Replacement of existing text: the original glyphs are removed with a
    text-only redaction (images and vector graphics are preserved) and the new
    text is laid out in the same rectangle.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple

import pymupdf

from src.engine.fonts import (
    FontRegistry, get_font_registry, contains_arabic, detect_direction, bidi_runs,
    normalize_arabic, glyph_unicode_map, font_glyph_unicode_map, is_presentation_form,
)

logger = logging.getLogger("NextPDF")

Color = Tuple[float, float, float]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class TextStyle:
    family: str = ""                 # empty -> registry default for the text
    size: float = 12.0
    color: Color = (0.0, 0.0, 0.0)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: str = "auto"              # auto | left | right | center | justify
    direction: str = "auto"          # auto | rtl | ltr
    line_height: float = 1.25
    opacity: float = 1.0

    def copy(self, **changes) -> "TextStyle":
        d = asdict(self)
        d.update(changes)
        return TextStyle(**d)


@dataclass
class TextSpan:
    """A span of existing text on a page (hit-testing / selection unit)."""
    text: str
    bbox: Tuple[float, float, float, float]
    font: str
    size: float
    color: Color
    bold: bool
    italic: bool
    direction: str            # rtl | ltr
    block: int
    line: int
    origin: Tuple[float, float] = (0.0, 0.0)
    page: int = 0             # 0-based

    @property
    def rect(self) -> pymupdf.Rect:
        return pymupdf.Rect(*self.bbox)


@dataclass
class TextLine:
    text: str
    bbox: Tuple[float, float, float, float]
    spans: List[TextSpan]
    direction: str
    block: int
    line: int
    dir: Tuple[float, float] = (1.0, 0.0)   # writing direction as MuPDF reports it

    @property
    def rect(self) -> pymupdf.Rect:
        return pymupdf.Rect(*self.bbox)


@dataclass
class TextInsertResult:
    success: bool
    message: str = ""
    rect: Optional[Tuple[float, float, float, float]] = None
    scale: float = 1.0
    fitted: bool = True
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ToUnicode helpers
# ---------------------------------------------------------------------------
def _utf16_decode(hexs: str) -> str:
    if not hexs:
        return ""
    if len(hexs) % 2:
        hexs = "0" + hexs
    try:
        return bytes.fromhex(hexs).decode("utf-16-be")
    except Exception:
        return ""


def _utf16_hex(s: str) -> str:
    return s.encode("utf-16-be").hex().upper()


def parse_tounicode(cmap: str) -> Dict[int, str]:
    """Parse bfchar/bfrange sections of a ToUnicode CMap into {cid: text}."""
    m: Dict[int, str] = {}
    for blk in re.finditer(r"beginbfchar(.*?)endbfchar", cmap, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blk.group(1)):
            m[int(src, 16)] = _utf16_decode(dst)
    for blk in re.finditer(r"beginbfrange(.*?)endbfrange", cmap, re.S):
        for lo, hi, rest in re.findall(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)", blk.group(1)):
            lo_i, hi_i = int(lo, 16), int(hi, 16)
            if hi_i - lo_i > 65535:
                continue
            if rest.startswith("["):
                for i, d in enumerate(re.findall(r"<([0-9A-Fa-f]*)>", rest)):
                    m[lo_i + i] = _utf16_decode(d)
            else:
                d = _utf16_decode(rest.strip("<>"))
                if not d:
                    continue
                base = ord(d[-1])
                for c in range(lo_i, hi_i + 1):
                    m[c] = d[:-1] + chr(base + (c - lo_i))
    return m


def build_tounicode(mapping: Dict[int, str]) -> bytes:
    items = sorted(mapping.items())
    out = ["/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
           "/CIDSystemInfo <</Registry(Adobe)/Ordering(UCS)/Supplement 0>> def\n"
           "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
           "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"]
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        out.append(f"{len(chunk)} beginbfchar\n")
        for cid, s in chunk:
            out.append(f"<{cid:04X}> <{_utf16_hex(s) if s else '0000'}>\n")
        out.append("endbfchar\n")
    out.append("endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n")
    return "".join(out).encode("latin-1")


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class TextEngine:
    """Stateless helper operating on pymupdf pages."""

    def __init__(self, registry: Optional[FontRegistry] = None):
        self.registry = registry or get_font_registry()

    # -- extraction ----------------------------------------------------------
    def extract_lines(self, page: pymupdf.Page) -> List[TextLine]:
        """Lines and spans of a page with normalised logical text."""
        lines: List[TextLine] = []
        try:
            d = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_LIGATURES | pymupdf.TEXT_PRESERVE_WHITESPACE
                              | pymupdf.TEXT_MEDIABOX_CLIP)
        except Exception as e:
            logger.error("text extraction failed: %s", e)
            return lines
        pno = page.number
        for b_i, block in enumerate(d.get("blocks", [])):
            if block.get("type") != 0:
                continue
            for l_i, line in enumerate(block.get("lines", [])):
                spans: List[TextSpan] = []
                for sp in line.get("spans", []):
                    text = normalize_arabic(sp.get("text", "")).replace("\xa0", " ").replace("\xad", "-")
                    if not text.strip():
                        continue
                    col = sp.get("color", 0)
                    if isinstance(col, int):
                        color = (((col >> 16) & 255) / 255.0, ((col >> 8) & 255) / 255.0, (col & 255) / 255.0)
                    else:
                        color = tuple(float(c) for c in col[:3]) if col else (0.0, 0.0, 0.0)
                    fontname = sp.get("font", "")
                    flags = sp.get("flags", 0)
                    spans.append(TextSpan(
                        text=text, bbox=tuple(sp["bbox"]), font=fontname, size=float(sp.get("size", 12)),
                        color=color, bold=bool(flags & 16) or "bold" in fontname.lower(),
                        italic=bool(flags & 2) or "italic" in fontname.lower() or "oblique" in fontname.lower(),
                        direction=detect_direction(text), block=b_i, line=l_i,
                        origin=tuple(sp.get("origin", (0, 0))), page=pno))
                if spans:
                    text = " ".join(s.text for s in spans) if len(spans) > 1 else spans[0].text
                    ldir = tuple(float(v) for v in line.get("dir", (1, 0)))
                    lines.append(TextLine(text=text, bbox=tuple(line["bbox"]), spans=spans,
                                          direction=detect_direction(text), block=b_i, line=l_i,
                                          dir=ldir))
        return self._merge_visual_lines(lines)

    @staticmethod
    def _merge_visual_lines(lines: List[TextLine]) -> List[TextLine]:
        """MuPDF often reports one visual line as several 'lines' (bidi segments,
        large gaps). Merge entries of the same block whose vertical extents
        overlap substantially, ordering segments visually by direction."""
        if not lines:
            return lines
        merged: List[List[TextLine]] = []
        for ln in lines:
            placed = False
            for group in merged:
                g0 = group[0]
                if g0.block != ln.block or g0.dir != ln.dir:
                    continue
                gy0 = min(g.bbox[1] for g in group); gy1 = max(g.bbox[3] for g in group)
                overlap = min(gy1, ln.bbox[3]) - max(gy0, ln.bbox[1])
                h = min(gy1 - gy0, ln.bbox[3] - ln.bbox[1])
                if h > 0 and overlap / h > 0.6:
                    group.append(ln)
                    placed = True
                    break
            if not placed:
                merged.append([ln])
        out: List[TextLine] = []
        for group in merged:
            if len(group) == 1:
                out.append(group[0])
                continue
            rtl_w = sum(g.bbox[2] - g.bbox[0] for g in group if g.direction == "rtl")
            ltr_w = sum(g.bbox[2] - g.bbox[0] for g in group if g.direction == "ltr")
            direction = "rtl" if rtl_w >= ltr_w else "ltr"
            group.sort(key=lambda g: g.bbox[2], reverse=(direction == "rtl"))
            spans = [s for g in group for s in g.spans]
            text = " ".join(g.text.strip() for g in group)
            bbox = (min(g.bbox[0] for g in group), min(g.bbox[1] for g in group),
                    max(g.bbox[2] for g in group), max(g.bbox[3] for g in group))
            out.append(TextLine(text=text, bbox=bbox, spans=spans, direction=direction,
                                block=group[0].block, line=group[0].line, dir=group[0].dir))
        out.sort(key=lambda l: (l.block, l.bbox[1], l.bbox[0]))
        return out

    def extract_spans(self, page: pymupdf.Page) -> List[TextSpan]:
        return [s for ln in self.extract_lines(page) for s in ln.spans]

    @staticmethod
    def span_at(spans: Sequence[TextSpan], x: float, y: float, tolerance: float = 2.0) -> Optional[TextSpan]:
        pt = pymupdf.Point(x, y)
        for s in spans:
            r = pymupdf.Rect(s.bbox)
            r.x0 -= tolerance; r.y0 -= tolerance; r.x1 += tolerance; r.y1 += tolerance
            if r.contains(pt):
                return s
        return None

    @staticmethod
    def line_at(lines: Sequence[TextLine], x: float, y: float, tolerance: float = 2.0) -> Optional[TextLine]:
        pt = pymupdf.Point(x, y)
        for ln in lines:
            r = pymupdf.Rect(ln.bbox)
            r.x0 -= tolerance; r.y0 -= tolerance; r.x1 += tolerance; r.y1 += tolerance
            if r.contains(pt):
                return ln
        return None

    # -- insertion -----------------------------------------------------------
    @staticmethod
    def css_align(physical: str, direction: str) -> str:
        """Translate a physical side into the keyword MuPDF needs.

        MuPDF resolves ``text-align`` against the paragraph direction, so under
        ``dir="rtl"`` the keyword is mirrored: asking for ``right`` pins the
        text to the left edge of the box.  Measured on PyMuPDF 2.1 / MuPDF
        1.28.6 (2026-11-16): an RTL line in a 400 pt box with ``text-align:
        right`` started at the box's left edge, with ``left`` it ended exactly
        at the right edge.  The engine's public ``align`` stays physical and
        only the emitted keyword is flipped.
        """
        if direction == "rtl":
            return {"right": "left", "left": "right"}.get(physical, physical)
        return physical

    def build_html(self, text: str, style: TextStyle) -> Tuple[str, str, List[str]]:
        """Return (html, css, families_used).

        Runs of a script the chosen family cannot render are wrapped in a span
        that names a bundled family which can, so every glyph comes from a
        font whose text layer we control (see FontRegistry.script_fallback).
        """
        family = self.registry.resolve_family(style.family, text)
        ar_fb = self.registry.script_fallback(family, arabic=True) if family else None
        lat_fb = self.registry.script_fallback(family, arabic=False) if family else None
        families = [f for f in (family, ar_fb, lat_fb) if f]
        faces_css, stack = self.registry.css_font_faces(families[:1])
        fb_stacks: Dict[str, str] = {}
        for fb in (ar_fb, lat_fb):
            if fb and fb not in fb_stacks:
                fb_css, fb_stack = self.registry.css_font_faces([fb])
                fb_stacks[fb] = fb_stack
                for rule in fb_css.splitlines():
                    if rule and rule not in faces_css:
                        faces_css += "\n" + rule
        r, g, b = (max(0, min(1, c)) for c in style.color)
        color = f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})"
        base_dir = style.direction if style.direction in ("rtl", "ltr") else detect_direction(text)
        if style.align == "auto":
            align = "right" if base_dir == "rtl" else "left"
        else:
            align = style.align
        weight = "bold" if style.bold else "normal"
        fstyle = "italic" if style.italic else "normal"
        deco = "underline" if style.underline else "none"
        css = (f"{faces_css}\n"
               f"body {{ margin:0; padding:0; }}\n"
               f"p {{ margin:0; padding:0; font-family:{stack}; font-size:{style.size}pt; color:{color};"
               f" font-weight:{weight}; font-style:{fstyle}; text-decoration:{deco};"
               f" line-height:{style.line_height};"
               f" text-align:{self.css_align(align, base_dir)}; }}\n")
        def render_runs(para: str) -> str:
            if not (ar_fb or lat_fb):
                return html.escape(para)
            parts = []
            for run, rtl in bidi_runs(para):
                needs_ar = contains_arabic(run)
                fb = ar_fb if needs_ar else (lat_fb if any(c.isalpha() for c in run) else None)
                esc = html.escape(run)
                if fb:
                    parts.append(f"<span style='font-family:{fb_stacks[fb]}'>{esc}</span>")
                else:
                    parts.append(esc)
            return "".join(parts)

        paras = []
        for para in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            pdir = base_dir if style.direction != "auto" else (detect_direction(para) if para.strip() else base_dir)
            palign = align if style.align != "auto" else ("right" if pdir == "rtl" else "left")
            content = render_runs(para) if para.strip() else "&nbsp;"
            paras.append(f'<p dir="{pdir}" style="text-align:{self.css_align(palign, pdir)}">'
                         f'{content}</p>')
        return "".join(paras), css, families

    def insert_text(self, page: pymupdf.Page, rect: pymupdf.Rect, text: str, style: TextStyle,
                    shrink_to_fit: bool = True, rotate: int = 0,
                    scale_low: Optional[float] = None) -> TextInsertResult:
        """Insert ``text`` laid out inside ``rect``. Returns the used rectangle."""
        if not text or not text.strip():
            return TextInsertResult(False, "empty text")
        rect = pymupdf.Rect(rect)
        if rect.is_empty or rect.width < 2:
            return TextInsertResult(False, "rectangle too small")
        html_s, css, families = self.build_html(text, style)
        fonts_before = {f[0] for f in page.get_fonts(full=True)}
        if scale_low is None:
            scale_low = 0.4 if shrink_to_fit else 1.0
        try:
            spare, scale = page.insert_htmlbox(
                rect, html_s, css=css, archive=self.registry.archive(),
                scale_low=scale_low, rotate=rotate, opacity=style.opacity)
        except Exception as e:
            logger.error("insert_htmlbox failed: %s", e)
            return TextInsertResult(False, f"insert failed: {e}")
        warnings: List[str] = []
        fitted = spare >= 0
        if not fitted:
            warnings.append("text does not fit the box")
        if scale < 0.999:
            warnings.append(f"text scaled to {scale:.0%} to fit")
        self._rebuild_tounicode(page, [text], fonts_before)
        used = pymupdf.Rect(rect)
        if fitted and spare > 0:
            used.y1 = used.y1 - spare
        return TextInsertResult(True, "ok", rect=tuple(used), scale=scale, fitted=fitted, warnings=warnings)

    def replace_text(self, page: pymupdf.Page, old_rects: Sequence[pymupdf.Rect], new_text: str,
                     style: TextStyle, target_rect: Optional[pymupdf.Rect] = None,
                     fill: Optional[Color] = None) -> TextInsertResult:
        """Remove text under ``old_rects`` (text only) and lay out ``new_text``.

        ``target_rect`` defaults to the union of ``old_rects`` grown downwards
        so longer replacements still fit; ``fill`` paints a background behind
        the removed text (None keeps the page background untouched).
        """
        if not old_rects:
            return TextInsertResult(False, "nothing to replace")
        union = pymupdf.Rect(old_rects[0])
        for r in old_rects[1:]:
            union |= pymupdf.Rect(r)
        for r in old_rects:
            rr = pymupdf.Rect(r)
            rr.y0 += 0.5; rr.y1 -= 0.5  # avoid touching neighbouring lines
            try:
                page.add_redact_annot(rr, fill=fill if fill else False)
            except Exception as e:
                return TextInsertResult(False, f"redaction failed: {e}")
        try:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                  text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        except TypeError:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        except Exception as e:
            return TextInsertResult(False, f"redaction failed: {e}")
        if not new_text.strip():
            return TextInsertResult(True, "deleted", rect=tuple(union))
        if target_rect is None:
            target_rect = self._fit_target_rect(page, union, new_text, style)
        res = self.insert_text(page, target_rect, new_text, style, shrink_to_fit=True)
        return res

    def _fit_target_rect(self, page: pymupdf.Page, union: pymupdf.Rect, text: str,
                         style: TextStyle) -> pymupdf.Rect:
        """Box for replacement text, anchored on the line it replaces.

        Horizontally the rectangle grows towards the free side (left for RTL,
        right for LTR) within the page margins; vertically it is offset so the
        new glyphs start on the same line as the old ones (see measure_box).
        """
        margin = 18.0
        page_r = page.rect
        direction = style.direction if style.direction in ("rtl", "ltr") else detect_direction(text)
        single = "\n" not in text.strip()
        need_w, _, _ = self.measure_box(text, style, width=10000 if single else union.width)
        need_w += 1.0  # guard against a rounding-induced wrap
        rect = pymupdf.Rect(union)
        if need_w > rect.width:
            extra = need_w - rect.width
            if direction == "rtl":
                rect.x0 = max(page_r.x0 + margin, rect.x0 - extra)
                if need_w > rect.width:
                    rect.x1 = min(page_r.x1 - margin, rect.x0 + need_w)
            else:
                rect.x1 = min(page_r.x1 - margin, rect.x1 + extra)
                if need_w > rect.width:
                    rect.x0 = max(page_r.x0 + margin, rect.x1 - need_w)
        _, h_at_width, top = self.measure_box(text, style, width=rect.width)
        rect.y0 = max(page_r.y0 + 1.0, union.y0 - top)
        rect.y1 = min(page_r.y1 - 2.0, rect.y0 + max(h_at_width, union.height) + 1.0)
        return rect

    def delete_text(self, page: pymupdf.Page, rects: Sequence[pymupdf.Rect]) -> bool:
        res = self.replace_text(page, rects, "", TextStyle())
        return res.success

    # -- ToUnicode -----------------------------------------------------------
    # Story embeds a fresh copy of the font on every insert_htmlbox call.
    # Re-pointing font resources to one shared copy was tried and is unsafe
    # with PyMuPDF 2.1 (xref_set_key writes a placeholder instead of the
    # reference and the text renders with a fallback font), so the copies are
    # left alone here and collapsed at save time with Document.subset_fonts(),
    # which keeps the ToUnicode maps intact (verified: 6 full fonts, 695 KB ->
    # 124 KB, identical extraction and search).

    def _rebuild_tounicode(self, page: pymupdf.Page, texts: List[str], fonts_before: set):
        """Rewrite the ToUnicode CMap of every Story font on the page.

        For fonts we know (registry faces) the map is rebuilt from scratch:
        the font's own cmap + GSUB-derived map covers every glyph MuPDF may
        emit, and a HarfBuzz shaping of the inserted texts refines ligature
        clusters.  Entries MuPDF wrote are only kept for glyphs neither source
        knows about.
        """
        doc = page.parent
        try:
            fonts = page.get_fonts(full=True)
        except Exception:
            return
        for f in fonts:
            xref, basefont = f[0], f[3]
            if not self._is_story_font(f):
                continue
            if xref in fonts_before and not getattr(doc, "_npf_rebuild_all", False):
                continue
            face = self.registry.face_for_basefont(basefont)
            try:
                tu = doc.xref_get_key(xref, "ToUnicode")
            except Exception:
                continue
            if tu[0] != "xref":
                continue
            tx = int(tu[1].split()[0])
            try:
                old = doc.xref_stream(tx).decode("latin-1", "replace")
            except Exception:
                continue
            mupdf_map = parse_tounicode(old)
            # normalise whatever MuPDF wrote (presentation forms -> logical)
            mupdf_map = {cid: normalize_arabic(s).replace("\xa0", " ").replace("\xad", "-")
                         for cid, s in mupdf_map.items()}
            if face is None:
                mapping = mupdf_map
            else:
                mapping = dict(font_glyph_unicode_map(face.path))
                for gid, s in glyph_unicode_map(face.path, texts).items():
                    if s or gid not in mapping:
                        mapping[gid] = s
                for gid, s in mupdf_map.items():
                    mapping.setdefault(gid, s)
            try:
                doc.update_stream(tx, build_tounicode(mapping))
            except Exception as e:
                logger.warning("ToUnicode update failed for %s: %s", basefont, e)

    def repair_text_layer(self, doc: pymupdf.Document, texts: Sequence[str]) -> int:
        """Rebuild the ToUnicode maps of every Story font in ``doc``.

        Used for documents produced by MuPDF's Story/DocumentWriter outside
        the page editor (Create PDF from text/Office).  ``texts`` are the
        strings that were laid out; they refine ligature clusters.  Returns
        the number of pages processed.
        """
        n = 0
        try:
            doc._npf_rebuild_all = True
        except Exception:
            pass
        try:
            for page in doc:
                self._rebuild_tounicode(page, list(texts), set())
                n += 1
        finally:
            try:
                doc._npf_rebuild_all = False
            except Exception:
                pass
        return n

    @staticmethod
    def _is_story_font(font_tuple) -> bool:
        # Story fonts are Type0/Identity-H with a /ToUnicode; we only touch those
        return len(font_tuple) > 5 and font_tuple[2] == "Type0" and font_tuple[5] == "Identity-H"

    # -- measuring -----------------------------------------------------------
    def measure(self, text: str, style: TextStyle, width: float = 10000) -> Tuple[float, float]:
        """(width, height) of text laid out at ``width``."""
        w, h, _ = self.measure_box(text, style, width)
        return (w, h)

    def measure_box(self, text: str, style: TextStyle,
                    width: float = 10000) -> Tuple[float, float, float]:
        """Lay ``text`` out at ``width`` and return (width, height, top).

        ``width`` and ``height`` are the glyph extent and the vertical space
        the layout consumes.  ``top`` is the signed offset from the top of the
        layout box to the top of the first line's glyphs; it is negative,
        because ascenders and Arabic diacritics reach above the line box (6.3
        pt for Noto Sans Arabic at 14 pt, 2.0 pt for Noto Sans).  A caller that
        wants the glyphs to start at a given y places the box at ``y - top``.
        """
        fallback = (len(text) * style.size * 0.55, style.size * style.line_height, 0.0)
        try:
            tmp = pymupdf.open()
            page = tmp.new_page(width=max(width, 10) + 20, height=5000)
            html_s, css, _ = self.build_html(text, style)
            rect = pymupdf.Rect(10, 10, 10 + max(width, 10), 4990)
            spare, _ = page.insert_htmlbox(rect, html_s, css=css, archive=self.registry.archive(), scale_low=1)
            h = rect.height - spare if spare >= 0 else rect.height
            # Extent of all text: MuPDF reports one bidi line as several
            # blocks, so take their union rather than the widest block.
            x0 = x1 = y0 = None
            for b in page.get_text("blocks"):
                x0 = b[0] if x0 is None else min(x0, b[0])
                x1 = b[2] if x1 is None else max(x1, b[2])
                y0 = b[1] if y0 is None else min(y0, b[1])
            w = (x1 - x0) if x0 is not None else 0.0
            top = (y0 - rect.y0) if y0 is not None else 0.0
            tmp.close()
            return (w or min(width, fallback[0]), h, top)
        except Exception:
            logger.debug("measure failed", exc_info=True)
            return fallback


_engine: Optional[TextEngine] = None


def get_text_engine() -> TextEngine:
    global _engine
    if _engine is None:
        _engine = TextEngine()
    return _engine
