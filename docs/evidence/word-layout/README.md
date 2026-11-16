# أدلة تنسيق تحويل PDF إلى Word (الإصدار 1.5.0، 2026-11-16)

السكربتات هنا هي التي بُنيت عليها قرارات هذا البند. تُشغَّل من جذر المشروع بـ
`.venv\Scripts\python.exe -X utf8 docs\evidence\word-layout\<script> <ملف.pdf>`
ولا تعدّل شيئًا في المشروع. `probe_word_alignment.py` وحده لا يأخذ ملفًا لأنه
يولّد مستنده بنفسه.

| الملف | ماذا يقيس |
|---|---|
| `probe_word_structure.py` | يصدّر الملف إلى DOCX ثم يفتحه ويطبع عدد الفقرات والجداول، وعروض الأعمدة، وألوان التظليل، وأسماء الخطوط. الأساس الذي قيست عليه نتيجة 144 فقرة ← 33 فقرة و2 جدول. |
| `probe_column_widths.py` | يقارن لكل عمود: الحد الذي رسمه المكتشف مقابل أعرض نص فعلي داخله. أظهر أن عمود التاريخ حدّه 39.1 نقطة ونصه 39.1 نقطة بلا أي فائض، وهو سبب التفافه على سطرين، وأن عمود «التصنيف / الطرف» عنده 98.1 نقطة فائض يمكن أخذها. |
| `probe_word_alignment.py` | يولّد ملف DOCX بثلاث فقرات عربية ويفتحه Word. أثبت أن `w:jc=right` داخل فقرة فيها `w:bidi` يُرسم على الحافة **اليسرى**، وأن `left` هو ما يثبّت النص يمينًا. |

## التحقق البصري

أُجري التحقق البصري على كشف حساب بنكي حقيقي: الصفحة الأولى من الـ PDF الأصلي
مقابل الصفحة الأولى من نفس الملف بعد تصديره إلى DOCX ثم **فتحه في Microsoft
Word 16 وتصديره منه إلى PDF**، فالمقارنة رسم Word نفسه لا محاكاة له. وأُعيد
التحقق نفسه على ناتج `NextPDF-Pro.exe` المبني.

الصور الثلاث (`source-page1.png` و`word-page1.png` و`exe-word-page1.png`) تبقى
محليّة ولا تُرفَع، لأنها تعرض اسم صاحب الحساب وأرصدته وكل عملياته. لإعادة
إنتاجها شغّل `probe_word_structure.py` على كشف حسابك ثم افتح `rebuilt.docx` في
Word.

## نتائج مرجعية (من آخر تشغيل)

```
probe_word_structure.py
paragraphs: 33 (total 36)      tables: 2
section: 842 x 595  orient=LANDSCAPE
table 0: 19 rows x 9 cols   bidiVisual: True
  header: التاريخ | رقم | النوع | البيان | الحساب | التصنيف / الطرف | وارد | صادر | الرصيد
  header fill 0B1647   header run: Tajawal 8.5 bold FFFFFF
  row fills alternate FFF6DA / None / F4F7FF

probe_column_widths.py
usable width 769.9   measured total 741.3   content total 463.4
col 8 (التاريخ)  measured 39.1  content 39.1  slack 0.0   <- كان يلتف
col 3 (التصنيف)  measured 164.7 content 66.6  slack 98.1  <- مصدر المساحة

probe_word_alignment.py (مرسومة بـ Word 16)
RIGHT + bidi -> النص على الحافة اليسرى
LEFT  + bidi -> النص على الحافة اليمنى
```
