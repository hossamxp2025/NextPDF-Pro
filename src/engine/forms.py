#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactive form fields (AcroForms): reading them, filling them, adding
simple ones, and flattening a filled form into ordinary page content.

Two facts decided the design here, and both are reported rather than hidden.

The value and the appearance of a field are two different things.  The value
is the data, stored as text in the PDF; the appearance is the picture of that
value drawn inside the field's rectangle.  PyMuPDF draws appearances with the
fourteen standard PDF fonts, none of which shapes Arabic, so an Arabic value
is stored exactly right while the appearance this program bakes for it comes
out with broken letters.  MuPDF also drops the ``NeedAppearances`` flag on
save, so a reader cannot be asked to redraw it.  ``set_value`` therefore
tells the caller whether the appearance can show what was stored.

Flattening is the way out for Arabic: the value is drawn as real page text
through the project's text engine, which embeds a real Arabic font and shapes
it properly, and the field is then removed.  After flattening the form is no
longer fillable, which is the point.
"""

import logging

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

logger = logging.getLogger("NextPDF")

TEXT = "text"
CHECKBOX = "checkbox"
RADIO = "radio"
DROPDOWN = "dropdown"
LISTBOX = "listbox"
BUTTON = "button"
SIGNATURE = "signature"
UNKNOWN = "unknown"

CREATABLE_KINDS = (TEXT, CHECKBOX, DROPDOWN)

_TYPE_TO_KIND = {
    fitz.PDF_WIDGET_TYPE_TEXT: TEXT,
    fitz.PDF_WIDGET_TYPE_CHECKBOX: CHECKBOX,
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: RADIO,
    fitz.PDF_WIDGET_TYPE_COMBOBOX: DROPDOWN,
    fitz.PDF_WIDGET_TYPE_LISTBOX: LISTBOX,
    fitz.PDF_WIDGET_TYPE_BUTTON: BUTTON,
    fitz.PDF_WIDGET_TYPE_SIGNATURE: SIGNATURE,
}

_KIND_TO_TYPE = {
    TEXT: fitz.PDF_WIDGET_TYPE_TEXT,
    CHECKBOX: fitz.PDF_WIDGET_TYPE_CHECKBOX,
    DROPDOWN: fitz.PDF_WIDGET_TYPE_COMBOBOX,
}

ARABIC_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
                 (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def contains_arabic(text) -> bool:
    return any(any(low <= ord(char) <= high for low, high in ARABIC_RANGES)
               for char in str(text or ""))


def _describe(widget, page_number: int) -> dict:
    rect = fitz.Rect(widget.rect)
    return {
        "name": widget.field_name or "",
        "kind": _TYPE_TO_KIND.get(widget.field_type, UNKNOWN),
        "value": widget.field_value,
        "choices": list(widget.choice_values or ()),
        "page": page_number,
        "rect": (rect.x0, rect.y0, rect.x1, rect.y1),
        "read_only": bool(getattr(widget, "field_flags", 0) & 1),
        "label": widget.field_label or "",
    }


def is_form(doc) -> bool:
    """Whether the document has any interactive fields at all."""
    try:
        return bool(doc.is_form_pdf)
    except Exception:
        return False


def list_fields(doc) -> list:
    """Every field in the document, page by page."""
    found = []
    for number in range(doc.page_count):
        page = doc[number]
        try:
            for widget in page.widgets():
                found.append(_describe(widget, number + 1))
        except Exception:
            logger.exception("Could not read the fields of page %d", number + 1)
    return found


def page_fields(page) -> list:
    try:
        return [_describe(widget, page.number + 1) for widget in page.widgets()]
    except Exception:
        logger.exception("Could not read the fields of a page")
        return []


def _widget_by_name(doc, name: str, page_number=None):
    numbers = ([page_number - 1] if page_number
               else range(doc.page_count))
    for index in numbers:
        page = doc[index]
        for widget in page.widgets():
            if (widget.field_name or "") == name:
                return page, widget
    return None, None


def checkbox_value(value) -> bool:
    """What a checkbox's stored value means as a yes or a no."""
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() not in {"", "off", "no", "false", "0"}


