# أدلة تصغير الحزمة (الإصدار 1.4.0، 2026-11-16)

| السكربت | ماذا يفعل |
|---|---|
| `pkg_sizes.py` | يقرأ `build/pyinstaller_build/NextPDF-Pro/PKG-00.toc` ويجمع أحجام ما دخل الحزمة فعلًا حسب المكوّن، مع أكبر الملفات المفردة. هو مصدر كل رقم "غير مضغوط" في التقرير. |
| `probe_mupdf_ocr.py` | يبني صفحة ممسوحة بالعربية والإنجليزية ويقارن ثلاثة مسارات: `get_textpage_ocr`، و`Pixmap.pdfocr_tobytes` (المعتمد)، وpytesseract الخارجي. هو أساس قرار الاستغناء عن `tesseract.exe`. |
| `check_excludes.py` | يحجب الوحدات المستبعدة في مواصفات PyInstaller عبر `meta_path` ثم يستورد التطبيق كاملًا ويشغّل تعرفًا حقيقيًا، للتأكد أن الاستبعاد لا يكسر شيئًا قبل البناء. |

## نتيجة `probe_mupdf_ocr.py` (مرجعية)

```
scan has no text layer: True
get_textpage_ocr FAILED: ReferenceError('weakly-referenced object no longer exists')
pdfocr_tobytes OK in 0.1s, 36289 bytes, pages=1
  [pdfocr] chars=72 hits={'المبلغ': 6, 'ريال': 4, 'Invoice': 1, 'TOTAL': 1}
      'Invoice INV-2026/0042 TOTAL DUE\nإجمالي المبلغ المستحق15,750.00ريال سعودي'
pytesseract: 'Invoice INV-2026/0042 TOTAL DUE\n\nإجمالي المبلغ المستحق 15,750.00 ريال سعودي'
```

`get_textpage_ocr` يفشل في PyMuPDF 2.1 بخطأ مرجع ضعيف، لذلك اعتُمد
`pdfocr_tobytes` وحده. جودة التعرف مطابقة لما كان يعطيه المحرك الخارجي.

## نتيجة `check_excludes.py` (مرجعية)

```
pymupdf 2.1
OCR engine=MuPDF built-in tessdata=.../resources/tessdata languages=['ara','eng'] available=True
recognised: PACKAGE SHRINK OK | boxes: 3
ALL IMPORTS AND OCR OK WITHOUT EXCLUDED MODULES
```
