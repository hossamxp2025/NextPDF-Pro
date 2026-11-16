import fitz
import sys

# إنشاء ملف PDF تجريبي بالعربية
doc = fitz.open()
page = doc.new_page()
page.insert_text(fitz.Point(50, 50), '\u0625\u064a\u062c\u0627\u0644\u064a \u0627\u0644\u0645\u064a\u0627\u064a\u0629 \u0627\u0644\u0645\u0633\u062a\u062d\u0642 15,750.00 \u0631\u064a\u0627\u0644 \u0633\u0639\u0648\u062f\u064a', fontsize=14)
doc.save('test_arabic.pdf')
doc.close()
print('تم إنشاء ملف الاختبار التجريبي بنجاح')
