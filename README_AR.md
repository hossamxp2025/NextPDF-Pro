# NextPDF Pro

[![Release](https://img.shields.io/github/v/release/hossamxp2025/NextPDF-Pro?color=2563eb)](https://github.com/hossamxp2025/NextPDF-Pro/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/hossamxp2025/NextPDF-Pro/total?color=16a34a)](https://github.com/hossamxp2025/NextPDF-Pro/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-dc2626)](LICENSE)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)

**[⬇️ تحميل أحدث إصدار](https://github.com/hossamxp2025/NextPDF-Pro/releases/latest)** · [English](README.md)

NextPDF Pro هو محرر PDF احترافي ومفتوح المصدر لنظام ويندوز، مصمم لسير العمل بالعربية والإنجليزية. يجمع بين واجهة شريط علوي حديثة، والتعرف الضوئي على الحروف (OCR) للغة العربية القابلة للبحث، وتحويلات مكتب أوفيس، وإنشاء ودمج ملفات PDF، والثيمات، والتعريب الكامل.

## الميزات

- **عرض وتحرير ملفات PDF** – فتح وعرض وتحرير مستندات PDF باستخدام PyMuPDF/MuPDF
- **تحرير عربي حقيقي** – النص الذي تضيفه أو تعدّله يُشكَّل بـ HarfBuzz ويُحفظ كـ Unicode منطقي، فيبقى قابلًا للبحث والتحديد والتصدير بعد الحفظ؛ وتعديل السطر يستبدله كاملًا بلا بقايا من النص القديم
- **التعرف الضوئي على الحروف باللغة العربية (OCR)** – تحويل الصور الماسحة إلى ملفات PDF قابلة للبحث باستخدام Tesseract (اللغة العربية، الإنجليزية، والمختلط)
- **إنشاء ملفات PDF** – إنشاء ملفات PDF من الصور، النصوص، DOCX، XLSX، PPTX، HTML، CSV؛ دمج عدة صور في ملف PDF واحد
- **تحويلات مكتب أوفيس** – تصدير ملفات PDF إلى DOCX قابلة للتحرير، PPTX، XLSX مع دعم اتجاه النص من اليمين إلى اليسار (RTL) للغة العربية
- **واجهة الشريط العلوي (Ribbon)** – 11 تبويب باللغتين العربية والإنجليزية، مع أيقونات SVG ملونة ونصائح تلميحية
- **الثيمات** – ثيمات فاتحة، غامقة، ونظام مع التبديل المباشر دون التأثير على المستندات
- **التعريب الكامل** – واجهة مستخدم كاملة بالعربية والإنجليزية مع اتجاه RTL؛ بدون خلط لغوي
- **OCR محمول بلا محرك منفصل** – التعرف يعمل على Tesseract المدمج داخل MuPDF، فالإصدار يحمل 5 ميجابايت من بيانات اللغة (ara وeng) بدل 175 ميجابايت من ملفات Tesseract التنفيذية؛ لا حاجة لتثبيت أي شيء على النظام
- **التكبير** – شريط انزلاقي حقيقي للتكبير (10–800%) متزامن عبر العروض

## التحميل

نزّل أحدث إصدار من [صفحة الإصدارات](https://github.com/hossamxp2025/NextPDF-Pro/releases/latest):

| الملف | استخدمه لو… |
|---|---|
| `NextPDF-Pro-Setup-<version>.exe` | عايز تثبيت عادي مع اختصارات في قائمة ابدأ (مُستحسن) |
| `NextPDF-Pro.exe` | عايز نسخة محمولة في ملف واحد بدون تثبيت (حوالي 89MB) |
| `SHA256SUMS.txt` | للتحقق من سلامة الملف: `Get-FileHash .\NextPDF-Pro.exe -Algorithm SHA256` |

> الملفات غير موقّعة رقميًا حتى الآن، فقد يظهر تحذير Windows SmartScreen أول مرة. اختر **مزيد من المعلومات ← التشغيل على أي حال**، أو ابنِ البرنامج من المصدر.

## المتطلبات

- ويندوز 10/11 (x64)
- بايثون 3.12+ (للتطوير من المصدر)
- لا حاجة لتثبيت Tesseract (المحرك مدمج داخل MuPDF)

## البناء من المصدر

```bash
# استنساخ المستودع
git clone <رابط-المستودع>
cd NextPDF-Pro

# إنشاء وتنشيط البيئة الافتراضية
python -m venv .venv
.venv\Scripts\activate

# تثبيت التبعيات
pip install -r requirements.txt

# تثبيت PyInstaller (لبناء الملف التنفيذي)
pip install pyinstaller

# إنشاء بيانات الإصدار
python build/generate_metadata.py

# بناء الملف التنفيذي المستقل (ملف واحد)
python build/build_exe.py

# اختياري: بناء مثبت Inno Setup
python build/build_exe.py --installer
```

يكتب سكريبت البناء إلى مجلد مصدّر (`dist/release-<version>/`) بحيث لا يتم استبدال الإصدارات الموجودة.

## OCR المحمول

التعرف يستخدم Tesseract المدمج داخل MuPDF عبر `Pixmap.pdfocr_tobytes`، فلا يُشحن `tesseract.exe` ولا أي من مكتباته. المضمَّن هو `ara.traineddata` و`eng.traineddata` فقط تحت `resources/tessdata/`. لا حاجة لتثبيت Tesseract على النظام.

## الترخيص

هذا المشروع مرخص بموجب **الرخصة العمومية affine العامة من جنو الإصدار 3.0** (AGPL-3.0). راجع [`LICENSE`](LICENSE) للنص الكامل.

إشعارات المكونات الخارجية موجودة في [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## هيكل المستودع

```
NextPDF-Pro/
├── src/                 # كود مصدر التطبيق
├── tests/               # مجموعة الاختبارات (pytest)
├── resources/           # الأيقونات، الخطوط، بيانات لغات OCR (tessdata)
├── build/               # مواصفات PyInstaller، سكريبت Inno Setup، سكريبتات البناء
├── docs/                # التوث ولقطات الشاشة الدليلية
├── LICENSE              # AGPL-3.0
├── THIRD_PARTY_NOTICES.md
├── README.md            # هذا الملف (بالإنجليزية)
├── README_AR.md         # العربية (هذا الملف)
├── CONTRIBUTING.md
├── CHANGELOG.md
├── requirements.txt
└── .gitignore
```

## الاختبار

```bash
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short -p no:cacheprovider
```

## ملفات الإصدار الناتجة

- `dist/release-<version>/NextPDF-Pro.exe` – ملف تنفيذي محمول مستقل (OneFile)
- `dist/release-<version>/NextPDF-Pro-Setup-<version>.exe` – مثبت Inno Setup
- مجموعات التحقق SHA256 في `SHA256SUMS.txt`