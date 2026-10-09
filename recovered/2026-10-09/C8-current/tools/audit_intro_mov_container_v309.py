#!/usr/bin/env python3
"""Forensic, fail-closed structural analysis of Azrael proprietary MOV files.
Never treats a valid container header as decoded video or verified audio.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

NAMES = ("MINDLOGO.MOV", "INTRO.MOV", "MOV/INTRO.MOV", "MOV/DEMO.MOV")
MAGIC = bytes.fromhex("90ef12ab")

def parse(data, name):
    if len(data) < 80 or data[:4] != MAGIC:
        raise ValueError(f"{name}: bad magic/truncated header")
    count, depth, width, height = struct.unpack_from("<4H", data, 4)
    if not (1 <= count <= 10000 and depth in (8, 12, 15, 16, 24, 32)
            and 1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError(f"{name}: implausible header")
    words = [{"offset": hex(i), "value": struct.unpack_from("<I", data, i)[0]}
             for i in range(12, 64, 4)]
    candidates = [{"header_offset": hex(i), "value": v["value"]}
                  for i, v in zip(range(12, 64, 4), words)
                  if 80 <= v["value"] < len(data)]
    return {
        "file": name, "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data), "magic": data[:4].hex(),
        "candidate_frame_count": count, "candidate_depth": depth,
        "candidate_width": width, "candidate_height": height,
        "header_u32": words, "in_file_offset_candidates": candidates,
        "decoded_frames": 0, "audio_verified": False,
        "codec": "UNKNOWN", "fidelity": "HOLD"
    }

def inventory(root):
    return [parse((root / n).read_bytes(), n) for n in NAMES]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    items = inventory(a.corpus)
    result = {"schema": "openazrael.intro_mov_container.v309",
              "status": "STRUCTURAL_PASS_FIDELITY_HOLD",
              "source_read_only": True, "files": items,
              "gates": {"all_four_headers": True, "frame_boundaries": False,
                        "frame_decode": False, "audio": False,
                        "original_runtime_comparison": False,
                        "godot_playback": False},
              "note": "Header words and offset candidates are hypotheses, not codec semantics."}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "files": len(items),
                      "candidates": [len(i["in_file_offset_candidates"]) for i in items]}))

if __name__ == "__main__":
    main()