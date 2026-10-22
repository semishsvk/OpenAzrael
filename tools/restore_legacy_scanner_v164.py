#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import wave
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/ui/legacy_scanner_manifest_v164.json"
OUT = ROOT / "assets/ui/legacy_menu"
RECEIPT = ROOT / ".tmp/menu_lab/legacy_scanner_restore_v164.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(root: Path, name: str, spec: dict) -> Path:
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != int(spec["bytes"]):
        raise ValueError(f"{name}: byte-size mismatch")
    if sha256(path) != str(spec["sha256"]):
        raise ValueError(f"{name}: SHA-256 mismatch")
    return path


def hud_message(blob: bytes, index: int, fmt: dict) -> str:
    table_offset = int(fmt["table_offset"])
    entry_size = int(fmt["entry_size"])
    record = table_offset + index * entry_size
    if record + 6 > len(blob):
        raise ValueError(f"HUDMES index {index}: table record out of range")
    payload_offset = struct.unpack_from("<I", blob, record)[0]
    payload_length = struct.unpack_from("<H", blob, record + 4)[0]
    if payload_offset + payload_length > len(blob):
        raise ValueError(f"HUDMES index {index}: payload out of range")
    return blob[payload_offset : payload_offset + payload_length].rstrip(b"\x00").decode("cp437").rstrip()


def wav_metadata(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        return {
            "channels": wav.getnchannels(),
            "sample_width": wav.getsampwidth(),
            "sample_rate": wav.getframerate(),
            "frames": wav.getnframes(),
            "duration_seconds": wav.getnframes() / float(wav.getframerate()),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore source-exact ATDEMO upper-right scanner/readout assets.")
    parser.add_argument("demo_dir", type=Path)
    args = parser.parse_args()
    source = args.demo_dir.resolve()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    verified: dict[str, Path] = {}
    for name, spec in manifest["files"].items():
        verified[name] = verify_file(source, name, spec)

    hud_blob = verified["HUDMES.DAT"].read_bytes()
    fmt = manifest["hudmes_format"]
    boot_ids = [int(value) for value in manifest["boot_message_ids"]]
    boot = [{"id": idx, "text": hud_message(hud_blob, idx, fmt)} for idx in boot_ids]

    rooms = {}
    for room_id, binding in manifest["demo_room_message_binding"].items():
        idx = int(binding["hud_message_id"])
        rooms[room_id] = {
            "hud_message_id": idx,
            "text": hud_message(hud_blob, idx, fmt),
            "provenance": binding["provenance"],
        }

    exe_bytes = verified["R.EXE"].read_bytes()
    scan_status = str(manifest["scan_status"])
    if scan_status.encode("ascii") not in exe_bytes:
        raise ValueError("R.EXE: scanner status string not found")

    OUT.mkdir(parents=True, exist_ok=True)
    for source_name, runtime_name in (("HUD3.WAV", "HUD3.wav"), ("SCAN.WAV", "SCAN.wav")):
        shutil.copyfile(verified[source_name], OUT / runtime_name)

    font_source = verified["RUSGLD2.PCX"]
    with Image.open(font_source) as indexed:
        indexed.load()
        if indexed.mode != "P":
            raise ValueError("RUSGLD2.PCX: expected indexed PCX")
        expected = manifest["files"]["RUSGLD2.PCX"]
        if indexed.size != (int(expected["width"]), int(expected["height"])):
            raise ValueError("RUSGLD2.PCX: dimensions mismatch")
        rgba = indexed.convert("RGBA")
        indices = list(indexed.getdata())
        alpha = Image.new("L", indexed.size, 255)
        alpha.putdata([0 if int(value) == 0 else 255 for value in indices])
        rgba.putalpha(alpha)
        rgba.save(OUT / "RUSGLD2.png", format="PNG", optimize=False)

    hud_meta = wav_metadata(verified["HUD3.WAV"])
    scan_meta = wav_metadata(verified["SCAN.WAV"])
    for source_name, actual in (("HUD3.WAV", hud_meta), ("SCAN.WAV", scan_meta)):
        expected = manifest["files"][source_name]
        if actual["sample_rate"] != int(expected["sample_rate"]) or actual["frames"] != int(expected["frames"]):
            raise ValueError(f"{source_name}: WAV metadata mismatch")

    runtime = {
        "schema": "openazrael.legacy_scanner.runtime_source",
        "version": 164,
        "status": "PASS",
        "scan_status": scan_status,
        "boot": boot,
        "rooms": rooms,
        "audio": {
            "hud_boot": {"path": "res://assets/ui/legacy_menu/HUD3.wav", **hud_meta},
            "scan": {"path": "res://assets/ui/legacy_menu/SCAN.wav", **scan_meta},
        },
        "presentation": manifest["presentation"],
        "source_sha256": {name: spec["sha256"] for name, spec in manifest["files"].items()},
    }
    runtime_path = OUT / "legacy_scanner_v164.json"
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "openazrael.legacy_scanner.restore",
        "version": 164,
        "status": "PASS",
        "boot_message_count": len(boot),
        "room_bindings": {key: value["hud_message_id"] for key, value in rooms.items()},
        "runtime_json_sha256": sha256(runtime_path),
        "font_png_sha256": sha256(OUT / "RUSGLD2.png"),
        "hud3_wav_sha256": sha256(OUT / "HUD3.wav"),
        "scan_wav_sha256": sha256(OUT / "SCAN.wav"),
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
