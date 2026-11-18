"""Opt-in release acceptance using the real GUI and its real child executables.

Run: NextPDF-Pro.exe --verify-release <evidence-directory>
No external test framework or development paths are used.
"""
import hashlib
import json
import logging
import sys
from pathlib import Path

import pymupdf as fitz
from openpyxl import load_workbook
from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWidgets import QApplication

from src.config import FONTS_DIR, ICONS_DIR
from src.i18n import get_translator
from src.ui.main_window import MainWindow
from src.ui.ocr_dialog import OCRDialog
from src.engine.ocr_engine import OCREngine
from src.version import APP_VERSION

NO_TABLES = "No extractable tables were found in this PDF. Try a document with a clearly structured table or use another extraction method."


def wait_for_job(dialog, target):
    loop = QEventLoop()
    events, ticks = [], []
    def done(value):
        events.append(('completed', value))
        loop.quit()
    def failed(value):
        events.append(('failed', value))
        loop.quit()
    dialog.worker.completed.connect(done)
    dialog.worker.failed.connect(failed)
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: ticks.append(True))
    heartbeat.start(10)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    deadline.start(120000)
    try:
        dialog.start_export(str(target))
        loop.exec()
        if dialog.worker.is_running():
            dialog.worker.cancel()
            dialog.worker.process.waitForFinished(15000)
            raise AssertionError('Child job timeout')
        assert len(events) == 1, events
        assert ticks, 'GUI event loop did not respond during conversion'
        assert dialog.worker._temp is None, 'Job not cleaned'
        return events[0]
    finally:
        deadline.stop()
        heartbeat.stop()
        dialog.worker.completed.disconnect(done)
        dialog.worker.failed.disconnect(failed)


def fixtures(directory):
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 100), 'An ordinary paragraph without tables.')
        doc.save(directory / 'no-tables.pdf')
    with fitz.open() as doc:
        page = doc.new_page(width=420, height=300)
        for x in (40, 200, 380):
            page.draw_line((x, 40), (x, 160))
        for y in (40, 80, 120, 160):
            page.draw_line((40, y), (380, y))
        for r, values in enumerate([('الشركة', 'Amount'), ('شركة المستقبل', '15750'), ('INV-2026', '2026-11-15')]):
            for c, text in enumerate(values):
                OCREngine._insert_word_layer(page, [{'text': text, 'left': 50 + c * 160,
                    'top': 50 + r * 40, 'width': 130, 'height': 18}], 1, 1)
        doc.save(directory / 'table.pdf')
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=250)
        page.insert_text((60, 170), 'HELLO WORLD', fontsize=30)
        page.insert_htmlbox(fitz.Rect(50, 40, 550, 110), '<p>مرحبا بالعالم</p>',
            css="@font-face {font-family:A;src:url('NotoNaskhArabic-Regular.ttf');} body{font-family:A;font-size:30px;}",
            archive=fitz.Archive(str(FONTS_DIR)))
        image = page.get_pixmap(dpi=200).tobytes('png')
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=250)
        page.insert_image(page.rect, stream=image)
        doc.save(directory / 'scan.pdf')


