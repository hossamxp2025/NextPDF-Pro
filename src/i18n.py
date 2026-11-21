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
        "Text formats export logical text, not original layout. SVG requires one selected page. Several pages of PNG, JPEG or WEBP are written as numbered files beside the one you name; TIFF holds them all in one file.": "الصيغ النصية تصدر النص المنطقي لا التخطيط الأصلي. تتطلب SVG صفحة محددة واحدة. وإذا اخترت عدة صفحات بصيغة PNG أو JPEG أو WEBP تُكتب ملفات مرقَّمة بجوار الملف الذي سمّيته، أما TIFF فيضمّها كلها في ملف واحد.",
        "Resolution": "الدقة",
        # Visible stamp
        "Visible stamp": "ختم مرئي",
        "Stamp an image": "ختم بصورة",
        "Stamp a name": "ختم باسم",
        "What a stamp is not": "ما لا يفعله الختم",
        "A visible stamp is a picture or text placed on the page. It is not a digital signature: it does not prove who placed it and it cannot detect a later change to the file. For that, use Sign with a certificate.":
            "الختم المرئي صورة أو نص يوضع على الصفحة. وهو ليس توقيعًا رقميًا: لا يثبت من وضعه، ولا يكشف تغييرًا يحدث للملف بعده. ولهذا الغرض استخدم «التوقيع بشهادة».",
        "Drag where the stamp belongs": "اسحب في المكان الذي تريد الختم فيه",
        "Stamp mode: drag where the stamp belongs":
            "وضع الختم: اسحب في المكان الذي تريد الختم فيه",
        "Choose the stamp image": "اختر صورة الختم",
        "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)":
            "الصور (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)",
        "Make the white background of the image transparent?":
            "أجعل خلفية الصورة البيضاء شفافة؟",
        "The text of the stamp": "نص الختم",
        "The stamp was placed.": "تم وضع الختم.",
        "The stamp could not be placed": "تعذّر وضع الختم",
        "The stamp area is too small": "منطقة الختم صغيرة جدًا",
        "The image file was not found": "ملف الصورة غير موجود",
        "The image could not be read": "تعذّر قراءة الصورة",
        "The stamp needs its text": "الختم يحتاج نصه",
        # Forms
        "Forms": "النماذج",
        "Fill": "تعبئة",
        "Build": "إنشاء",
        "Fill the form": "تعبئة النموذج",
        "Flatten the form": "تثبيت النموذج",
        "Add a text field": "إضافة حقل نص",
        "Add a tick box": "إضافة مربع اختيار",
        "Add a list of choices": "إضافة قائمة اختيارات",
        "Remove a field": "حذف حقل",
        "Field name": "اسم الحقل",
        "Fields": "الحقول",
        "Filled fields": "الحقول المعبّأة",
        "Flattened fields": "الحقول المثبَّتة",
        "Choices": "الاختيارات",
        "The choices, separated by commas": "الاختيارات مفصولة بفواصل",
        "A list of choices needs its choices.": "قائمة الاختيارات تحتاج اختياراتها.",
        "This document has no interactive fields.": "لا توجد حقول تفاعلية في هذا المستند.",
        "Unnamed field": "حقل بلا اسم",
        "Nothing was filled": "لم تُعبَّأ أي حقول",
        "Nothing was flattened": "لم يُثبَّت شيء",
        "The field could not be added": "تعذّرت إضافة الحقل",
        "The field could not be removed": "تعذّر حذف الحقل",
        "Drag where the field belongs": "اسحب في المكان الذي تريد الحقل فيه",
        "Field mode: drag where the field belongs":
            "وضع الحقول: اسحب في المكان الذي تريد الحقل فيه",
        "The values become part of the page and the form stops being fillable. Continue?":
            "القيم ستصبح جزءًا من الصفحة ولن يعود النموذج قابلًا للتعبئة. أتريد المتابعة؟",
        "An Arabic value is stored exactly as you type it, but the picture "
        "drawn inside the field uses the standard PDF fonts, which cannot "
        "shape Arabic. Flatten the form to have it drawn correctly on the page.":
            "القيمة العربية تُحفظ كما كتبتها تمامًا، لكن الصورة المرسومة داخل "
            "الحقل تستخدم خطوط PDF القياسية وهي لا تشكّل العربية. ثبِّت النموذج "
            "ليُرسم النص على الصفحة بشكل صحيح.",
        # Comments (Review)
        "Comments": "التعليقات",
        "Shapes": "الأشكال",
        "Manage": "إدارة",
        "Highlight": "تظليل",
        "Sticky note": "ملاحظة لاصقة",
        "Text on the page": "نص على الصفحة",
        "Rectangle": "مستطيل",
        "Ellipse": "بيضاوي",
        "Line": "خط",
        "Edit the comment": "تعديل التعليق",
        "Delete the comment": "حذف التعليق",
        "List the comments": "قائمة التعليقات",
        "Comment text": "نص التعليق",
        "Click where the note belongs": "اضغط في المكان الذي تريد الملاحظة فيه",
        "Drag over the part you mean": "اسحب فوق الجزء الذي تقصده",
        "Comment mode: click where the note belongs":
            "وضع التعليق: اضغط في المكان الذي تريد الملاحظة فيه",
        "Comment mode: drag over the part you mean":
            "وضع التعليق: اسحب فوق الجزء الذي تقصده",
        "Click a comment on the page first.": "اضغط على تعليق في الصفحة أولًا.",
        "This document has no comments.": "لا توجد تعليقات في هذا المستند.",
        "The comment could not be added": "تعذّرت إضافة التعليق",
        "The comment could not be removed": "تعذّر حذف التعليق",
        "The comment could not be changed": "تعذّر تعديل التعليق",
        # File size, printing and properties
        "Size": "الحجم",
        "Reduce the file size": "تصغير حجم الملف",
        "Save the smaller file as": "احفظ الملف المصغَّر باسم",
        "Save the document first.": "احفظ المستند أولًا.",
        "There are unsaved changes. Save them first, so the smaller copy holds them too.":
            "فيه تعديلات غير محفوظة. احفظها أولًا حتى تكون موجودة في النسخة المصغَّرة.",
        "This file is already as small as this tool can make it; the copy is identical.":
            "هذا الملف بالفعل أصغر ما تستطيع الأداة الوصول إليه، والنسخة مطابقة له.",
        "Could not reduce the file size": "تعذّر تصغير حجم الملف",
        "Saved": "وُفِّر",
        "Printing failed": "فشلت الطباعة",
        "Sent to the printer": "أُرسل إلى الطابعة",
        "Location": "المكان",
        "File name": "اسم الملف",
        "File size": "حجم الملف",
        "Page size": "مقاس الصفحة",
        "Document information": "بيانات المستند",
        "Title": "العنوان",
        "Author": "المؤلف",
        "Subject": "الموضوع",
        "Keywords": "الكلمات المفتاحية",
        "Created with": "أُنشئ ببرنامج",
        "Produced by": "أُنتج ببرنامج",
        "Created on": "تاريخ الإنشاء",
        "Changed on": "تاريخ التعديل",
        "Protection": "الحماية",
        "Protected": "محمي",
        "Not protected": "غير محمي",
        "Allowed": "مسموح",
        "Not allowed": "غير مسموح",
        "Markdown: headings come from the text sizes on the page and detected tables become real tables. A scanned page is recognised automatically and marked as recognised.": "ماركداون: العناوين مأخوذة من أحجام النص على الصفحة، والجداول المكتشَفة تُكتب جداول حقيقية. الصفحة الممسوحة ضوئيًا تُقرأ آليًا ويُشار إلى أن نصها مقروء آليًا.",
        "Logical text, not the original layout. A scanned page is recognised automatically with the chosen language.": "نص منطقي لا تخطيط أصلي. الصفحة الممسوحة ضوئيًا تُقرأ آليًا باللغة المختارة.",
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
        # Protection
        "Protected file": "ملف محمي",
        "This file is protected. Enter its password.": "الملف محمي. اكتب كلمة المرور.",
        "Wrong password, try again": "كلمة المرور غير صحيحة، حاول مرة أخرى",
        "The file was not opened because the password did not match.":
            "لم يُفتح الملف لأن كلمة المرور غير مطابقة.",
        "Protect with a password": "حماية بكلمة مرور",
        "Remove protection": "إزالة الحماية",
        "Remove document information": "إزالة بيانات المستند",
        "Redact text": "إخفاء نص",
        "Security": "الحماية",
        "The open password is asked for when the file is opened. The owner "
        "password is what lifts the restrictions below, so it has to be "
        "different from the open password.":
            "كلمة مرور الفتح تُطلب عند فتح الملف. وكلمة مرور المالك هي التي ترفع "
            "القيود الموجودة بالأسفل، لذلك يجب أن تكون مختلفة عن كلمة مرور الفتح.",
        "Open password": "كلمة مرور الفتح",
        "Repeat the open password": "أعد كتابة كلمة مرور الفتح",
        "Owner password": "كلمة مرور المالك",
        "Permissions": "الصلاحيات",
        "Allow printing": "السماح بالطباعة",
        "Allow copying text": "السماح بنسخ النص",
        "Allow changing the document": "السماح بتعديل المستند",
        "Allow comments": "السماح بالتعليقات",
        "Also remove the document information": "إزالة بيانات المستند أيضًا",
        "Apply": "تطبيق",
        "The two open passwords are not the same.":
            "كلمتا مرور الفتح غير متطابقتين.",
        "Enter a password, or choose to remove the document information.":
            "اكتب كلمة مرور، أو اختر إزالة بيانات المستند.",
        "The owner password has to be different from the open password.":
            "يجب أن تكون كلمة مرور المالك مختلفة عن كلمة مرور الفتح.",
        "Restrictions need an owner password, otherwise whoever opens the "
        "file may do everything.":
            "القيود تحتاج كلمة مرور مالك، وإلا فمن يفتح الملف يستطيع فعل كل شيء.",
        "The document is now protected.": "المستند صار محميًا الآن.",
        "The protection was removed.": "تمت إزالة الحماية.",
        "The document information was removed.": "تمت إزالة بيانات المستند.",
        "This document is not protected.": "هذا المستند غير محمي.",
        "Text to redact": "النص المراد إخفاؤه",
        "The text will be removed from the file, not covered.":
            "سيُحذف النص من الملف ولن يُغطّى فقط.",
        "Nothing matched that text.": "لا يوجد ما يطابق هذا النص.",
        "Removed areas": "المواضع المحذوفة",
        "Hide an area": "إخفاء منطقة",
        "Apply the hidden areas": "تنفيذ الإخفاء",
        "Hiding mode: drag over what should be removed":
            "وضع الإخفاء: اسحب فوق ما تريد حذفه",
        "Drag over what should be removed, then apply.":
            "اسحب فوق ما تريد حذفه ثم نفّذ الإخفاء.",
        "Mark an area on the page first.": "حدّد منطقة على الصفحة أولًا.",
        "Redaction failed": "فشل الإخفاء",
        "Save the protected file as": "احفظ الملف المحمي باسم",
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
        # Digital signature
        "Digital signature": "التوقيع الرقمي",
        "Sign with a certificate": "التوقيع بشهادة",
        "Check the signatures": "التحقق من التوقيعات",
        "What a signature proves": "ما يثبته التوقيع",
        "A digital signature is added to a new copy of the file; this document is left as it is. The signature lets a reader prove the file has not changed since it was signed. Whether the reader also believes it was you depends on their trusting your certificate.":
            "يُضاف التوقيع الرقمي إلى نسخة جديدة من الملف، وهذا المستند يبقى كما هو. والتوقيع يتيح لأي قارئ أن يثبت أن الملف لم يتغير منذ توقيعه. أما أن يقتنع القارئ بأنك أنت من وقّع فذلك يعتمد على ثقته في شهادتك.",
        "Certificate": "الشهادة",
        "Browse": "استعراض",
        "Certificate file": "ملف الشهادة",
        "Certificate password": "كلمة مرور الشهادة",
        "Check the certificate": "فحص الشهادة",
        "What the signature records": "ما يسجّله التوقيع",
        "Name to show": "الاسم المعروض",
        "Reason": "السبب",
        "Place": "المكان",
        "Draw the signature on the page": "ارسم التوقيع على الصفحة",
        "An invisible signature is not a weaker one. It is simply not drawn.":
            "التوقيع غير المرئي ليس أضعف، إنما هو فقط غير مرسوم.",
        "Sign": "توقيع",
        "Choose a certificate": "اختر شهادة",
        "Certificate files": "ملفات الشهادات",
        "Choose a certificate file first.": "اختر ملف الشهادة أولًا.",
        "Signer": "الموقِّع",
        "Issued by": "جهة الإصدار",
        "Valid until": "صالحة حتى",
        "This certificate has expired.": "هذه الشهادة منتهية الصلاحية.",
        "This certificate signed itself, so no authority vouches for it. A signature made with it still proves the file has not changed, but a reader has no way to confirm who made it unless you give them this certificate yourself.":
            "هذه الشهادة وقّعت نفسها، فلا توجد جهة تشهد لها. والتوقيع بها يثبت أن الملف لم يتغير، لكن القارئ لا يملك وسيلة للتأكد من هوية من وقّع إلا إذا أعطيته هذه الشهادة بنفسك.",
        "Choose the certificate to sign with.": "اختر الشهادة التي ستوقّع بها.",
        "That certificate file does not exist.": "ملف الشهادة هذا غير موجود.",
        "Bottom right": "أسفل اليمين",
        "Bottom left": "أسفل اليسار",
        "Top right": "أعلى اليمين",
        "Top left": "أعلى اليسار",
        "This document has no digital signature.": "هذا المستند لا يحمل توقيعًا رقميًا.",
        "Signature": "توقيع",
        "not stated": "غير مذكور",
        "Signed at": "وقت التوقيع",
        "the time the signer claims, not a verified one":
            "الوقت الذي يذكره الموقِّع، وليس وقتًا موثَّقًا",
        "The file has not changed since it was signed.": "الملف لم يتغير منذ توقيعه.",
        "The file HAS changed since it was signed.": "الملف تغيّر بعد توقيعه.",
        "Something was added to the file after signing; the signature does not cover that part.":
            "أُضيف شيء إلى الملف بعد التوقيع، والتوقيع لا يشمل هذا الجزء.",
        "The certificate is trusted on this computer.": "الشهادة موثوقة على هذا الجهاز.",
        "The signer is not confirmed: no authority this computer trusts vouches for the certificate.":
            "هوية الموقِّع غير مؤكَّدة: لا توجد جهة يثق بها هذا الجهاز تشهد للشهادة.",
        "Reason given": "السبب المذكور",
        "Why the signer is not confirmed": "سبب عدم تأكيد الهوية",
        # Sentences the engine writes. English is the key here as everywhere,
        # so the report reads as Arabic instead of switching language halfway.
        "No trusted certificates were supplied, so nothing can be said about who signed this":
            "لم تُسلَّم أي شهادات موثوقة، فلا يمكن قول شيء عمّن وقّع هذا الملف",
        "No trusted timestamp: the signing time is the one the signer reported, not one a time authority confirmed":
            "لا ختم زمني موثوق: وقت التوقيع هو ما أبلغ به الموقِّع، لا وقت أكّدته سلطة توقيت",
        "The signer's certificate is not trusted here":
            "شهادة الموقِّع غير موثوقة هنا",
        "This signature could not be checked at all": "تعذّر فحص هذا التوقيع أصلًا",
        "The signature is present but could not be read": "التوقيع موجود لكن تعذّرت قراءته",
        "Something was added to the file after this signature was made; the signature covers only the part of the file up to that point":
            "أُضيف شيء إلى الملف بعد هذا التوقيع، والتوقيع يشمل الجزء السابق لتلك النقطة فقط",
        "No signing key could be read from the certificate. The password is probably wrong, or the file is not a PKCS#12 certificate with a private key in it.":
            "تعذّرت قراءة مفتاح توقيع من الشهادة. الأرجح أن كلمة المرور غير صحيحة، أو أن الملف ليس شهادة PKCS#12 تحمل مفتاحًا خاصًا.",
        "Place given": "المكان المذكور",
        "A digital signature does two separate things, and they are worth keeping apart.\n\nFirst, it lets any reader prove the file has not changed since it was signed. That part is arithmetic: it either holds or it does not, and nobody's opinion enters into it.\n\nSecond, it carries a certificate that claims who signed. That claim is worth something only to a reader who trusts the certificate. A certificate you made yourself proves nothing to anyone else until you give it to them by some other means they trust.\n\nWhat this program does not do: it does not add a timestamp from a time authority, so the signing time recorded is the one your computer reported and is not evidence of when you signed. It does not embed revocation data either, so a reader cannot check later whether the certificate was withdrawn.":
            "التوقيع الرقمي يفعل أمرين منفصلين، ويستحقان أن يُفرَّق بينهما.\n\nالأول: يتيح لأي قارئ أن يثبت أن الملف لم يتغير منذ توقيعه. وهذا الجزء حساب رياضي: إما يصح وإما لا، ولا يدخل فيه رأي أحد.\n\nالثاني: يحمل شهادة تدّعي من الذي وقّع. وهذا الادعاء لا قيمة له إلا عند قارئ يثق في الشهادة. والشهادة التي تصنعها بنفسك لا تثبت شيئًا لأحد غيرك حتى تسلّمها له بوسيلة أخرى يثق بها.\n\nوما لا يفعله هذا البرنامج: لا يضيف ختمًا زمنيًا من سلطة توقيت، فوقت التوقيع المسجَّل هو ما أبلغ به جهازك وليس دليلًا على وقت توقيعك. ولا يضمّن بيانات سحب الشهادة، فلا يستطيع القارئ أن يتحقق لاحقًا مما إذا كانت الشهادة قد سُحبت.",
        "Save this document to a file first. A signature is made over the bytes of a saved file.":
            "احفظ هذا المستند في ملف أولًا. التوقيع يُحسب على بايتات ملف محفوظ.",
        "This document has unsaved changes. Save them first, otherwise the signature would cover the file as it is on disk, not what you see.":
            "هذا المستند فيه تعديلات غير محفوظة. احفظها أولًا، وإلا سيغطي التوقيع الملف كما هو على القرص لا كما تراه أمامك.",
        "That page does not exist in this document": "هذه الصفحة غير موجودة في المستند",
        "Save the signed file as": "حفظ الملف الموقَّع باسم",
        "The document could not be signed": "لم يتمكن البرنامج من توقيع المستند",
        "The signed copy was written": "تمت كتابة النسخة الموقَّعة",
        "The signed copy is saved. The original is untouched. There is no timestamp from a time authority in it, and no revocation data, so it is not a long-term archival signature.":
            "تم حفظ النسخة الموقَّعة، والأصل لم يُمَس. ولا يوجد فيها ختم زمني من سلطة توقيت ولا بيانات سحب، فهي ليست توقيعًا أرشيفيًا طويل الأمد.",
        "The signatures could not be read": "لم يتمكن البرنامج من قراءة التوقيعات",
        "These results describe the file on disk. The unsaved changes in front of you are not part of it.":
            "هذه النتائج تصف الملف الموجود على القرص. والتعديلات غير المحفوظة التي أمامك ليست جزءًا منه.",
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
