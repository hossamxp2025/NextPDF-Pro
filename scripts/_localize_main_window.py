import pathlib

p = pathlib.Path('src/ui/main_window.py')
s = p.read_text(encoding='utf-8')
repls = [
 ('QMessageBox.critical(self, "خطأ / Error", f"فشل إنشاء مستند جديد: {e}")',
  'QMessageBox.critical(self, tr("Error"), f"{tr(\'Failed to create a new document\')}: {e}")'),
 ('"فتح ملف PDF / Open PDF File",\n            "",\n            "ملفات PDF (*.pdf)"',
  'tr("Open PDF File"),\n            "",\n            f"{tr(\'PDF files\')} (*.pdf)"'),
 ('QMessageBox.critical(self, "خطأ / Error", f"فشل فتح الملف: {e}")',
  'QMessageBox.critical(self, tr("Error"), f"{tr(\'Failed to open the file\')}: {e}")'),
 ('self.status_label.setText("تم الحفظ / Saved")',
  'self.status_label.setText(tr("Saved"))'),
 ('"حفظ باسم / Save As",\n            "",\n            "ملفات PDF (*.pdf)"',
  'tr("Save As"),\n            "",\n            f"{tr(\'PDF files\')} (*.pdf)"'),
 ('self.status_label.setText(f"تم الحفظ باسم: {os.path.basename(file_path)}")',
  'self.status_label.setText(f"{tr(\'Saved as\')}: {os.path.basename(file_path)}")'),
 ('QMessageBox.warning(self, "تنبيه / Warning", "يرجى فتح ملف PDF أولاً / Please open a PDF file first")',
  'QMessageBox.warning(self, tr("Warning"), tr("Please open a PDF file first"))'),
 ('self.status_label.setText("وضع تحرير النص - انقر على نص لتعديله / Text editing mode - Click text to edit")',
  'self.status_label.setText(tr("Text editing mode - Click text to edit"))'),
 ('QMessageBox.warning(self, "خطأ / Error", "لا يوجد عارض صفحات نشط / No active PDF viewer")',
  'QMessageBox.warning(self, tr("Error"), tr("No active PDF viewer"))'),
 ('self.status_label.setText("وضع إضافة نص - انقر في الصفحة لإضافة نص / Add text mode - Click page to add text")',
  'self.status_label.setText(tr("Add text mode - Click page to add text"))'),
 ('"اختر صورة / Select Image",',
  'tr("Select Image"),'),
 ('self.status_label.setText("تم إدراج الصورة / Image inserted")',
  'self.status_label.setText(tr("Image inserted"))'),
 ('self.status_label.setText("تم إدراج صفحة فارغة / Blank page inserted")',
  'self.status_label.setText(tr("Blank page inserted"))'),
 ('self.status_label.setText("تم حذف الصفحة / Page deleted")',
  'self.status_label.setText(tr("Page deleted"))'),
 ('self.status_label.setText("تم دوران الصفحة / Page rotated")',
  'self.status_label.setText(tr("Page rotated"))'),
 ('self, "OCR غير متاح / OCR Not Available",',
  'self, tr("OCR Not Available"),'),
 ('dialog.setWindowTitle("نتائج OCR / OCR Results")',
  'dialog.setWindowTitle(tr("OCR Results"))'),
 ('self.status_label.setText("تم تحديد صورة / Image selected")',
  'self.status_label.setText(tr("Image selected"))'),
 ('self.status_label.setText(f"تم تحديد نص: {run.text[:30]}...")',
  'self.status_label.setText(f"{tr(\'Text selected\')}: {run.text[:30]}...")'),
]
missing = []
for a, b in repls:
    if a not in s:
        missing.append(a[:70])
    else:
        s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print("missing:", missing)
