#!/usr/bin/env python3
"""Fail-closed original Azrael MOV inventory."""
import argparse, hashlib, json, struct
from pathlib import Path
FILES=("MINDLOGO.MOV","INTRO.MOV","MOV/INTRO.MOV","MOV/DEMO.MOV")
def inspect(root,name):
    b=(root/name).read_bytes()
    if len(b)<48 or b[:4]!=bytes.fromhex("90ef12ab"): raise ValueError(name+": invalid header")
    count,depth,width,height=struct.unpack_from("<HHHH",b,4)
    if not(1<=count<=10000 and depth in (8,12,15,16,24,32) and 1<=width<=4096 and 1<=height<=4096): raise ValueError(name+": invalid dimensions")
    return dict(file=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),header_candidate=dict(count=count,depth=depth,width=width,height=height),codec="UNKNOWN",frames="BLOCKED",audio="UNKNOWN")
def main():
    p=argparse.ArgumentParser();p.add_argument("corpus",type=Path);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    result=dict(schema="openazrael.intro_mov_evidence.v1",status="STRUCTURAL_ONLY",files=[inspect(a.corpus,n) for n in FILES],fidelity_pass=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":result["status"],"files":len(result["files"])}))
if __name__=="__main__":main()