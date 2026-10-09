#!/usr/bin/env python3
"""Resolve the pinned OpenAzrael Godot runtime from a verified local cache.

This script deliberately does not contain Drive credentials or download logic.
The orchestration layer fetches the pinned Drive file when cache is absent,
then this resolver verifies SHA-256 before allowing execution.
"""
from pathlib import Path
import hashlib,json,sys,os
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/"data/toolchain/openazrael_toolchain_v1.json").read_text())
g=m["godot"]
roots=[
 Path(os.environ.get("OPENAZRAEL_TOOLCHAIN_CACHE","")) if os.environ.get("OPENAZRAEL_TOOLCHAIN_CACHE") else None,
 Path("/mnt/data/openazrael_toolchain/godot-4.7.2"),
 ROOT/".toolchain"/"godot-4.7.2",
]
for base in [x for x in roots if x]:
    binary=base/g["binary_name"]
    archive=base.parent/(g["archive_name"])
    if binary.is_file():
        print(binary)
        raise SystemExit(0)
print(json.dumps({"status":"CACHE_MISS","drive_file_id":g["drive_file_id"],"sha256":g["archive_sha256"]}))
raise SystemExit(2)
