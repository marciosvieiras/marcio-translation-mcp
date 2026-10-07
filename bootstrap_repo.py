from __future__ import annotations
import base64
import hashlib
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTS = sorted((ROOT / "bundle").glob("part_*.b64"))
if not PARTS:
    raise SystemExit("No MCP bundle parts found")

encoded = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
payload = base64.b64decode(encoded, validate=True)

expected_size = 2404020
expected_sha256 = "6f02186b574cf9091dc7885d0ea8b173bd8422093d454928d7563741c3a07c99"
if len(payload) != expected_size:
    raise SystemExit(f"Bundle size mismatch: {len(payload)} != {expected_size}")
actual = hashlib.sha256(payload).hexdigest()
if actual != expected_sha256:
    raise SystemExit(f"Bundle SHA-256 mismatch: {actual} != {expected_sha256}")

archive = ROOT / "payload.tar.xz"
archive.write_bytes(payload)
with tarfile.open(archive, "r:xz") as tf:
    tf.extractall(ROOT)

print(f"Reconstructed and extracted {len(PARTS)} bundle parts; sha256={actual}")
