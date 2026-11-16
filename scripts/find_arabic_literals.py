import pathlib
import re

pat = re.compile(r'[\u0600-\u06FF]')
quote_chars = ('"', "'")
for name in ['src/ui/pdf_viewer.py', 'src/ui/components.py', 'src/ui/ocr_dialog.py',
             'src/ui/main_window.py', 'src/commands/command.py']:
    for i, line in enumerate(pathlib.Path(name).read_text(encoding='utf-8').splitlines(), 1):
        text = line.strip()
        if not pat.search(text) or text.startswith('#'):
            continue
        if not any(q in text for q in quote_chars):
            continue
        print(f'{name}:{i}: {text[:130]}')
