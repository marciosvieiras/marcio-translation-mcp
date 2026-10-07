from __future__ import annotations
import tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PARTS=sorted((ROOT/'bundle').glob('payload.tar.xz.part*'))
if not PARTS:
    raise SystemExit('No MCP bundle parts found')
bundle=ROOT/'payload.tar.xz'
with bundle.open('wb') as out:
    for p in PARTS:
        out.write(p.read_bytes())
with tarfile.open(bundle,'r:xz') as tf:
    tf.extractall(ROOT)
print(f'Extracted {len(PARTS)} bundle parts')
