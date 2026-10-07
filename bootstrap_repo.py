from __future__ import annotations
import base64
from pathlib import Path
ROOT=Path(__file__).resolve().parent
B64_DIR=ROOT/"data_bundle_b64"
OUT_DIR=ROOT/"data_bundle"
OUT_DIR.mkdir(parents=True,exist_ok=True)
for p in sorted(B64_DIR.glob("sources.tar.xz.part*.b64")):
    out=OUT_DIR/p.name[:-4]
    out.write_bytes(base64.b64decode(p.read_text(encoding="ascii").strip()))
print(f"Decoded {len(list(B64_DIR.glob('sources.tar.xz.part*.b64')))} data shards")
