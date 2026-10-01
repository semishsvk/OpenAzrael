#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets/source_books/1_1_0.png"
RECEIPT=ROOT/".tmp/kg001/r1p1_book_restore_v162.json"
EXPECTED_BOK_SHA="69525535f529aa4ce37e826d90b6bbaa0bdb85a6a18cf689529c33a7d6ae0d18"
EXPECTED_PCX_SHA="b17ec230b56fbcacdbe51cb2dd50bb584dc477f543a6999ff5fedfa8a9cc9dae"
EXPECTED_BOK=b"1_1_\r\n1\r\n\x1a"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser(description="Restore verified R1P1 book page from an extracted ATDEMO directory.")
    ap.add_argument("demo_dir",type=Path)
    a=ap.parse_args(); root=a.demo_dir.resolve()
    bok=root/"BOOKS/R1P1.BOK"; pcx=root/"TEXTURES/BOOKS/1_1_0.PCX"
    if not bok.is_file() or not pcx.is_file(): raise FileNotFoundError("R1P1 source book files missing")
    if sha(bok)!=EXPECTED_BOK_SHA or bok.read_bytes()!=EXPECTED_BOK: raise ValueError("R1P1.BOK fingerprint/descriptor mismatch")
    if sha(pcx)!=EXPECTED_PCX_SHA: raise ValueError("1_1_0.PCX fingerprint mismatch")
    with Image.open(pcx) as im:
        im.load()
        if im.size!=(640,480) or im.mode!="P": raise ValueError(f"unexpected R1P1 page format {im.mode} {im.size}")
        OUT.parent.mkdir(parents=True,exist_ok=True)
        im.convert("RGB").save(OUT,format="PNG",optimize=False)
    receipt={"schema":"openazrael.kg001.r1p1_book_restore","version":162,"status":"PASS","descriptor_sha256":sha(bok),"source_pcx_sha256":sha(pcx),"source_dimensions":[640,480],"runtime":str(OUT.relative_to(ROOT)).replace("\\","/"),"runtime_png_sha256":sha(OUT)}
    RECEIPT.parent.mkdir(parents=True,exist_ok=True); RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
