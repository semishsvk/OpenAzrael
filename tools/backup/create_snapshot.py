#!/usr/bin/env python3
"""Create an integrity-checked full OpenAzrael snapshot.

The snapshot is intentionally broader than Git and includes repository-excluded
source evidence. Transient caches, Git internals and prior backup trees are skipped.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, zipfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEST = ROOT.parent / "OpenAzrael_Backups"
SKIP_DIRS = {".git", ".godot", ".import", "__pycache__", ".cache", ".tmp", "OpenAzrael_Backups", "backups", "snapshots"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".tmp"}


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["daily", "weekly", "monthly", "release"], default="daily")
    ap.add_argument("--label", default="")
    ap.add_argument("--destination", type=Path, default=DEFAULT_DEST)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(c for c in args.label if c.isalnum() or c in "-_.")
    suffix = f"_{safe_label}" if safe_label else ""
    out_dir = args.destination.expanduser().resolve() / args.tier
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"OpenAzrael_{args.tier}_{stamp}{suffix}.zip"

    included = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or should_skip(path):
                continue
            rel = path.relative_to(ROOT)
            zf.write(path, Path(ROOT.name) / rel)
            included.append({"path": str(rel).replace(os.sep, "/"), "size": path.stat().st_size})

    digest = sha256_file(archive)
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    manifest = archive.with_suffix(archive.suffix + ".json")
    manifest.write_text(json.dumps({
        "schema": "openazrael.backup_snapshot",
        "schema_version": 1,
        "created_utc": now.isoformat(),
        "tier": args.tier,
        "label": args.label,
        "project_root": ROOT.name,
        "archive": archive.name,
        "sha256": digest,
        "file_count": len(included),
        "archive_size": archive.stat().st_size,
        "files": included,
    }, indent=2), encoding="utf-8")

    print(f"snapshot: {archive}")
    print(f"sha256:   {digest}")
    print(f"files:    {len(included)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
