#!/usr/bin/env python3
"""Evidence-oriented demo-vs-retail ROOMS.DAT comparison.

This tool intentionally reports only verified byte-level patch facts. It does not
claim that all of ROOMS.DAT is a 60-byte-record file; the fixed stride is proven
only for the late object/override table around the demo room definitions.
"""
from pathlib import Path
import hashlib, json

PATCHES = [
    ("insert", "R1Entry", 0x150C4, None),
    ("insert", "TongR6", 0x152A6, None),
    ("insert", "R1DemoTapPiece1", 0x152E2, None),
    ("insert", "WellRoomdoor", 0x15888, None),
    ("delete", "R8FromR6", None, 0x15B9A),
]

def main(demo: Path, retail: Path, out: Path):
    d, r = demo.read_bytes(), retail.read_bytes()
    records = []
    for kind, name, doff, roff in PATCHES:
        blob = d[doff:doff+60] if doff is not None else r[roff:roff+60]
        if len(blob) != 60:
            raise SystemExit(f"short patch record: {name}")
        records.append({
            "kind": kind, "name": name, "size": 60,
            "demo_offset": doff, "retail_offset": roff,
            "sha256": hashlib.sha256(blob).hexdigest(),
        })
    payload = {
        "demo_size": len(d), "retail_size": len(r), "delta": len(d)-len(r),
        "fixed_stride_region_patch": records,
        "net_records": sum(1 if x[0]=="insert" else -1 for x in PATCHES),
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("demo", type=Path)
    ap.add_argument("retail", type=Path)
    ap.add_argument("out", type=Path)
    a=ap.parse_args(); main(a.demo,a.retail,a.out)
