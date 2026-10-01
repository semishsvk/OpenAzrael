#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def cstring(data:bytes,start:int,limit:int=64):
    end=data.find(b"\0",start,min(len(data),start+limit))
    if end<0:return None
    raw=data[start:end]
    if not raw or any(c<32 or c>=127 for c in raw):return None
    return raw.decode("ascii")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--puzzles",type=Path,required=True)
    ap.add_argument("--world",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    p=a.puzzles.read_bytes(); w=a.world.read_bytes()
    actions=[]
    for i in range(len(p)-4):
        if p[i:i+2]!=b"\x10\x00": continue
        op=p[i+2]; tok=cstring(p,i+3)
        if tok and tok.lower() in ("r7p1","spaper"):
            actions.append({"offset":i,"offset_hex":hex(i),"opcode":op,"opcode_hex":hex(op),"token":tok})
    out={"schema":"openazrael.r7p1_action_slice","version":166,
         "inputs":{"puzzles_sha256":hashlib.sha256(p).hexdigest(),"world_sha256":hashlib.sha256(w).hexdigest()},
         "actions":actions,
         "expected":{"0x28":["spaper"],"0x08":["R7P1"],"0x07":["R7P1"],"0x21":["R7P1"]},
         "boundary":"Opcode identity/token extraction only. 0x21 semantics require executable consumer evidence."}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()
