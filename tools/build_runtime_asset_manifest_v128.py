#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
ROOTS=(ROOT/"assets/rooms",ROOT/"assets/audio",ROOT/"assets/textures/classic",ROOT/"assets/ui/mice")
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,default=ROOT/"data/runtime_generated/runtime_asset_manifest_v128.json");args=ap.parse_args()
    files=[]
    for base in ROOTS:
        if base.is_dir():
            files.extend(p for p in base.rglob("*") if p.is_file())
    files=sorted(set(files),key=lambda p:str(p.relative_to(ROOT)).lower())
    payload={"schema":"openazrael.runtime_asset_manifest","version":128,"files":{
        str(p.relative_to(ROOT)).replace("\\","/"):{"bytes":p.stat().st_size,"sha256":sha(p)} for p in files
    }}
    payload["file_count"]=len(payload["files"])
    payload["room_glb_count"]=sum(1 for p in files if p.parent==ROOT/"assets/rooms" and p.suffix.lower()==".glb")
    payload["classic_png_count"]=sum(1 for p in files if p.parent==ROOT/"assets/textures/classic" and p.suffix.lower()==".png")
    payload["audio_file_count"]=sum(1 for p in files if (ROOT/"assets/audio") in p.parents)
    payload["cursor_png_count"]=sum(1 for p in files if p.parent==ROOT/"assets/ui/mice" and p.suffix.lower()==".png")
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    ok=payload["room_glb_count"]>=3 and payload["classic_png_count"]==86 and payload["audio_file_count"]>0 and payload["cursor_png_count"]==35
    print(json.dumps({"status":"PASS" if ok else "FAIL",**{k:payload[k] for k in ("file_count","room_glb_count","classic_png_count","audio_file_count","cursor_png_count")}},indent=2))
    return 0 if ok else 1
if __name__=="__main__":raise SystemExit(main())
