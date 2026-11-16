#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Centralized Arabic/English localization for NextPDF Pro.

Every application-owned visible string must come from this module.  The
translation is intentionally a plain dictionary (no compiled .qm files) so the
packaged application has no external translation dependency.  Missing keys
return the English key itself, and a test asserts that every key used by the UI
exists in both languages.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("NextPDF")

# fmt: off
TRANSLATIONS = {
    "ar": {
        "Extracts rectangular tables and some aligned borderless tables. Review the output. CSV requires one table. Merged cells and scanned tables are not reliably supported.": "يستخرج الجداول المستطيلة وبعض الجداول ذات الأعمدة المحاذاة دون حدود. راجع الناتج. يتطلب CSV جدولًا واحدًا. الخلايا المدمجة والجداول المصورة غير مدعومة بصورة موثوقة.",
        # Application / window
        "NextPDF Pro": "NextPDF Pro",
        "Word page images": "وورد: صور صفحات",
        "Excel grid tables": "إكسل: جداول شبكية",
        "PowerPoint page images": "باوربوينت: صور صفحات",
        "CSV grid tables": "تصدير الجداول",
        "Editable Word unavailable": "وورد القابل للتحرير غير متاح",
        "Editable Word": "وورد قابل للتحرير",
        "Editable slides": "شرائح قابلة للتحرير",
        "Editable Word: tables, shading, fonts and reading order are rebuilt; absolute positions are not. Legacy visual Arabic is refused.": "وورد قابل للتحرير: تُعاد بناء الجداول والتظليل والخطوط وترتيب القراءة، أما المواضع المطلقة فلا. يُرفض النص العربي المرسوم بصريًا.",
        "Editable slides: real positioned text boxes and images, approximate layout. Legacy visual Arabic is refused.": "شرائح قابلة للتحرير: مربعات نص حقيقية بمواضعها مع الصور، وتخطيط تقريبي. يُرفض النص العربي المرسوم بصريًا.",
        "Page images only: appearance preserved, text and tables are not editable.": "صور صفحات فقط: يُحفظ المظهر، لكن النصوص والجداول ليست قابلة للتحرير.",
        "Only fully ruled rectangular grids are supported. CSV requires one table. Merged cells and scanned tables are unsupported.": "تُدعم الجداول المستطيلة ذات الحدود الكاملة فقط. يتطلب تصدير البيانات جدولًا واحدًا. الخلايا المدمجة والجداول المصورة غير مدعومة.",
        "PNG": "صور نقطية",
        "JPEG": "صور مضغوطة",
        "TIFF": "صور مسح ضوئي",
        "WEBP": "صور ويب",
        "TXT": "نص عادي",
        "HTML": "صفحة ويب",
        "Markdown": "نص منسق",
        "SVG": "رسوم متجهية",
        "JSON": "بيانات منظمة",
        "Start conversion": "بدء التحويل",
        "Save conversion output": "حفظ ناتج التحويل",
        "Conversion failed": "فشل التحويل؛ راجع القيود والسجل",
        "Converting PDF": "جارٍ تحويل PDF",
        "Conversion output saved": "تم حفظ ناتج التحويل",
        "Conversion cancelled": "أُلغي التحويل",
        "Cancelling conversion": "جارٍ إلغاء التحويل",
        "Text formats export logical text, not original layout. PNG/JPEG/WEBP/SVG require one selected page. TIFF supports multiple pages.": "الصيغ النصية تصدر النص المنطقي لا التخطيط الأصلي. تتطلب PNG وJPEG وWEBP وSVG صفحة محددة واحدة. يدعم TIFF عدة صفحات.",
        "Selected pages": "صفحات محددة",
        "Arabic and English": "العربية والإنجليزية",
        "Page range": "نطاق الصفحات",
        "Recognition language": "لغة التعرف",
        "Output format": "صيغة الإخراج",
        "OCR preserves the page image; it does not restore editable layout.": "يحافظ OCR على صورة الصفحة، ولا يستعيد تخطيطًا قابلًا للتحرير.",
        "Start OCR": "بدء التعرف",
        "Open output": "فتح الناتج",
        "Page range is invalid": "نطاق الصفحات غير صالح",
        "Save OCR output": "حفظ ناتج التعرف",
        "OCR output must use a different path": "يجب اختيار مسار مختلف للناتج",
        "OCR failed": "فشل التعرف؛ راجع السجل للتفاصيل",
        "Processing OCR": "جارٍ التعرف الضوئي",
        "OCR output saved": "تم حفظ ناتج التعرف",
        "OCR cancelled": "أُلغي التعرف الضوئي",
        "Cancelling OCR": "جارٍ إلغاء التعرف",
        "Create from files": "إنشاء من ملفات",
        "Images to PDF": "صور إلى PDF",
        "Text to PDF": "نصوص إلى PDF",
        "Add files": "إضافة ملفات",
        "Remove": "إزالة",
        "Move up": "تحريك لأعلى",
        "Move down": "تحريك لأسفل",
        "Create": "إنشاء",
        "Add at least one file": "أضف ملفًا واحدًا على الأقل",
        "Save created PDF": "حفظ ملف PDF المنشأ",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "PDF files are merged as they are. Images keep their aspect ratio. Documents are reflowed into pages; this is not a page-faithful Office render.": "تُدمج ملفات PDF كما هي. تحتفظ الصور بنسب أبعادها. تُعاد تدفق المستندات إلى صفحات، وهذا ليس مطابقة كاملة لتخطيط Office.",
        "All supported (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.txt *.md *.html *.htm *.csv *.docx *.xlsx *.pptx)": "كل الصيغ المدعومة (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.txt *.md *.html *.htm *.csv *.docx *.xlsx *.pptx)",
        "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)": "صور (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)",
        "Documents (*.txt *.md *.html *.htm *.csv *.docx *.xlsx *.pptx)": "مستندات (*.txt *.md *.html *.htm *.csv *.docx *.xlsx *.pptx)",
        "Creating PDF": "جارٍ إنشاء PDF",
        "PDF created": "تم إنشاء ملف PDF",
        "Create PDF failed": "فشل إنشاء PDF؛ راجع السجل للتفاصيل",
        "PDF creation cancelled": "أُلغي إنشاء PDF",
        "Cancelling PDF creation": "جارٍ إلغاء إنشاء PDF",
        "Create PDF output must use a different path": "يجب اختيار مسار مختلف لملف PDF الناتج",
        "Encrypted PDF requires a password": "ملف PDF مشفر ويتطلب كلمة مرور",
        "The selected sources produced no pages": "لم تُنتج الملفات المحددة أي صفحات",
        "No source files were selected": "لم يتم تحديد أي ملفات مصدر",
        "Home": "الرئيسية",
        "Edit PDF": "تحرير PDF",
        "Organize Pages": "تنظيم الصفحات",
        "Insert": "إدراج",
        "Create PDF": "إنشاء PDF",
        "Review": "مراجعة",
        "Protect and Sign": "حماية وتوقيع",
        "Settings": "الإعدادات",
        "Document": "المستند",
        "History": "السجل",
        "Text": "النص",
        "Content": "المحتوى",
        "Images and text": "صور ونصوص",
        "Office": "أوفيس",
        "From files": "من ملفات",
        "Recognition": "التعرف",
        "Comments": "التعليقات",
        "Security": "الأمان",
        "Zoom": "التكبير",
        "Language": "اللغة",
        "Appearance": "المظهر",
        "Error": "خطأ",
        "Warning": "تنبيه",
        "Open PDF File": "فتح ملف PDF",
        "Please open a PDF file first": "يرجى فتح ملف PDF أولاً",
        "Text editing mode - Click text to edit": "وضع تحرير النص - انقر على النص لتحريره",
        "No active PDF viewer": "لا يوجد عارض صفحات نشط",
        "Add text mode - Click page to add text": "وضع إضافة النص - انقر على الصفحة لإضافة نص",
        "Select Image": "اختر صورة",
        "Image inserted": "تم إدراج الصورة",
        "Blank page inserted": "تم إدراج صفحة فارغة",
        "Page deleted": "تم حذف الصفحة",
        "Page rotated": "تم دوران الصفحة",
        "OCR Not Available": "OCR غير متاح",
        "OCR Results": "نتائج OCR",
        "Image selected": "تم تحديد صورة",
        "Text selected": "تم تحديد نص",
        "Pages panel": "لوحة الصفحات",
        "Properties panel": "لوحة الخصائص",
        "Failed to create a new document": "فشل إنشاء مستند جديد",
        "Failed to open the file": "فشل فتح الملف",
        "PDF files": "ملفات PDF",
        "Saved as": "تم الحفظ باسم",
        "Undone": "تم التراجع",
        "Redone": "تم الإعادة",
        "Images": "صور",
        "Switch language": "تبديل اللغة",
        "Light theme": "المظهر النهاري",
        "Dark theme": "المظهر الليلي",
        "System theme": "مظهر النظام",
        "Not implemented": "غير منفذ حاليًا",
        "Conversion unavailable": "التحويل غير متاح حاليًا",
        "Create PDF unavailable": "إنشاء PDF غير متاح حاليًا",
        "Review unavailable": "المراجعة غير متاحة حاليًا",
        "Protect and Sign unavailable": "الحماية والتوقيع غير متاحين حاليًا",
        "File": "ملف",
        "Edit": "تحرير",
        "View": "عرض",
        "Tools": "أدوات",
        "Help": "مساعدة",
        "Exit": "خروج",
        "About": "حول",
        "Arabic": "العربية",
        "English": "الإنجليزية",
        "Professional PDF Editor": "محرر PDF احترافي",
        "Professional PDF Editor for Windows": "محرر PDF احترافي لنظام Windows",
        "No Selection": "لا يوجد تحديد",
        "Select an element to view its properties": "حدد عنصرًا لعرض خصائصه",
        "Pages": "الصفحات",
        "Page": "الصفحة",
        "Ready": "جاهز",
        "Opened": "تم الفتح",
        "Saved": "تم الحفظ",
        "Text Properties": "خصائص النص",
        "Image Properties": "خصائص الصورة",
        "Font Family": "نوع الخط",
        "Font Size": "حجم الخط",
        "Color": "اللون",
        "Direction": "الاتجاه",
        "Right to left": "من اليمين إلى اليسار",
        "Left to right": "من اليسار إلى اليمين",
        "Style": "النمط",
        "Regular": "عادي",
        "Bold": "عريض",
        "Italic": "مائل",
        "Size": "الحجم",
        "Position": "الموضع",
        "Rotation": "الدوران",
        "Opacity": "الشفافية",
        "Apply": "تطبيق",
        "Cancel": "إلغاء",
        "Enter text": "إدخال النص",
        "Edit text": "تحرير النص",
        "Previous Page": "الصفحة السابقة",
        "Next Page": "الصفحة التالية",
        "Actual Size": "الحجم الفعلي",
        "Go to Page": "انتقل إلى الصفحة",
        "Text editing mode: click a text line to edit": "انقر على سطر نص لتحريره",
        "Add text mode: click on the page to place text": "انقر على الصفحة لإضافة النص",
        "Open a PDF file to get started": "افتح ملف PDF للبدء",
        "Open PDF": "فتح PDF",
        # File
        "New": "جديد",
        "Open": "فتح",
        "Save": "حفظ",
        "Save As": "حفظ باسم",
        "Print": "طباعة",
        # Edit
        "Undo": "تراجع",
        "Redo": "إعادة",
        "Edit Text": "تحرير النص",
        "Add Text": "إضافة نص",
        "Delete Selected Text": "حذف النص المحدد",
        # Insert
        "Insert Image": "إدراج صورة",
        # Pages
        "Insert Page": "إدراج صفحة",
        "Delete Page": "حذف صفحة",
        "Rotate": "تدوير",
        "Extract Pages": "استخراج صفحات",
        "Move Page Up": "تحريك الصفحة للأعلى",
        "Move Page Down": "تحريك الصفحة للأسفل",
        "Merge PDFs": "دمج ملفات PDF",
        # View
        "Zoom In": "تكبير",
        "Zoom Out": "تصغير",
        "Fit Page": "ملاءمة الصفحة",
        "Fit Width": "ملاءمة العرض",
        # Tools
        "Search": "بحث",
        "All pages": "جميع الصفحات",
        "Current page": "الصفحة الحالية",
        "Properties": "خصائص",
        "OCR": "OCR",
        "Install Tesseract OCR to use this feature.": "ثبّت Tesseract OCR لاستخدام هذه الميزة.",
        "OCR engine is not installed": "محرك التعرف الضوئي غير مثبت",
        "This build does not include Office conversion.": "هذا الإصدار لا يتضمن تحويل Office.",
        "Digital signatures are not implemented.": "التوقيعات الرقمية غير منفذة.",
        "Encryption and permissions are not implemented.": "التشفير والتصاريح غير منفذة.",
        "Redaction is not implemented.": "الإخفاء الآمن غير منفذ.",
        # About
        "About NextPDF Pro": "حول NextPDF Pro",
        "Version": "الإصدار",
        "A professional PDF editor for Windows.": "محرر PDF احترافي لنظام Windows.",
        "Built with Python, PySide6 and PyMuPDF.": "مبني باستخدام Python وPySide6 وPyMuPDF.",
        # Project identity / credits
        "Established and developed by": "تأسيس وإنشاء وتطوير",
        "Future of Automation (مستقبل الأتمتة)": "مستقبل الأتمتة (Future of Automation)",
        "Next Ai Agent | Future ai agent": "Next Ai Agent | Future ai agent",
        "Free & Open Source Software": "برنامج مجاني ومفتوح المصدر",
        "Licensed under GNU AGPL v3.0": "مرخص بموجب GNU AGPL v3.0",
        # Terms and Conditions
        "NextPDF Pro — الشروط والأحكام": "NextPDF Pro — الشروط والأحكام",
        "NextPDF Pro — Terms and Conditions": "NextPDF Pro — الشروط والأحكام",
        "Terms intro ar": "برنامج NextPDF Pro هو برنامج لتحرير وإنشاء وتحويل وإدارة ملفات PDF، وقد تم تأسيسه وإنشاؤه وتطويره تحت مظلة «مستقبل الأتمتة» (Future of Automation)، مع إظهار اسمي Next Ai Agent وFuture ai agent ضمن الهوية التعريفية للمشروع.\n\nيُتاح البرنامج بوصفه مشروعًا مجانيًا ومفتوح المصدر بموجب ترخيص GNU AGPL v3.0.\n\nتخضع حقوق استخدام البرنامج ونسخه وتعديله وإعادة توزيعه لأحكام الترخيص المفتوح المصدر المعتمد، مع استمرار سريان التراخيص والإشعارات الخاصة بالمكونات التابعة لجهات خارجية.\n\nلا تشكل هذه البيانات التعريفية تعديلًا لشروط GNU AGPL v3.0 أو تقييدًا للحقوق التي يمنحها الترخيص للمستخدمين والمطورين.",
        "Terms intro en": "NextPDF Pro is a PDF editing, creation, conversion, and management application established, created, and developed under Future of Automation (مستقبل الأتمتة), with Next Ai Agent and Future ai agent presented as part of the project's identity.\n\nNextPDF Pro is distributed as free and open-source software under the GNU AGPL v3.0 license.\n\nUse, modification, copying, and redistribution are governed by the applicable open-source license, while third-party components retain their respective licenses and copyright notices.\n\nThese project credits do not modify the GNU AGPL v3.0 license or restrict the rights it grants.",
        # Misc
        "Close": "إغلاق",
        "Unsupported rotation": "دوران غير مدعوم",
        "Only horizontal text can be edited safely.": "يمكن تحرير النص الأفقي فقط بأمان.",
        "The selected text is not editable.": "النص المحدد غير قابل للتحرير.",
        "Scanned page: no editable text layer.": "صفحة مسحوبة ضوئياً: لا يوجد طبقة نص قابلة للتحرير.",
        # Conversion PDF
        "Convert PDF": "تحويل PDF",
        "to Word": "إلى وورد",
        "to Excel": "إلى إكسل",
        "to PowerPoint": "إلى باوربوينت",
        "to PNG": "إلى صور",
        "to JPG": "إلى JPG",
        "to TIFF": "إلى TIFF",
        "to TXT": "إلى TXT",
        "to HTML": "إلى HTML",
        "to CSV": "إلى بيانات الجداول",
        "Searchable PDF": "PDF قابل للبحث",
        "OCR": "التعرف الضوئي (OCR)",
        "Create PDF": "إنشاء PDF",
        "From files": "من الملفات",
        "Recognition": "التعرف",
        "Images to PDF": "صور إلى PDF",
        "Text to PDF": "نص إلى PDF",
        "Create from files": "إنشاء من ملفات",
        "No extractable tables were found in this PDF. Try a document with a clearly structured table or use another extraction method.": "لم يتم العثور على جداول قابلة للاستخراج من ملف PDF. يمكنك تجربة ملف يحتوي على جداول واضحة أو استخدام طريقة استخراج مختلفة.",
        "No supported tables were found in this PDF. Try a document with a clearly structured table or use another extraction method.": "لم يتم العثور على جداول قابلة للاستخراج من ملف PDF. يمكنك تجربة ملف يحتوي على جداول واضحة أو استخدام طريقة استخراج مختلفة.",
        "No supported tables were found": "لم يتم العثور على جداول قابلة للاستخراج من ملف PDF. يمكنك تجربة ملف يحتوي على جداول واضحة أو استخدام طريقة استخراج مختلفة.",
        "Unsupported conversion options": "خيارات التحويل غير مدعومة",
        "Invalid page selection": "اختيار صفحات غير صالح",
        "This output format requires one selected page": "هذه الصيغة تتطلب صفحة واحدة محددة",
    },
    "en": {},
}
# fmt: on