def set_value(doc, name: str, value, page_number=None) -> dict:
    """Store *value* in the field called *name*.

    Returns ``{"stored": True/False, "appearance_ok": bool, "field": ...}``.
    ``appearance_ok`` is False when the value is stored correctly but the
    appearance drawn for it cannot show the characters (Arabic in a text
    field); the caller is expected to say so or to flatten the form.
    """
    page, widget = _widget_by_name(doc, name, page_number)
    if widget is None:
        return {"stored": False, "appearance_ok": True, "field": None,
                "reason": "No such field"}
    kind = _TYPE_TO_KIND.get(widget.field_type, UNKNOWN)
    if kind in (BUTTON, SIGNATURE, UNKNOWN):
        return {"stored": False, "appearance_ok": True, "field": None,
                "reason": f"A {kind} field cannot be filled in here"}
    if kind == CHECKBOX:
        widget.field_value = checkbox_value(value)
    elif kind in (DROPDOWN, LISTBOX):
        choices = list(widget.choice_values or ())
        if choices and str(value) not in choices:
            return {"stored": False, "appearance_ok": True, "field": None,
                    "reason": "That is not one of the choices"}
        widget.field_value = str(value)
    else:
        widget.field_value = "" if value is None else str(value)
    widget.update()
    appearance_ok = not (kind == TEXT and contains_arabic(widget.field_value))
    return {"stored": True, "appearance_ok": appearance_ok,
            "field": _describe(widget, page.number + 1)}


def add_field(page, rect, name: str, kind: str = TEXT, value=None,
              choices=None, font_size: float = 11.0,
              border_color=(0.3, 0.3, 0.3), fill_color=(0.95, 0.96, 0.98)):
    """Add one simple field to a page."""
    if kind not in CREATABLE_KINDS:
        raise ValueError(f"This kind of field cannot be created here: {kind}")
    if not (name or "").strip():
        raise ValueError("A field needs a name")
    box = fitz.Rect(rect)
    if box.get_area() <= 0:
        raise ValueError("A field needs an area")
    if any((widget.field_name or "") == name for widget in page.widgets()):
        raise ValueError("A field with that name is already on this page")
    if kind == DROPDOWN and not choices:
        raise ValueError("A dropdown needs its choices")
    widget = fitz.Widget()
    widget.rect = box
    widget.field_name = name
    widget.field_type = _KIND_TO_TYPE[kind]
    widget.border_color = border_color
    widget.fill_color = fill_color
    widget.text_fontsize = float(font_size)
    if kind == DROPDOWN:
        widget.choice_values = list(choices)
        widget.field_value = str(value) if value is not None else str(choices[0])
    elif kind == CHECKBOX:
        widget.field_value = checkbox_value(value)
    else:
        widget.field_value = "" if value is None else str(value)
    page.add_widget(widget)
    page, created = _widget_by_name(page.parent, name, page.number + 1)
    return _describe(created, page.number + 1)


def delete_field(doc, name: str, page_number=None) -> bool:
    page, widget = _widget_by_name(doc, name, page_number)
    if widget is None:
        return False
    page.delete_widget(widget)
    return True


def flatten(doc, text_engine=None) -> dict:
    """Turn the filled values into ordinary page content.

    A value the baked appearance cannot show (Arabic) is drawn first as real
    page text through the text engine, which embeds a font that shapes it;
    the field's own value is then cleared so nothing broken is baked over it.
    Returns how many fields were flattened and how many were redrawn this
    way.  The form stops being fillable, which is what flattening means.
    """
    fields = list_fields(doc)
    if not fields:
        return {"flattened": 0, "redrawn": 0}
    redrawn = 0
    if text_engine is None:
        from src.engine.text_engine import TextEngine

        text_engine = TextEngine()
    from src.engine.text_engine import TextStyle

    for field in fields:
        if field["kind"] != TEXT or not contains_arabic(field["value"]):
            continue
        page = doc[field["page"] - 1]
        _, widget = _widget_by_name(doc, field["name"], field["page"])
        if widget is None:
            continue
        box = fitz.Rect(field["rect"])
        result = text_engine.insert_text(
            page, box, str(field["value"]),
            TextStyle(size=11.0, direction="rtl", align="right"))
        if getattr(result, "success", False):
            # The field's own appearance was already baked with the broken
            # letters, and clearing the value does not remove that picture,
            # so the widget itself goes: the redrawn text replaces it.
            page.delete_widget(widget)
            redrawn += 1
        else:
            logger.warning("Could not redraw an Arabic field: %s",
                           getattr(result, "message", ""))
    doc.bake(annots=False, widgets=True)
    return {"flattened": len(fields), "redrawn": redrawn}
