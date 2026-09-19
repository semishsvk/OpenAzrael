"""Repair the verified 797TAP RIFF container for Godot; preserve exact PCM bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ORIGINAL_SHA256 = "b307df0a07c48da7968b949e776f3143ba8a4c8a9fe0d9289b34432c5f1456e9"

def prepare(source: Path, destination: Path) -> dict:
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Source must be the fingerprint-verified original 797TAP.WAV")
    assert original[:4] == b"RIFF" and original[8:12] == b"WAVE"
    assert original[36:40] == b"data" and struct.unpack_from("<I", original, 40)[0] == 5079
    # A terminal empty JUNK chunk avoids Godot 4.7.2's seek-past-end diagnostic
    # on this odd-length final data chunk. No sample or format byte changes.
    prepared = original[:4] + struct.pack("<I", len(original)) + original[8:] + b"JUNK\0\0\0\0"
    assert prepared[12:len(original)] == original[12:]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(prepared)
    return {"source_sha256": ORIGINAL_SHA256,
            "prepared_sha256": hashlib.sha256(prepared).hexdigest(),
            "pcm_sha256": hashlib.sha256(original[44:5123]).hexdigest(),
            "pcm_bytes": 5079, "pcm_unchanged": True,
            "operation": "append empty RIFF JUNK chunk and update RIFF length"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), indent=2))
