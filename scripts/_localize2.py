import pathlib
p = pathlib.Path('src/ui/main_window.py')
s = p.read_text(encoding='utf-8')
pairs = [
 ('self.status_label.setText(f"تم التراجع: {desc}")',
  'self.status_label.setText(f"{tr(\'Undone\')}: {desc}")'),
 ('self.status_label.setText(f"تم الإعادة: {desc}")',
  'self.status_label.setText(f"{tr(\'Redone\')}: {desc}")'),
 ('"صور (*.png *.jpg *.jpeg *.bmp *.gif)"',
  'f"{tr(\'Images\')} (*.png *.jpg *.jpeg *.bmp *.gif)"'),
]
for a, b in pairs:
    assert a in s, a
    s = s.replace(a, b)
p.write_text(s, encoding='utf-8')

p = pathlib.Path('src/commands/command.py')
s = p.read_text(encoding='utf-8')
pairs = [
 ('return f"تعديل نص / Edit text: {self._new_text[:30]}"',
  'return f"Edit text: {self._new_text[:30]}"'),
 ('return f"إضافة نص جديد / Insert text: {self._text[:30]}"',
  'return f"Insert text: {self._text[:30]}"'),
 ('return "حذف نص / Delete text"',
  'return "Delete text"'),
]
for a, b in pairs:
    assert a in s, a
    s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print("localized")
