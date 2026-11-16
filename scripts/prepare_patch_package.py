"""Stage release documentation and installed dependency license texts.

The target folder follows ``src.version`` so a release is never staged into a
previous version's folder; pass an explicit path to override it.
"""
import hashlib
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.version import APP_VERSION

RELEASE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / f'dist/release-{APP_VERSION}'
RELEASE.mkdir(parents=True, exist_ok=True)
for source, name in [('LICENSE', 'LICENSE.txt'), ('LICENSES.txt', 'LICENSES.txt'),
                     ('THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md'),
                     ('README.md', 'README.txt'), ('VERSION.txt', 'VERSION.txt')]:
    shutil.copy2(ROOT / source, RELEASE / name)
licenses = RELEASE / 'licenses'
licenses.mkdir(exist_ok=True)
inventory = []
for dist in importlib.metadata.distributions():
    name = dist.metadata['Name']
    copied = []
    for entry in dist.files or []:
        if any(word in str(entry).lower() for word in ('license', 'copying', 'copyright', 'notice')):
            source = Path(dist.locate_file(entry))
            if source.is_file() and source.suffix.lower() in {'', '.txt', '.md', '.rst', '.html'}:
                relative = Path(str(entry).replace('..', '_'))
                target = licenses / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied.append(str(target.relative_to(licenses)))
    if copied:
        inventory.append({'package': name, 'version': dist.version, 'license_files': copied})
for source in (ROOT / 'resources/fonts').glob('*.txt'):
    shutil.copy2(source, licenses / source.name)
(licenses / 'inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
sums = []
for name in ('NextPDF-Pro.exe', f'NextPDF-Pro-Setup-{APP_VERSION}.exe'):
    binary = RELEASE / name
    if binary.exists():
        sums.append(hashlib.sha256(binary.read_bytes()).hexdigest() + '  ' + name)
(RELEASE / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='utf-8')
print('Staged', len(inventory), 'installed-package license inventories into', RELEASE)
print('Hashed:', ', '.join(line.split('  ')[1] for line in sums) or 'nothing')
