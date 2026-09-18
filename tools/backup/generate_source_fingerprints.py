#!/usr/bin/env python3
"""Fingerprint local original/source evidence that is intentionally excluded from Git."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "backup" / "source_fingerprints.json"
TARGETS = [
    ROOT / "data" / "MAPS.DAT",
    ROOT / "data" / "ROOMS.DAT",
    ROOT / "data" / "audio" / "original_audio",
    ROOT / "assets" / "audio",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

entries = []
for target in TARGETS:
    if target.is_file():
        candidates = [target]
    elif target.is_dir():
        candidates = sorted(p for p in target.rglob("*") if p.is_file())
    else:
        continue
    for path in candidates:
        entries.append({
            "path": str(path.relative_to(ROOT)).replace(os.sep, "/"),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "schema": "openazrael.source_fingerprints",
    "schema_version": 1,
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "purpose": "Identify local source/original evidence excluded from Git; does not imply redistribution permission.",
    "entries": entries,
}, indent=2), encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}: {len(entries)} entries")
