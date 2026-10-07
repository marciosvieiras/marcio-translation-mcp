from __future__ import annotations
import subprocess, sys, tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'knowledge.sqlite3'
SOURCES = ROOT / 'data' / 'sources'
BUNDLE_DIR = ROOT / 'data_bundle'
BUNDLE = BUNDLE_DIR / 'sources.tar.xz'
if not SOURCES.exists():
    parts = sorted(BUNDLE_DIR.glob('sources.tar.xz.part*'))
    if not parts:
        raise SystemExit('Missing data source bundle parts')
    with BUNDLE.open('wb') as out:
        for part in parts:
            out.write(part.read_bytes())
    with tarfile.open(BUNDLE, 'r:xz') as tf:
        tf.extractall(ROOT)
if not SOURCES.exists():
    raise SystemExit('data/sources was not extracted')
DB.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(ROOT/'scripts'/'rebuild_database.py')], check=True)
print(f'Bootstrap complete: {DB} ({DB.stat().st_size} bytes)')
