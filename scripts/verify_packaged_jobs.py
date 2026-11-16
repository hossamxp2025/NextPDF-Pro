"""Exercise frozen job dispatch, including unexpected parser failures."""
import json
import subprocess
import sys
from pathlib import Path

exe = Path(sys.argv[1]).resolve()
directory = Path(sys.argv[2]).resolve()
directory.mkdir(parents=True, exist_ok=True)
checks = []
for flag in ('--conversion-job', '--ocr-job', '--create-job'):
    work = directory / flag[2:]
    work.mkdir(exist_ok=True)
    request = work / 'request.json'
    request.write_text('{broken')
    process = subprocess.run([str(exe), flag, str(request)], cwd=directory, timeout=120)
    result = json.loads((work / 'result.json').read_text())
    ok = process.returncode == 1 and result['ok'] is False and 'Traceback' in (work / 'traceback.txt').read_text()
    checks.append({'name': flag + ' malformed request', 'status': 'PASS' if ok else 'FAIL'})
work = directory / 'create-success'
work.mkdir(exist_ok=True)
text = work / 'text.txt'
text.write_text('PACKAGED CREATE PDF VERIFIED', encoding='utf-8')
request = work / 'request.json'
request.write_text(json.dumps({'sources': [str(text)]}))
process = subprocess.run([str(exe), '--create-job', str(request)], cwd=directory, timeout=120)
result = json.loads((work / 'result.json').read_text())
ok = process.returncode == 0 and result['ok'] and (work / 'output.pdf').read_bytes().startswith(b'%PDF-')
checks.append({'name': 'packaged create PDF', 'status': 'PASS' if ok else 'FAIL'})
(directory / 'report.json').write_text(json.dumps(checks, indent=2))
print(json.dumps(checks, indent=2))
sys.exit(0 if all(item['status'] == 'PASS' for item in checks) else 1)