def verify_bands(directory, check):
    """Protection, compression, comments and forms, run inside the packaged app.

    These are the features added after 1.5.0.  Each one is exercised against a
    file written here and then reopened, so what is checked is the saved PDF
    and not the state left in memory.
    """
    from src.models.document import PDFDocument
    from src.engine import annotations as ann
    from src.engine.optimizer import compress_pdf

    plain = directory / 'band-source.pdf'
    with fitz.open() as doc:
        doc.new_page(width=595, height=842).insert_text((60, 100), 'Protected content')
        doc.save(plain)

    # ----------------------------------------------------------- protection
    document = PDFDocument()
    check('protection: plain file opens', document.load(str(plain)))
    secured = directory / 'band-protected.pdf'
    check('protection: saved with AES-256 and permissions',
          document.save(str(secured), incremental=False, user_password='open-me',
                        owner_password='own-me',
                        permissions=int(fitz.PDF_PERM_ACCESSIBILITY)))
    blind = PDFDocument()
    check('protection: refused without the password', not blind.load(str(secured)))
    check('protection: refusal says the file is encrypted', bool(blind.last_error))
    unlocked = PDFDocument()
    check('protection: opens with the password', unlocked.load(str(secured), password='open-me'))
    check('protection: content readable after unlocking',
          'Protected content' in unlocked.get_page(1).get_text())
    kept = directory / 'band-protected-resaved.pdf'
    check('protection: an ordinary save keeps the encryption',
          unlocked.save(str(kept), incremental=False))
    with fitz.open(kept) as doc:
        check('protection: resaved file still needs the password', bool(doc.needs_pass))

    # ------------------------------------------------------------- redaction
    redacted_source = directory / 'band-redact.pdf'
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=200)
        page.insert_text((40, 60), 'Account 123456789')
        page.insert_text((40, 120), 'Keep this line')
        doc.save(redacted_source)
    document = PDFDocument()
    document.load(str(redacted_source))
    applied = document.redact_areas({1: [(35, 45, 260, 70)]})
    check('redaction: the marked area was applied', applied == 1)
    redacted = directory / 'band-redacted.pdf'
    check('redaction: saved', document.save(str(redacted), incremental=False))
    with fitz.open(redacted) as doc:
        text = doc[0].get_text()
        check('redaction: the content is gone, not covered', '123456789' not in text)
        check('redaction: the rest of the page survived', 'Keep this line' in text)

    # ----------------------------------------------------------- compression
    scan = directory / 'scan.pdf'
    smaller = directory / 'band-compressed.pdf'
    report = compress_pdf(str(scan), str(smaller))
    check('compression: ran and reported', bool(report))
    check('compression: the reported sizes are the real ones',
          report['before'] == scan.stat().st_size
          and report['after'] == smaller.stat().st_size)
    check('compression: never writes a bigger file', report['after'] <= report['before'])
    with fitz.open(smaller) as doc:
        check('compression: the result still opens and keeps its page',
              doc.page_count == 1)

    # -------------------------------------------------------------- comments
    document = PDFDocument()
    document.load(str(plain))
    highlight = document.add_comment(1, ann.KIND_HIGHLIGHT,
                                    rects=[(58, 88, 240, 104)], content='looked at')
    note = document.add_comment(1, ann.KIND_NOTE, point=(320, 100),
                                content='ملاحظة عربية')
    shape = document.add_comment(1, ann.KIND_RECTANGLE, rect=(60, 200, 300, 260))
    check('comments: highlight added', bool(highlight))
    check('comments: sticky note added', bool(note))
    check('comments: shape added', bool(shape))
    refused = document.add_comment(1, ann.KIND_FREE_TEXT,
                                   rect=(60, 300, 300, 340), text='مرحبا بالعالم')
    check('comments: Arabic free text refused, with a reason',
          refused is None and bool(document.last_error))
    commented = directory / 'band-commented.pdf'
    check('comments: saved', document.save(str(commented), incremental=False))
    reread = PDFDocument()
    reread.load(str(commented))
    items = reread.page_annotations(1)
    check('comments: all three read back from the saved file',
          sorted(item['kind'] for item in items) == ['highlight', 'note', 'rectangle'])
    check('comments: the Arabic note text is stored as typed',
          any(item['content'] == 'ملاحظة عربية' for item in items))
    removed = reread.delete_comment(1, items[0]['xref'])
    check('comments: one can be deleted', removed and len(reread.page_annotations(1)) == 2)

    # ----------------------------------------------------------------- forms
    document = PDFDocument()
    document.load(str(plain))
    field = document.add_form_field(1, (60, 300, 300, 326), 'full_name', kind='text')
    check('forms: text field created', bool(field))
    check('forms: a duplicate name is refused',
          document.add_form_field(1, (60, 340, 300, 366), 'full_name') is None)
    check('forms: a list without choices is refused',
          document.add_form_field(1, (60, 380, 300, 406), 'city', kind='dropdown') is None)
    result = document.set_field_value('full_name', 'حسام الفاخرة')
    check('forms: the Arabic value is stored', result['stored'])
    check('forms: the broken appearance is declared, not hidden',
          result['appearance_ok'] is False)
    form_path = directory / 'band-form.pdf'
    check('forms: saved', document.save(str(form_path), incremental=False))
    reread = PDFDocument()
    reread.load(str(form_path))
    check('forms: the saved file is a form', reread.has_form())
    check('forms: the value is exact after reopening',
          [item['value'] for item in reread.form_fields()] == ['حسام الفاخرة'])
    flat = reread.flatten_form()
    check('forms: flattened, and the Arabic value was redrawn',
          bool(flat) and flat['flattened'] == 1 and flat['redrawn'] == 1)
    flat_path = directory / 'band-form-flat.pdf'
    check('forms: the flattened file saved', reread.save(str(flat_path), incremental=False))
    with fitz.open(flat_path) as doc:
        text = doc[0].get_text()
        check('forms: the flattened value is real, shaped page text',
              'حسام الفاخرة' in text)
        check('forms: nothing fillable is left', not doc.is_form_pdf)

    # ------------------------------------------------------------ conversion
    from src.engine.conversion import export_pdf

    source_bytes = plain.read_bytes()
    markdown = directory / 'band-export.md'
    export_pdf(source_bytes, str(markdown), [1], 'md')
    check('conversion: Markdown written', markdown.is_file())
    check('conversion: the Markdown carries the page text',
          'Protected content' in markdown.read_text(encoding='utf-8'))
    with fitz.open() as doc:
        doc.new_page(width=200, height=200).insert_text((20, 40), 'one')
        doc.new_page(width=200, height=200).insert_text((20, 40), 'two')
        two_pages = doc.tobytes()
    images = directory / 'band-pages.png'
    export_pdf(two_pages, str(images), [1, 2], 'png', dpi=120)
    produced = sorted(p.name for p in directory.glob('band-pages*.png'))
    check('conversion: one numbered image file per page', len(produced) == 2)


