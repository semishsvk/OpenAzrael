"""Pad verified odd-length demo WAV containers; preserve exact PCM bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ORIGINAL_SHA256 = "b307df0a07c48da7968b949e776f3143ba8a4c8a9fe0d9289b34432c5f1456e9"
S137_SHA256 = "dc4526516cfa13540522abaa8258ac834d0abc3ee3e5a72e27445249d88644c6"

def prepare(source: Path, destination: Path) -> dict:
    original = source.read_bytes()
    source_hash = hashlib.sha256(original).hexdigest()
    if source_hash not in (ORIGINAL_SHA256, S137_SHA256):
        raise ValueError("Source must be fingerprint-verified original 797TAP.WAV or S137.WAV")
    assert original[:4] == b"RIFF" and original[8:12] == b"WAVE"
    assert original[36:40] == b"data"
    pcm_size = struct.unpack_from("<I", original, 40)[0]
    assert 44 + pcm_size <= len(original)
    # S137 lacks the RIFF word-alignment byte after its odd-sized data chunk.
    # 797TAP already has padding and is left byte-for-byte unchanged.
    prepared = original + (b"\0" if len(original) % 2 else b"")
    prepared = prepared[:4] + struct.pack("<I", len(prepared)-8) + prepared[8:]
    assert prepared[12:len(original)] == original[12:]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(prepared)
    return {"source_sha256": source_hash,
            "prepared_sha256": hashlib.sha256(prepared).hexdigest(),
            "pcm_sha256": hashlib.sha256(original[44:44+pcm_size]).hexdigest(),
            "pcm_bytes": pcm_size, "pcm_unchanged": True,
            "operation": "ensure terminal RIFF alignment padding; no sample changes"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), indent=2))