# English keys map to themselves; keep the explicit table above as the single
# source of truth for both languages.  A few keys are tokens rather than the
# English sentence itself, so their English text is set explicitly here.
TRANSLATIONS["en"] = {key: key for key in TRANSLATIONS["ar"]}
TRANSLATIONS["en"]["Terms intro en"] = TRANSLATIONS["ar"]["Terms intro en"]


class Translator:
    """Small, dependency-free translator with an explicit language setter."""

    def __init__(self, language: str = "en"):
        self._language = language if language in TRANSLATIONS else "en"

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language in TRANSLATIONS:
            self._language = language
        else:
            logger.warning("Unknown language %r; keeping %r", language, self._language)

    def is_rtl(self) -> bool:
        return self._language == "ar"

    def tr(self, key: str, **kwargs) -> str:
        """Translate *key*; format placeholders when kwargs are supplied."""
        text = TRANSLATIONS.get(self._language, {}).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                logger.warning("Bad translation placeholders for %r", key)
        return text

    # Backwards-compatible names used by older code.
    def get(self, key: str, default=None) -> str:
        return self.tr(key) if key in TRANSLATIONS["ar"] else (default if default is not None else key)


_translator = Translator("en")


def get_translator() -> Translator:
    return _translator


def set_translator_language(language: str) -> Translator:
    _translator.set_language(language)
    return _translator


def tr(key: str, **kwargs) -> str:
    return _translator.tr(key, **kwargs)