def run(evidence_path):
    directory = Path(evidence_path).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(directory / 'application.log', encoding='utf-8')
    logging.getLogger().addHandler(handler)
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    checks = []
    def check(name, value):
        checks.append({'name': name, 'status': 'PASS' if value else 'FAIL'})
        if not value:
            raise AssertionError(name)
    try:
        fixtures(directory)
        source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.pdf')}
        for language in ('ar', 'en'):
            get_translator().set_language(language)
            window._retranslate_ui()
            check(language + ' open no-table PDF', window._open_file_path(str(directory / 'no-tables.pdf')))
            dialog = OCRDialog(window.current_context, window, conversion_format='xlsx')
            dialog.show()
            app.processEvents()
            target = directory / (language + '-failed.xlsx')
            event = wait_for_job(dialog, target)
            check(language + ' structured no_tables', event == ('failed', 'no_tables'))
            check(language + ' localized message', dialog.status.text() == get_translator().tr(NO_TABLES))
            check(language + ' no traceback in UI', 'Traceback' not in dialog.status.text())
            check(language + ' main window alive', window.isVisible() and window.isEnabled())
            check(language + ' retry enabled', dialog.start_button.isEnabled())
            check(language + ' no XLSX published', not target.exists())
            dialog.grab().save(str(directory / (language + '-failure.png')))
            window.grab().save(str(directory / (language + '-window.png')))
            check(language + ' open table PDF', window._open_file_path(str(directory / 'table.pdf')))
            dialog.context = window.current_context
            target = directory / (language + '-table.xlsx')
            event = wait_for_job(dialog, target)
            check(language + ' success immediately after failure', event == ('completed', str(target)))
            book = load_workbook(target)
            try:
                check(language + ' logical Arabic cells', book.active['A2'].value == 'شركة المستقبل')
                check(language + ' numeric value', book.active['B2'].value == 15750)
                check(language + ' Excel RTL', book.active.sheet_view.rightToLeft is True)
            finally:
                book.close()
            dialog.grab().save(str(directory / (language + '-success.png')))
            dialog.close()
        window._open_file_path(str(directory / 'scan.pdf'))
        dialog = OCRDialog(window.current_context, window, conversion_format='xlsx')
        event = wait_for_job(dialog, directory / 'scan.xlsx')
        check('scanned table controlled refusal', event == ('failed', 'no_tables'))
        dialog.close()
        ocr = OCRDialog(window.current_context, window)
        event = wait_for_job(ocr, directory / 'searchable.pdf')
        check('bundled OCR subprocess', event[0] == 'completed')
        with fitz.open(directory / 'searchable.pdf') as doc:
            text = doc[0].get_text()
            check('OCR English searchable', bool(doc[0].search_for('HELLO WORLD')))
            check('OCR Arabic searchable', bool(doc[0].search_for('مرحبا')))
        ocr.close()
        check('sources unchanged', all(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
                                       for name, digest in source_hashes.items()))
        check('technical traceback logged', 'Traceback' in (directory / 'application.log').read_text(encoding='utf-8'))
        check('application icon loaded', not window.windowIcon().isNull())
        window.windowIcon().pixmap(256, 256).save(str(directory / 'window-icon.png'))
        check('bundled icon resource', (ICONS_DIR / 'NextPDF-Pro.ico').is_file())
        verify_bands(directory, check)
    except Exception:
        logging.exception('Release verification failed')
        checks.append({'name': 'verification exception; see application.log', 'status': 'FAIL'})
    finally:
        for dialog in window.findChildren(OCRDialog):
            if dialog.worker.is_running():
                dialog.worker.cancel()
                dialog.worker.process.waitForFinished(15000)
        window.close()
        logging.getLogger().removeHandler(handler)
        handler.close()
        report = {'version': APP_VERSION, 'frozen': bool(getattr(sys, 'frozen', False)),
                  'executable': sys.executable, 'checks': checks,
                  'original_customer_pdf': 'Not provided', 'clean_machine': False}
        (directory / 'report.json').write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding='utf-8')
    return 1 if any(item['status'] == 'FAIL' for item in checks) else 0
