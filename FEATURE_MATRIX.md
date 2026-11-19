# مصفوفة الميزات - NextPDF Pro v1.6.1

| الميزة | الحالة | ملاحظات |
|--------|--------|---------|
| واجهة حديثة (Modern Dark Theme) | Implemented & Tested | QSS احترافي مع ألوان مريحة |
| Ribbon Toolbar بتبويبات | Implemented & Tested | 12 تبويبًا: Home, Edit PDF, Insert, Organize Pages, Convert PDF, Create PDF, OCR, Forms, Review, Protect and Sign, View, Settings |
| أزرار احترافية مع أيقونات | Implemented & Tested | ModernButton مع hover/pressed/disabled states |
| اللوحة اليسرى - الصور المصغرة | Implemented & Tested | ThumbnailPanel مع Cards للصفحات |
| اللوحة اليمنى - الخصائص | Implemented & Tested | PropertiesPanel مع Empty State |
| منطقة العمل الوسطى | Implemented & Tested | PDFViewer مع تكبير 10%-800% |
| Empty State عند عدم فتح ملف | Implemented & Tested | أيقونة كبيرة، نص واضح، زر فتح |
| شريط حالة سفلي | Implemented & Tested | رقم الصفحة، نسبة التكبير، حالة المستند |
| دعم RTL (العربية) | Implemented & Tested | تخطيط من اليمين لليسار |
| دعم LTR (الإنجليزية) | Implemented & Tested | تخطيط من اليسار لليمين |
| تبديل اللغة العربية/الإنجليزية | Implemented & Tested | تبديل ديناميكي دون إعادة تشغيل |
| High DPI و4K دعم | Implemented & Tested | Qt HighDPI scaling |
| فتح ملف PDF | Implemented & Tested | باستخدام PyMuPDF/pymupdf |
| عرض صفحات PDF | Implemented & Tested | مع تكبير وتصغير |
| تحرير نص إنجليزي | Implemented & Tested | تحرير أصلي في content stream |
| تحرير نص عربي (RTL) | Implemented & Tested | مع Arabic Shaping |
| تغيير مبلغ مالي | Implemented & Tested | اختبار إلزامي مكتمل |
| إضافة نص جديد | Implemented & Tested | مربع نص جديد |
| حذف نص | Implemented & Tested | |
| نقل نص | Implemented & Tested | |
| تغيير خط وحجم ولون | Implemented & Tested | |
| إدراج صورة | Implemented & Tested | |
| استبدال صورة | Implemented & Tested | |
| حذف صورة | Implemented & Tested | |
| تغيير حجم صورة | Implemented & Tested | |
| دوران صورة | Implemented & Tested | |
| نقل صورة | Implemented & Tested | |
| دمج ملفات PDF | Implemented but Not Tested | |
| تقسيم ملفات PDF | Implemented but Not Tested | |
| استخراج صفحات | Implemented but Not Tested | |
| حذف صفحة | Implemented & Tested | |
| إدراج صفحة | Implemented & Tested | |
| إعادة ترتيب صفحات | Implemented but Not Tested | |
| دوران صفحة | Implemented & Tested | |
| صفحة فارغة | Implemented & Tested | |
| OCR عربي | Implemented | محرك مدمج في MuPDF، لا يحتاج تثبيتًا؛ مُتحقق في `tests/test_ocr_integration.py` |
| OCR إنجليزي | Implemented | محرك مدمج في MuPDF، لا يحتاج تثبيتًا |
| PDFقابل للبحث | Partially Implemented | |
| التعليقات (تظليل، ملاحظة، نص، أشكال) | Implemented & Tested | تعليقات PDF حقيقية يراها أي قارئ آخر؛ تحديد وتعديل وحذف وقائمة، وتراجع/إعادة لكل عملية. `tests/test_annotations.py` و`tests/test_annotations_ui.py` |
| نص على الصفحة بالعربية (FreeText) | Not Implemented | مرفوض صراحةً: خطوط PDF القياسية لا تشكّل العربية، والبديل المعروض هو الملاحظة اللاصقة أو محرر النص |
| النماذج التفاعلية (AcroForms) | Implemented & Tested | قراءة الحقول وتعبئتها وحفظها، وإنشاء حقل نص ومربع اختيار وقائمة اختيارات، وحذف حقل، وتثبيت النموذج؛ تراجع/إعادة لكل عملية. `tests/test_forms.py` و`tests/test_forms_ui.py` |
| قيمة عربية في حقل نص | Implemented with a stated limit | القيمة تُحفظ كما كُتبت تمامًا، لكن الصورة المرسومة داخل الحقل بخطوط PDF القياسية لا تشكّل العربية؛ التثبيت يعيد رسمها بخط يشكّلها |
| XFA Forms | Not Implemented | النماذج الديناميكية غير مدعومة |
| الختم المرئي (صورة) | Implemented & Tested | صورة تُرسم على الصفحة كمحتوى لا كتعليق، بنسبها محفوظة، ويمكن جعل خلفيتها البيضاء شفافة؛ تراجع/إعادة. `tests/test_stamps.py` |
| الختم المرئي (اسم مكتوب) | Implemented & Tested | يُرسم بمحرك النص الذي يضمّن خطًا يشكّل العربية، فيظهر صحيحًا في أي قارئ ويبقى قابلًا للبحث |
| التوقيع الرقمي | Implemented & Tested | توقيع بشهادة PKCS#12 (ظاهر أو غير ظاهر) وتحقّق يفصل **سلامة الملف** عن **ثقة الموقِّع**، ويُكتب في نسخة جديدة فالأصل لا يُمَس. يُرفض توقيع مستند فيه تعديلات غير محفوظة. `tests/test_signing.py` و`tests/test_signing_ui.py` (41 اختبارًا) |
| ختم زمني من سلطة توقيت وبيانات الإبطال (PAdES B-LT/LTA) | Not Implemented | وقت التوقيع المسجَّل هو ما أبلغ به جهاز الموقِّع، ولا يصلح دليلًا على وقت التوقيع. مذكور في كل تقرير تحقّق وفي رسالة النجاح |
| حماية بكلمة مرور | Implemented & Tested | AES-256 بكلمة مرور فتح وكلمة مرور مالك وصلاحيات (طباعة، نسخ، تعديل، تعليقات)؛ `tests/test_protection.py` |
| فتح ملف محمي بكلمة مرور | Implemented & Tested | ثلاث محاولات مع تمييز «كلمة المرور غلط» |
| إزالة الحماية | Implemented & Tested | تتطلب طلبًا صريحًا؛ الحفظ العادي يحافظ على التشفير |
| إزالة بيانات المستند | Implemented & Tested | الميتاداتا و XMP |
| Redaction آمن | Implemented & Tested | بالنص أو بتحديد منطقة بالسحب؛ المحتوى يُحذف من الصفحة ولا يُغطّى. `tests/test_redaction.py` |
| PDF to Word (صور صفحات) | Implemented & Tested | المظهر محفوظ، غير قابل للتحرير |
| PDF to Word (قابل للتحرير) | Implemented & Tested | 1.5.0: جداول Word حقيقية بعروض أعمدة وتظليل، أسماء خطوط من الخط المضمَّن، ترتيب قراءة RTL، صور في مواضعها. المواضع المطلقة لا تُستنسخ |
| PDF/A | Not Implemented | |
| مقارنة ملفين | Not Implemented | |
| معالجة دُفعية | Not Implemented | |
| تحسين ضغط PDF | Implemented & Tested | إزالة ما لا يحتاجه الملف + إعادة ترميز الصور؛ يبلّغ الحجم قبل وبعد، وإذا لم ينقص الحجم يقول ذلك ولا يكتب ملفًا أكبر. يحافظ على التشفير. `tests/test_compression.py` |
| تحكم في دقة التصدير (DPI) | Implemented & Tested | 72–600 في حوار التحويل، ويظهر فقط مع الصيغ التي تُرسَم صورًا |
| تصدير عدة صفحات صورًا | Implemented & Tested | PNG/JPEG/WEBP تُكتب ملفات مرقَّمة، وTIFF يضمّها في ملف واحد |
| Markdown حقيقي | Implemented & Tested | عناوين من أحجام النص، جداول بصيغة pipe، تأكيد عريض/مائل. `tests/test_markdown_export.py` |
| قراءة آلية للملف الممسوح عند التحويل | Implemented & Tested | الصفحة بلا طبقة نص تُقرأ آليًا ويُعلَّم ناتجها أنه مقروء آليًا |
| طباعة | Implemented & Tested | حوار الطباعة النظامي مع نطاق الصفحات |
| خصائص المستند | Implemented & Tested | ملف، صفحات، مقاس، بيانات المستند، حالة الحماية والصلاحيات (للعرض فقط) |
| EXE مستقل | Built | تم بناؤه باستخدام PyInstaller |
| Setup Installer | Built | تم بناؤه باستخدام Inno Setup |
| التراجع والإعادة | Implemented & Tested | Command Pattern |
| اختصارات لوحة مفاتيح | Implemented & Tested | Ctrl+N, Ctrl+O, Ctrl+S, إلخ |
| أيقونات SVG placeholder | Implemented & Tested | 12 أيقونة للوظائف الأساسية |
| حفظ الإعدادات | Implemented & Tested | QByteArray serialization عبر base64 |