#!/usr/bin/env python3
"""Correlate readable-object tokens with nearby action records and LOOK-family strings.

This is a conservative evidence producer. Proximity is not semantic identity.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

TOKENS=("r1p1","paper","parchment")
LOOK=("LOOK","LOOK1","LOOK2","LOOK3","PHOTO","BLOOK")
PRINT=re.compile(rb"[\x20-\x7e]{3,}")

def hits(data, needles):
    rows=[]
    for m in PRINT.finditer(data):
        s=m.group().decode("latin1")
        if any(n.lower() in s.lower() for n in needles):
            rows.append({"offset":m.start(),"text":s})
    return rows

def action_records(data):
    out=[]
    for i in range(max(0,len(data)-4)):
        if data[i:i+2]!=b"\x10\x00": continue
        opcode=data[i+2]; end=data.find(b"\x00",i+3,min(i+99,len(data)))
        if end<0 or end==i+3: continue
        raw=data[i+3:end]
        if all(32<=b<127 for b in raw):
            out.append({"offset":i,"opcode":opcode,"token":raw.decode("latin1")})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",action="append",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--radius",type=int,default=512)
    a=ap.parse_args()
    result={"schema":"openazrael.readable_look_correlation","version":159,"files":{},"warning":"Byte proximity is evidence only; it does not prove dispatch semantics."}
    for raw_path in a.input:
        p=Path(raw_path); data=p.read_bytes()
        target=hits(data,TOKENS); look=hits(data,LOOK); actions=action_records(data)
        neighborhoods=[]
        for t in target:
            neighborhoods.append({"target":t,
                "look_hits":[x for x in look if abs(x["offset"]-t["offset"])<=a.radius],
                "action_hits":[x for x in actions if abs(x["offset"]-t["offset"])<=a.radius]})
        result["files"][str(p)]={"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"target_hits":target,"look_hits":look,"neighborhoods":neighborhoods}
    Path(a.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","out":a.out,"files":len(result["files"])},indent=2))
if __name__=="__main__": main()
