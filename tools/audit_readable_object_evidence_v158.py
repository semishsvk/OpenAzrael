#!/usr/bin/env python3
"""Audit readable/inspect object evidence without inferring missing presentation payloads."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

TARGETS = ("r1p1", "paper", "parchment")
PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")

def strings(data: bytes):
    return [(m.start(), m.group().decode("latin1")) for m in PRINTABLE.finditer(data)]

def windows(rows, targets, radius=5):
    out=[]
    for i,(off,s) in enumerate(rows):
        low=s.lower()
        if any(t in low for t in targets):
            lo=max(0,i-radius); hi=min(len(rows),i+radius+1)
            out.append({"match_offset":off,"match":s,"neighbors":[{"offset":o,"text":x} for o,x in rows[lo:hi]]})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rooms", required=True)
    ap.add_argument("--world")
    ap.add_argument("--puzzles")
    ap.add_argument("--out", required=True)
    a=ap.parse_args()
    result={"schema":"openazrael.readable_object_evidence","version":158,"targets":list(TARGETS),"files":{},"conclusion":"HOLD unless a source payload/reference is independently bound"}
    for label,path in (("ROOMS",a.rooms),("WORLD",a.world),("PUZZLES",a.puzzles)):
        if not path: continue
        data=Path(path).read_bytes(); rows=strings(data)
        result["files"][label]={"path":str(path),"sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"matches":windows(rows,TARGETS)}
    Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"out":a.out,"match_counts":{k:len(v["matches"]) for k,v in result["files"].items()}},indent=2))

if __name__=="__main__":
    main()
