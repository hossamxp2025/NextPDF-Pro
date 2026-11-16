import json
import tempfile
from pathlib import Path

import pytest
from PySide6.QtCore import QProcess, QEventLoop, QTimer

from src.workers.ocr_process import ConversionProcess
from src.i18n import get_translator
from src.ui.ocr_dialog import OCRDialog
from src.release_verification import NO_TABLES


@pytest.mark.parametrize('module', ['conversion_job', 'ocr_job', 'creation_job'])
def test_imported_entry_contains_unexpected_failure(tmp_path, module, caplog):
    import importlib
    run = importlib.import_module('src.' + module).run
    request = tmp_path / 'request.json'
    request.write_text('{broken')
    assert run(str(request)) == 1
    assert json.loads((tmp_path / 'result.json').read_text())['ok'] is False
    assert 'Traceback' in caplog.text


@pytest.mark.parametrize('payload', [None, '{broken', '[]', '{"ok": "yes"}', '{"ok": true}'])
def test_invalid_result_never_publishes_or_escapes(tmp_path, payload, caplog):
    worker = ConversionProcess()
    worker._target = str(tmp_path / 'target.xlsx')
    worker._format = 'xlsx'
    worker._temp = tempfile.TemporaryDirectory(dir=tmp_path)
    worker._directory = Path(worker._temp.name)
    if payload is not None:
        (worker._directory / 'result.json').write_text(payload)
    (worker._directory / 'output.xlsx').write_bytes(b'not a workbook')
    errors = []
    worker.failed.connect(errors.append)
    worker._finished(0, QProcess.NormalExit)
    assert errors and worker._temp is None
    assert not Path(worker._target).exists()
    assert 'Traceback' in caplog.text


def test_unexpected_exit_rejected(tmp_path):
    worker = ConversionProcess()
    worker._target = str(tmp_path / 'target.xlsx')
    worker._format = 'xlsx'
    worker._temp = tempfile.TemporaryDirectory(dir=tmp_path)
    worker._directory = Path(worker._temp.name)
    (worker._directory / 'result.json').write_text('{"ok": true}')
    errors = []
    worker.failed.connect(errors.append)
    worker._finished(-1, QProcess.CrashExit)
    assert errors and worker._temp is None
    assert not Path(worker._target).exists()


def test_failed_start_is_reported(tmp_path, monkeypatch):
    import sys
    worker = ConversionProcess()
    loop = QEventLoop()
    errors = []
    worker.failed.connect(lambda message: (errors.append(message), loop.quit()))
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'missing.exe'))
    worker.start(b'invalid', str(tmp_path / 'out.xlsx'), 'eng', [1], 'xlsx')
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(5000)
    loop.exec()
    timer.stop()
    assert errors and worker._temp is None


@pytest.mark.parametrize('language', ['ar', 'en'])
def test_error_message_exactly_localized(language):
    translator = get_translator()
    old = translator.language
    try:
        translator.set_language(language)
        dialog = OCRDialog(None, conversion_format='xlsx')
        dialog._failed('no_tables')
        expected = NO_TABLES if language == 'en' else 'لم يتم العثور على جداول قابلة للاستخراج من ملف PDF. يمكنك تجربة ملف يحتوي على جداول واضحة أو استخدام طريقة استخراج مختلفة.'
        assert dialog.status.text() == expected
        dialog._failed('Traceback: secret internal error')
        assert 'Traceback' not in dialog.status.text()
        dialog.close()
    finally:
        translator.set_language(old)
