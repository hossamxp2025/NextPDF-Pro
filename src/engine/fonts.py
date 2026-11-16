#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Font registry for NextPDF Pro.

Bundled fonts (redistributable):
  * Noto Sans Arabic (SIL OFL 1.1) Arabic, default for Arabic text
  * Noto Sans (SIL OFL 1.1)        Latin, default for Latin text
  * DejaVu Sans (Bitstream Vera)   Latin + Arabic, universal fallback

Noto Naskh Arabic ships for OCR/conversion fixtures only: MuPDF's shaping of
it cannot be mapped back to Unicode reliably (verified 2026-11-16), so it is
not offered for editing.  Amiri was evaluated and rejected for the same
reason (kashida alternates break MuPDF's text extraction order).

System fonts (Windows) are offered only if present on the user's machine and
are never copied into the distribution.
"""

from __future__ import annotations

import logging
import os
import sys
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import FONTS_DIR

logger = logging.getLogger("NextPDF")

STYLE_REGULAR = "regular"
STYLE_BOLD = "bold"
STYLE_ITALIC = "italic"
STYLE_BOLD_ITALIC = "bolditalic"


@dataclass
class FontFace:
    family: str
    style: str
    path: str
    full_name: str = ""          # "<family> <subfamily>" as MuPDF reports it as BaseFont
    has_arabic: bool = False
    has_latin: bool = False
    redistributable: bool = True


@dataclass
class FontFamily:
    name: str
    faces: Dict[str, FontFace] = field(default_factory=dict)
    redistributable: bool = True

    def face(self, bold: bool = False, italic: bool = False) -> Optional[FontFace]:
        key = {(False, False): STYLE_REGULAR, (True, False): STYLE_BOLD,
               (False, True): STYLE_ITALIC, (True, True): STYLE_BOLD_ITALIC}[(bold, italic)]
        return (self.faces.get(key) or self.faces.get(STYLE_REGULAR)
                or next(iter(self.faces.values()), None))

    @property
    def has_arabic(self) -> bool:
        return any(f.has_arabic for f in self.faces.values())


# Known bundled files -> (family, style).  Only families whose ToUnicode map
# can be rebuilt correctly are listed (see module docstring).
_BUNDLED = {
    "NotoSansArabic-Regular.ttf": ("Noto Sans Arabic", STYLE_REGULAR),
    "NotoSansArabic-Bold.ttf": ("Noto Sans Arabic", STYLE_BOLD),
    "NotoSans-Regular.ttf": ("Noto Sans", STYLE_REGULAR),
    "DejaVuSans.ttf": ("DejaVu Sans", STYLE_REGULAR),
    "DejaVuSans-Bold.ttf": ("DejaVu Sans", STYLE_BOLD),
    "DejaVuSans-Oblique.ttf": ("DejaVu Sans", STYLE_ITALIC),
    "DejaVuSans-BoldOblique.ttf": ("DejaVu Sans", STYLE_BOLD_ITALIC),
}

# Optional system fonts (Windows). Only used when present locally.
_SYSTEM = {
    "arial.ttf": ("Arial", STYLE_REGULAR), "arialbd.ttf": ("Arial", STYLE_BOLD),
    "ariali.ttf": ("Arial", STYLE_ITALIC), "arialbi.ttf": ("Arial", STYLE_BOLD_ITALIC),
    "tahoma.ttf": ("Tahoma", STYLE_REGULAR), "tahomabd.ttf": ("Tahoma", STYLE_BOLD),
    "segoeui.ttf": ("Segoe UI", STYLE_REGULAR), "segoeuib.ttf": ("Segoe UI", STYLE_BOLD),
    "segoeuii.ttf": ("Segoe UI", STYLE_ITALIC), "segoeuiz.ttf": ("Segoe UI", STYLE_BOLD_ITALIC),
    "times.ttf": ("Times New Roman", STYLE_REGULAR), "timesbd.ttf": ("Times New Roman", STYLE_BOLD),
    "calibri.ttf": ("Calibri", STYLE_REGULAR), "calibrib.ttf": ("Calibri", STYLE_BOLD),
}

DEFAULT_ARABIC_FAMILY = "Noto Sans Arabic"
DEFAULT_LATIN_FAMILY = "Noto Sans"
FALLBACK_FAMILY = "DejaVu Sans"


def _system_font_dirs() -> List[Path]:
    dirs = []
    if sys.platform == "win32":
        win = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(Path(win) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    return [d for d in dirs if d.exists()]


def _inspect(path: str) -> Tuple[str, bool, bool]:
    """Return (full_name, has_arabic, has_latin) using fontTools."""
    try:
        from fontTools.ttLib import TTFont
        t = TTFont(path, lazy=True)
        names = {}
        for rec in t["name"].names:
            if rec.nameID in (1, 2) and rec.nameID not in names:
                try:
                    names[rec.nameID] = rec.toUnicode()
                except Exception:
                    pass
        cmap = t.getBestCmap() or {}
        full = f"{names.get(1, '')} {names.get(2, '')}".strip()
        t.close()
        return full, (0x0628 in cmap), (ord("a") in cmap)
    except Exception as e:
        logger.debug("font inspect failed for %s: %s", path, e)
        return Path(path).stem, False, True


class FontRegistry:
    """Discovers bundled and system fonts and builds CSS for MuPDF Story."""

    def __init__(self):
        self.families: Dict[str, FontFamily] = {}
        self._by_full_name: Dict[str, FontFace] = {}
        self._dirs: List[Path] = []
        self.reload()

    # -- discovery -----------------------------------------------------------
    def reload(self):
        self.families.clear()
        self._by_full_name.clear()
        self._dirs = []
        if FONTS_DIR.exists():
            self._dirs.append(FONTS_DIR)
            for fname, (family, style) in _BUNDLED.items():
                p = FONTS_DIR / fname
                if p.exists():
                    self._add(family, style, str(p), redistributable=True)
        for d in _system_font_dirs():
            self._dirs.append(d)
            for fname, (family, style) in _SYSTEM.items():
                p = d / fname
                if p.exists() and family not in self.families or (
                        p.exists() and style not in self.families[family].faces):
                    self._add(family, style, str(p), redistributable=False)
        if not self.families:
            logger.warning("No fonts found in %s or system directories", FONTS_DIR)

    def _add(self, family: str, style: str, path: str, redistributable: bool):
        full, has_ar, has_lat = _inspect(path)
        face = FontFace(family=family, style=style, path=path, full_name=full,
                        has_arabic=has_ar, has_latin=has_lat, redistributable=redistributable)
        fam = self.families.setdefault(family, FontFamily(name=family, redistributable=redistributable))
        fam.faces[style] = face
        fam.redistributable = fam.redistributable and redistributable
        self._by_full_name[full.lower()] = face
        self._by_full_name[Path(path).stem.lower()] = face

    # -- queries -------------------------------------------------------------
    def family_names(self, arabic_only: bool = False) -> List[str]:
        names = [n for n, f in self.families.items() if (f.has_arabic or not arabic_only)]
        # bundled first, then system
        return sorted(names, key=lambda n: (not self.families[n].redistributable, n))

    def get_family(self, name: str) -> Optional[FontFamily]:
        if name in self.families:
            return self.families[name]
        low = name.lower()
        for n, f in self.families.items():
            if n.lower() == low:
                return f
        return None

    def resolve_family(self, name: Optional[str], text: str = "") -> str:
        """Pick an available family: requested one, else Arabic/Latin default."""
        if name and self.get_family(name):
            return self.get_family(name).name
        if text and contains_arabic(text) and self.get_family(DEFAULT_ARABIC_FAMILY):
            return DEFAULT_ARABIC_FAMILY
        if self.get_family(DEFAULT_LATIN_FAMILY):
            return DEFAULT_LATIN_FAMILY
        return next(iter(self.families), "")

    def script_fallback(self, family: str, arabic: bool) -> Optional[str]:
        """Family to use for an Arabic (or Latin) run that ``family`` cannot
        render, or None when ``family`` covers that script itself.

        MuPDF's Story does not fall back along the CSS font-family stack per
        glyph; missing glyphs go to its built-in fonts, whose text layer we
        cannot repair.  Runs of the other script are therefore wrapped in an
        explicit span using a bundled family that has the glyphs.
        """
        fam = self.get_family(family)
        if fam is None:
            return None
        faces = list(fam.faces.values())
        if arabic:
            if any(f.has_arabic for f in faces):
                return None
            for cand in (DEFAULT_ARABIC_FAMILY, FALLBACK_FAMILY):
                if self.get_family(cand) and self.get_family(cand).has_arabic:
                    return cand
        else:
            if any(f.has_latin for f in faces):
                return None
            for cand in (DEFAULT_LATIN_FAMILY, FALLBACK_FAMILY):
                c = self.get_family(cand)
                if c and any(f.has_latin for f in c.faces.values()):
                    return cand
        return None

    def face_for_basefont(self, basefont: str) -> Optional[FontFace]:
        """Map a PDF BaseFont name (as reported by MuPDF) to a known face."""
        if not basefont:
            return None
        key = basefont.lower()
        if "+" in key:  # subset prefix ABCDEF+Name
            key = key.split("+", 1)[1]
        if key in self._by_full_name:
            return self._by_full_name[key]
        key2 = key.replace("-", " ").replace("_", " ")
        for k, face in self._by_full_name.items():
            if k == key2 or k.replace(" ", "") == key.replace(" ", ""):
                return face
        return None

    def font_dirs(self) -> List[str]:
        return [str(d) for d in self._dirs]

    # -- CSS for MuPDF Story -------------------------------------------------
    def css_font_faces(self, families: List[str]) -> Tuple[str, str]:
        """Return (@font-face CSS, font-family stack) for the given families
        plus the universal fallback. Family CSS names are sanitised."""
        rules = []
        stack = []
        seen = set()
        for fam_name in list(families) + [FALLBACK_FAMILY]:
            fam = self.get_family(fam_name)
            if not fam or fam.name in seen:
                continue
            seen.add(fam.name)
            css_name = self.css_name(fam.name)
            for style, face in fam.faces.items():
                weight = "bold" if style in (STYLE_BOLD, STYLE_BOLD_ITALIC) else "normal"
                fstyle = "italic" if style in (STYLE_ITALIC, STYLE_BOLD_ITALIC) else "normal"
                rules.append(
                    f'@font-face {{ font-family: "{css_name}"; src: url("{Path(face.path).name}");'
                    f' font-weight: {weight}; font-style: {fstyle}; }}')
            stack.append(f'"{css_name}"')
        return "\n".join(rules), ", ".join(stack) if stack else "sans-serif"

    @staticmethod
    def css_name(family: str) -> str:
        return "npf-" + "".join(c if c.isalnum() else "-" for c in family.lower())

    def archive(self):
        """pymupdf.Archive that resolves the url() file names used in CSS."""
        import pymupdf
        arch = pymupdf.Archive()
        for d in self._dirs:
            try:
                arch.add(str(d))
            except Exception as e:
                logger.debug("archive add failed %s: %s", d, e)
        return arch


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def contains_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F"
               or "\u08A0" <= c <= "\u08FF" or "\uFB50" <= c <= "\uFDFF"
               or "\uFE70" <= c <= "\uFEFF" for c in text)


def detect_direction(text: str) -> str:
    """'rtl' if the first strong character is R/AL, else 'ltr'."""
    for ch in text:
        bc = unicodedata.bidirectional(ch)
        if bc in ("R", "AL"):
            return "rtl"
        if bc == "L":
            return "ltr"
    return "rtl" if contains_arabic(text) else "ltr"


def is_presentation_form(ch: str) -> bool:
    return ("\uFB50" <= ch <= "\uFDFF") or ("\uFE70" <= ch <= "\uFEFF")


def normalize_arabic(text: str) -> str:
    """Map Arabic presentation forms back to logical letters (NFKC) while
    leaving everything else untouched."""
    if not any(is_presentation_form(c) for c in text):
        return text
    return "".join(unicodedata.normalize("NFKC", c) if is_presentation_form(c) else c for c in text)


# ---------------------------------------------------------------------------
# HarfBuzz glyph -> unicode mapping (for ToUnicode rebuild)
# ---------------------------------------------------------------------------
def bidi_runs(text: str) -> List[Tuple[str, bool]]:
    """Split text into directional runs (text, is_rtl). Neutral characters
    attach to the current run; a leading neutral run takes the direction of
    the first strong character."""
    runs: List[Tuple[str, bool]] = []
    cur = ""
    cur_rtl: Optional[bool] = None
    for ch in text:
        bc = unicodedata.bidirectional(ch)
        if bc in ("R", "AL"):
            rtl: Optional[bool] = True
        elif bc == "L":
            rtl = False
        else:
            rtl = cur_rtl
        if cur_rtl is None and rtl is not None:
            cur_rtl = rtl
        if rtl is not None and cur_rtl is not None and rtl != cur_rtl and cur:
            runs.append((cur, cur_rtl))
            cur, cur_rtl = "", rtl
        cur += ch
    if cur:
        runs.append((cur, bool(cur_rtl)))
    return runs


@lru_cache(maxsize=16)
def _hb_font(path: str):
    import uharfbuzz as hb
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    return hb.Font(face)


def glyph_unicode_map(font_path: str, texts: List[str]) -> Dict[int, str]:
    """Shape ``texts`` with HarfBuzz and return {glyph_id: logical string}.

    Glyph ids are the CIDs MuPDF writes for Identity-H fonts, so the map can
    be turned straight into a ToUnicode CMap.  Cluster level 2 (CHARACTERS)
    keeps every glyph attached to the character it came from even when the
    shaper reorders marks (shadda before a vowel), so a base glyph and its
    mark glyphs each map to their own character; only true ligatures collapse
    several characters onto one glyph.
    """
    try:
        import uharfbuzz as hb
    except ImportError:
        logger.warning("uharfbuzz not available: ToUnicode rebuild disabled")
        return {}
    font = _hb_font(font_path)
    gmap: Dict[int, str] = {}
    for text in texts:
        for run, rtl in bidi_runs(text):
            if not run:
                continue
            buf = hb.Buffer()
            buf.add_str(run)
            buf.guess_segment_properties()
            buf.direction = "rtl" if rtl else "ltr"
            buf.cluster_level = 2
            try:
                hb.shape(font, buf)
            except Exception as e:
                logger.debug("hb.shape failed: %s", e)
                continue
            clusters: Dict[int, List[int]] = {}
            for gi in buf.glyph_infos:
                clusters.setdefault(gi.cluster, []).append(gi.codepoint)
            keys = sorted(clusters)
            for i, cl in enumerate(keys):
                nxt = keys[i + 1] if i + 1 < len(keys) else len(run)
                chars = run[cl:nxt]
                gids = clusters[cl]
                for k, g in enumerate(gids):
                    val = chars if k == 0 else ""
                    if g not in gmap or (not gmap[g] and val):
                        gmap[g] = val
    return gmap


@lru_cache(maxsize=16)
def font_glyph_unicode_map(font_path: str) -> Dict[int, str]:
    """Static {glyph_id: logical string} for a whole font file.

    Built from the font's own tables, independently of any shaper: the cmap
    gives the directly encoded glyphs, and the GSUB lookups (single, multiple,
    alternate and ligature substitutions) are resolved back to the characters
    they were substituted from.  Contextual forms, kashidas and ligatures that
    MuPDF's shaper emits therefore still decode to the right logical text even
    when our own HarfBuzz shaping pass picks a different glyph.
    """
    gmap: Dict[int, str] = {}
    try:
        from fontTools.ttLib import TTFont
        t = TTFont(font_path, lazy=True)
    except Exception as e:
        logger.debug("font map failed for %s: %s", font_path, e)
        return gmap
    try:
        order = t.getGlyphOrder()
        name2gid = {n: i for i, n in enumerate(order)}
        cmap = t.getBestCmap() or {}
        for cp, gname in cmap.items():
            gid = name2gid.get(gname)
            if gid is None or cp < 32:
                continue
            ch = chr(cp)
            if gid not in gmap or (is_presentation_form(gmap[gid]) and not is_presentation_form(ch)):
                gmap[gid] = ch
        for gid in list(gmap):
            gmap[gid] = normalize_arabic(gmap[gid])
        pending: List[Tuple[int, List[int]]] = []
        if "GSUB" in t:
            for lookup in t["GSUB"].table.LookupList.Lookup:
                for sub in lookup.SubTable:
                    st = getattr(sub, "ExtSubTable", sub)
                    lt = getattr(st, "LookupType", lookup.LookupType)
                    try:
                        if lt == 1:
                            for a, b in st.mapping.items():
                                pending.append((name2gid[b], [name2gid[a]]))
                        elif lt == 2:
                            for a, seq in st.mapping.items():
                                for i, b in enumerate(seq):
                                    pending.append((name2gid[b], [name2gid[a]] if i == 0 else []))
                        elif lt == 3:
                            for a, alts in st.alternates.items():
                                for b in alts:
                                    pending.append((name2gid[b], [name2gid[a]]))
                        elif lt == 4:
                            for first, ligs in st.ligatures.items():
                                for lig in ligs:
                                    comps = [first] + list(lig.Component)
                                    pending.append((name2gid[lig.LigGlyph], [name2gid[c] for c in comps]))
                    except Exception as e:
                        logger.debug("GSUB lookup skipped: %s", e)
        for _ in range(8):
            changed = False
            for out, ins in pending:
                if out in gmap:
                    continue
                if not ins:
                    gmap[out] = ""
                    changed = True
                elif all(i in gmap for i in ins):
                    gmap[out] = "".join(gmap[i] for i in ins)
                    changed = True
            if not changed:
                break
    except Exception as e:
        logger.debug("font map incomplete for %s: %s", font_path, e)
    finally:
        try:
            t.close()
        except Exception:
            pass
    return gmap


_registry: Optional[FontRegistry] = None


def get_font_registry() -> FontRegistry:
    global _registry
    if _registry is None:
        _registry = FontRegistry()
    return _registry
