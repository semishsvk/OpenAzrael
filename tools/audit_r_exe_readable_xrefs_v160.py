#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
ASCII=re.compile(rb"[\x20-\x7e]{3,}")
TERMS=("LOOK.PCX","BLOOK.PCX","LOOK1.PCX","LOOK2.PCX","LOOK3.PCX","PHOTO.PCX","r1p1","PAPER","Parchment")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("exe",type=Path); ap.add_argument("--out",type=Path,required=True); ap.add_argument("--radius",type=int,default=1024); a=ap.parse_args()
    data=a.exe.read_bytes(); strings=[(m.start(),m.group().decode("latin1")) for m in ASCII.finditer(data)]
    hits=[]
    for off,s in strings:
        if any(t.lower() in s.lower() for t in TERMS):
            near=[{"offset":o,"text":x} for o,x in strings if o!=off and abs(o-off)<=a.radius]
            hits.append({"offset":off,"text":s,"neighbors":near})
    payload={"schema":"openazrael.r_exe_readable_xref_window","version":160,"exe":{"path":str(a.exe),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()},"radius":a.radius,"hits":hits,"warning":"String-window proximity is structural evidence only, not control-flow proof."}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","hits":len(hits),"out":str(a.out)},indent=2))
if __name__=="__main__": main()
