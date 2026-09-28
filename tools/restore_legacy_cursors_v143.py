#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"data/ui/legacy_cursor_manifest_v143.json"
OUT_ROOT=ROOT/"assets/ui/mice"
RECEIPT=ROOT/".tmp/kg001/legacy_cursor_restore_v143.json"

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def convert(source:Path,destination:Path)->dict:
    with Image.open(source) as indexed:
        indexed.load()
        if indexed.mode!="P":
            raise ValueError(f"{source.name}: expected indexed PCX, got {indexed.mode}")
        if indexed.getpalette() is None:
            raise ValueError(f"{source.name}: palette missing")
        rgba=indexed.convert("RGBA")
        source_indices=list(indexed.getdata())
        alpha=Image.new("L",indexed.size,255)
        alpha.putdata([0 if int(v)==0 else 255 for v in source_indices])
        rgba.putalpha(alpha)
        destination.parent.mkdir(parents=True,exist_ok=True)
        rgba.save(destination,format="PNG",optimize=False)
        return {
            "width":indexed.width,
            "height":indexed.height,
            "transparent_pixels":sum(1 for v in source_indices if int(v)==0),
            "runtime_png_sha256":sha256(destination),
            "runtime_png_bytes":destination.stat().st_size,
        }

def main()->int:
    ap=argparse.ArgumentParser(description="Restore source-exact Azrael's Tear demo cursor art from ATDEMO/MICE.")
    ap.add_argument("demo_dir",type=Path)
    args=ap.parse_args()
    mice=args.demo_dir.resolve()/"MICE"
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    specs=manifest["files"]
    actual=sorted(p.name for p in mice.glob("*.PCX"))
    expected=sorted(specs)
    if actual!=expected:
        raise ValueError({"cursor_corpus_mismatch":{"expected":expected,"actual":actual}})
    rows=[]
    for name in expected:
        src=mice/name
        source_sha=sha256(src)
        spec=specs[name]
        if source_sha!=str(spec[0]) or src.stat().st_size!=int(spec[1]):
            raise ValueError(f"{name}: source fingerprint mismatch")
        with Image.open(src) as im:
            if im.size!=(int(spec[2]),int(spec[3])):
                raise ValueError(f"{name}: source dimensions mismatch {im.size}")
        destination=OUT_ROOT/(Path(name).stem+".png")
        converted=convert(src,destination)
        rows.append({
            "source":name,
            "source_sha256":source_sha,
            "runtime":str(destination.relative_to(ROOT)).replace("\\","/"),
            **converted,
        })
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    receipt={"schema":"openazrael.kg001.legacy_cursor_restore","version":143,"status":"PASS","source_count":len(rows),"runtime_count":len(rows),"files":rows}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","source_count":len(rows),"runtime_count":len(rows),"output":str(OUT_ROOT.relative_to(ROOT))},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
