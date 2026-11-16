import json
import logging

import pymupdf as fitz

from src.conversion_job import run


def test_imported_job_contains_exception_and_writes_result(tmp_path, caplog):
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 100), 'Ordinary paragraph, no table')
        doc.save(tmp_path / 'input.pdf')
    request = tmp_path / 'request.json'
    request.write_text(json.dumps({'format': 'xlsx', 'pages': [1]}))
    with caplog.at_level(logging.ERROR):
        assert run(str(request)) == 1
    result = json.loads((tmp_path / 'result.json').read_text())
    assert result == {'ok': False, 'error_code': 'no_tables'}
    assert 'Traceback' in (tmp_path / 'traceback.txt').read_text()
    assert not (tmp_path / 'output.xlsx').exists()
