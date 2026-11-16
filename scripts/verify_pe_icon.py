"""Compare embedded PE icon images directly; bypass Windows shell icon caches."""
import hashlib
import json
import struct
import sys
from pathlib import Path
import pefile

exe, ico, report = map(Path, sys.argv[1:])
data = ico.read_bytes()
count = struct.unpack_from('<H', data, 4)[0]
expected = []
for i in range(count):
    width, height, _, _, _, _, length, offset = struct.unpack_from('<BBBBHHII', data, 6 + 16 * i)
    expected.append({'width': width or 256, 'height': height or 256,
                     'sha256': hashlib.sha256(data[offset:offset + length]).hexdigest()})
pe = pefile.PE(str(exe))
embedded = []
for resource in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if resource.id == 3:
        for image in resource.directory.entries:
            for lang in image.directory.entries:
                item = lang.data.struct
                blob = pe.get_data(item.OffsetToData, item.Size)
                embedded.append(hashlib.sha256(blob).hexdigest())
result = {'exe': str(exe), 'reference': str(ico), 'frames': expected,
          'all_frames_embedded_exactly': all(frame['sha256'] in embedded for frame in expected)}
report.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
sys.exit(0 if result['all_frames_embedded_exactly'] else 1)
