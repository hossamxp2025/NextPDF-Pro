# تعليمات البناء والنشر - NextPDF Pro

## المتطلبات

1. **Python 3.8+** - مثبت على نظام Windows
2. **PyInstaller** - لبناء ملف EXE المستقل
3. **Inno Setup 6** - لبناء ملف تثبيت Windows (Setup.exe)

لا يلزم تثبيت Tesseract: محرك التعرف الضوئي مدمج داخل MuPDF، والمشحون معه
بيانات اللغتين في `resources/tessdata` فقط.

## تحميل المكونات المطلوبة

- Python: https://python.org
- Inno Setup 6: https://jrsoftware.org/isinfo.php

## الخطوات

### 1. تثبيت التبعيات

```bash
cd "D:\CAP CAT OTER\PDF DEEB\NextPDF Pro"
pip install -r requirements.txt
```

### 2. تشغيل التطبيق (للتطوير والاختبار)

```bash
run_app.bat
```

### 3. تشغيل الاختبارات

```bash
run_tests.bat
```

### 4. إنشاء ملف اختبار PDF

```bash
create_test_pdf.bat
```

### 5. بناء ملف EXE المستقل

```bash
build_app.bat
```

سيقوم هذا بإنشاء `dist/release/NextPDF-Pro.exe` - ملف 실행 مستقل لا يحتاج Python.

### 6. بناء ملف التثبيت (Setup.exe)

```bash
build_app_installer.bat
```

يتطلب تثبيت Inno Setup 6 على النظام.

سيقوم هذا بإنشاء `dist/release/NextPDF-Pro-Setup.exe` - ملف تثبيت Windows احترافي.

## مخرجات البناء النهائية

المجلد `dist/release/` يحتوي على:

| الملف | الوصف |
|-------|-------|
| `NextPDF-Pro.exe` | التطبيق التنفيذي المستقل (x64) |
| `NextPDF-Pro-Setup.exe` | ملف تثبيت Windows احترافي |
| `README.txt` | تعليمات الاستخدام |
| `VERSION.txt` | رقم الإصدار |
| `LICENSES.txt` | تراخيص المكتبات الخارجية |
| `SHA256SUMS.txt` | مجموعات التجزئة للتحقق من سلامة الملفات |
| `TEST_REPORT.txt` | تقرير نتائج الاختبار |

## اختبار على جهاز Windows نظيف

1. نسخ `NextPDF-Pro-Setup.exe` إلى جهاز Windows 10/11 x64 لا يحتوي على Python
2. تشغيل ملف الإعداد والنقر مرتين للتثبيت
3. تشغيل البرنامج من اختصار سطح المكتب أو قائمة ابدأ
4. فتح ملف PDF واختبار التحرير
5. حفظ المستند وإعادة فتحه للتحقق
6. إلغاء تثبيت البرنامج من لوحة التحكم

## ملاحظات هامة

- لا يحتاج المستخدم النهائي إلى Python أو أي أدوات تطوير
- جميع ملفات DLL وQtPlugins والموارد مضمّنة في التوزيع
- يدعم Windows 10 و Windows 11 (64-bit فقط)
- OCR يعمل دون أي تثبيت: المحرك مدمج داخل MuPDF وبيانات اللغتين مضمَّنة
- لم يتم اختبار ARM64 بعد - يدعم x64 فقط حاليًا