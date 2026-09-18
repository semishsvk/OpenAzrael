#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, sys, zipfile


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    args = ap.parse_args()
    archive = args.archive.expanduser().resolve()
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    manifest = archive.with_suffix(archive.suffix + ".json")
    if not archive.exists() or not checksum.exists() or not manifest.exists():
        print("OpenAzrael snapshot verification: FAIL - archive/checksum/manifest set incomplete")
        return 1
    expected = checksum.read_text(encoding="utf-8").split()[0]
    actual = sha256_file(archive)
    if expected != actual:
        print("OpenAzrael snapshot verification: FAIL - SHA-256 mismatch")
        return 1
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            bad = zf.testzip()
            if bad:
                print(f"OpenAzrael snapshot verification: FAIL - corrupt member {bad}")
                return 1
            zip_count = len([i for i in zf.infolist() if not i.is_dir()])
        meta = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"OpenAzrael snapshot verification: FAIL - {exc}")
        return 1
    if meta.get("sha256") != actual or meta.get("file_count") != zip_count:
        print("OpenAzrael snapshot verification: FAIL - manifest mismatch")
        return 1
    print("OpenAzrael snapshot verification: PASS")
    print(" archive:", archive.name)
    print(" sha256: ", actual)
    print(" files:  ", zip_count)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
