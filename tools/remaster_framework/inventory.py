from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".godot",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

MANIFEST_VERSION = 1


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(
    root: Path,
    excluded_dirs: Iterable[str] = DEFAULT_EXCLUDED_DIRS,
    excluded_paths: Iterable[Path] = (),
) -> list[Path]:
    root = root.resolve()
    excluded = set(excluded_dirs)
    excluded_abs = {path.resolve() for path in excluded_paths}
    files: list[Path] = []

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts):
            continue
        if path.is_symlink():
            continue
        if path.resolve() in excluded_abs:
            continue
        if path.is_file():
            files.append(path)

    return sorted(files, key=lambda p: p.relative_to(root).as_posix().casefold())


def build_inventory(
    root: Path,
    excluded_paths: Iterable[Path] = (),
) -> dict:
    root = root.resolve()
    records = []
    total_size = 0

    for path in iter_files(root, excluded_paths=excluded_paths):
        stat = path.stat()
        size = stat.st_size
        total_size += size
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": size,
                "sha256": sha256_file(path),
            }
        )

    corpus_digest = hashlib.sha256()
    for record in records:
        corpus_digest.update(record["path"].encode("utf-8"))
        corpus_digest.update(b"\0")
        corpus_digest.update(record["sha256"].encode("ascii"))
        corpus_digest.update(b"\n")

    return {
        "manifest_version": MANIFEST_VERSION,
        "file_count": len(records),
        "total_size": total_size,
        "corpus_sha256": corpus_digest.hexdigest(),
        "files": records,
    }


def write_inventory(root: Path, output: Path) -> dict:
    root = root.resolve()
    output = output.resolve()
    payload = build_inventory(root, excluded_paths=(output,))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a deterministic, source-safe SHA-256 inventory."
    )
    parser.add_argument("root", type=Path, help="Directory to inventory")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSON manifest destination",
    )
    args = parser.parse_args()

    payload = write_inventory(args.root, args.output)
    print(
        f"inventory: {payload['file_count']} files, "
        f"{payload['total_size']} bytes, "
        f"corpus={payload['corpus_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
