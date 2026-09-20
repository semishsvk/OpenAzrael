#!/usr/bin/env python3
"""Validate an AL-POC-01 manifest and optionally prove source files are unchanged."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.audio_lab.common import iter_audio_files, tree_digest
else:
    from .common import iter_audio_files, tree_digest

def validate(manifest: dict, source_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "openazrael.audio_lab.inventory":
        errors.append("unexpected manifest schema")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return errors + ["assets must be a list"]
    if manifest.get("source_file_count") != len(assets):
        errors.append("source_file_count does not equal inventory length")

    paths = [str(a.get("path", "")) for a in assets]
    if paths != sorted(paths, key=str.casefold):
        errors.append("assets are not deterministically path-sorted")
    if len(paths) != len(set(paths)):
        errors.append("duplicate paths in inventory")

    for asset in assets:
        if not asset.get("sha256") or len(str(asset["sha256"])) != 64:
            errors.append("invalid SHA-256 for " + str(asset.get("path")))
        for item in asset.get("issues", []):
            if item.get("severity") == "error":
                errors.append(f"{asset.get('path')}: {item.get('code')}")

    qa = manifest.get("qa", {})
    if qa.get("missing_expected_assets"):
        errors.append("missing expected fingerprint assets: " + ", ".join(qa["missing_expected_assets"]))
    if qa.get("status") == "FAIL" and not any("AUD" in e or "missing expected" in e for e in errors):
        errors.append("QA summary is FAIL")

    if source_root is not None:
        source_root = source_root.resolve()
        files = iter_audio_files(source_root, manifest.get("extensions", []))
        current_digest = tree_digest(source_root, files)
        if current_digest != manifest.get("source_tree_sha256"):
            errors.append("source tree digest changed since scan")
        if len(files) != manifest.get("source_file_count"):
            errors.append("source audio file count changed since scan")
    return errors

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--source-root", type=Path)
    args = ap.parse_args(argv)
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate(data, args.source_root)
    if errors:
        print("OpenAzrael Audio Lab AL-POC-01 validation: FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("OpenAzrael Audio Lab AL-POC-01 validation: PASS")
    print(" assets:", len(data.get("assets", [])))
    print(" source tree:", data.get("source_tree_sha256"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
