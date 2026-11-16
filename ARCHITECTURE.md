# معمارية NextPDF Pro

## نظرة عامة

NextPDF Pro يتبع معمارية مودولية مع فصل واضح بين واجهة المستخدم ومحرك معالجة PDF.

## الطبقات المعمارية

### 1. طبقة العرض (Presentation Layer)
- `src/ui/main_window.py` - النافذة الرئيسية مع الشريط العلوي واللوحات
- `src/ui/pdf_viewer.py` - عارض الصفحات مع التكبير والتحديد
- لوائح الخصائص الديناميكية حسب العنصر المحدد

### 2. طبقة الأوامر (Command Layer)
- `src/commands/command.py` - نمط Command Pattern للتراجع والإعادة
- `CommandStack` - إدارة سجل الأوامر

### 3. طبقة المحركات (Engine Layer)
- `src/engine/text_editor.py` - تحرير النصوص الحقيقي (content stream manipulation)
- `src/engine/page_manager.py` - إدارة الصفحات (دمج، تقسيم، إلخ)
- `src/engine/image_editor.py` - تحرير الصور
- `src/engine/ocr_engine.py` - تحويل الصور إلى نص (OCR)

### 4. طبقة النموذج (Model Layer)
- `src/models/document.py` - PDFDocument, TextRun, ImageElement, ShapeElement, Annotation

### 5. طبقة العمال (Worker Layer)
- `src/workers/base_worker.py` - عمليات خلفية مع إمكانية الإلغاء

## أنماط التصميم المستخدمة

1. **Command Pattern**: للتراجع والإعادة عن كل عملية تحرير
2. **Model-View**: فصل البيانات عن العرض
3. **Modular Architecture**: كل محرك يعمل بشكل مستقل
4. **Worker Pattern**: العمليات الطويلة في خلفية خيوط منفصلة

## فصل العمليات

- **Rendering**: عرض الصفحات باستخدام PyMuPDF (fitz)
- **Editing**: تعديل Content Streams مباشرة باستخدام TextEditor
- **Serialization**: الحفظ باستخدام fitz.Document.save() مع garbage collection

## تدفق تحرير النص

1. المستخدم ينقر على نص في الصفحة
2. PDFViewer يحدد TextRun بناءً على الإحداثيات
3. TextEditor يعدل TextRun في النموذج
4. عند الحفظ، يتم تطبيق التغييرات على Content Stream للصفحة
5. يتم حذف النص القديم باستخدام Redaction وإدراج النص الجديد

## دعم العربية (RTL)

- اكتشاف تلقائي للنصوص العربية وتحديد اتجاهها كـ RTL
- استخدام خطوط تدعم العربية (Arial, Tahoma, Amiri, Cairo)
- قياس عرض النص باستخدام fitz.get_text_length()
- تحذير عند احتمالية فقدان التنسيق

## تقنيات التخزين

- SQLite للإعدادات والسجل المحلي
- JSON لملفات الإعدادات
- نسخ احتياطية تلقائية قبل الحفظ

## أمان الحفظ

- Atomic Save عند الإمكان
- نسخ احتياطية (.bak) قبل الكتابة فوق الملف الأصلي
- Save As للحفظ في مسار جديد