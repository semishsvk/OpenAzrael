#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BOOKS={
 "R1P1":{"descriptor":b"1_1_\r\n1\r\n\x1a","bok_sha":"69525535f529aa4ce37e826d90b6bbaa0bdb85a6a18cf689529c33a7d6ae0d18","pcx":"1_1_0.PCX","pcx_sha":"b17ec230b56fbcacdbe51cb2dd50bb584dc477f543a6999ff5fedfa8a9cc9dae","png":"1_1_0.png"},
 "R3T1":{"descriptor":b"r3t1_\r\n1\r\n\x1a","bok_sha":"79eda3dff3fd663f76117955d94d97270b88b3b24291f04f760edc6fa913c771","pcx":"R3T1_0.PCX","pcx_sha":"2b39a403187b724a13e89ec2b65bf9940cb6781cc33d7152eba2996caac5c161","png":"r3t1_0.png"},
 "R8T3":{"descriptor":b"r8t3_\r\n1\r\n\x1a","bok_sha":"d1286dfc12ac8169aff367408056b9770c9e70b511ecad604c91f22f936ce608","pcx":"R8T3_0.PCX","pcx_sha":"196ab58f3f31fcd71714b4008dd3a27de47baf220e2d5fde9d9025554c2c0689","png":"r8t3_0.png"},
 "R8T4":{"descriptor":b"r8t4_\r\n1\r\n\x1a","bok_sha":"62eba9574a87bc7ddb48df990c5f3d779fbe603e88ad3343bd542a9e7c96d22b","pcx":"R8T4_0.PCX","pcx_sha":"8b5d3736e50b3821aa91b5984704483a5390ba90be93476f7b905082aef52043","png":"r8t4_0.png"}
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("demo_dir",type=Path);a=ap.parse_args();src=a.demo_dir.resolve();outdir=ROOT/"assets/source_books";outdir.mkdir(parents=True,exist_ok=True);rows=[]
 for key,s in BOOKS.items():
  bok=src/"BOOKS"/(key+".BOK");pcx=src/"TEXTURES/BOOKS"/s["pcx"]
  if not bok.is_file() or not pcx.is_file():raise FileNotFoundError(key+" source book files missing")
  if bok.read_bytes()!=s["descriptor"] or sha(bok)!=s["bok_sha"]:raise ValueError(key+" descriptor mismatch")
  if sha(pcx)!=s["pcx_sha"]:raise ValueError(key+" PCX fingerprint mismatch")
  with Image.open(pcx) as im:
   im.load()
   if im.size!=(640,480) or im.mode!="P":raise ValueError(key+" unexpected page format")
   out=outdir/s["png"];im.convert("RGB").save(out,format="PNG",optimize=False)
  rows.append({"object":key,"descriptor_sha256":sha(bok),"source_pcx":s["pcx"],"source_pcx_sha256":sha(pcx),"runtime":"assets/source_books/"+s["png"],"runtime_png_sha256":sha(out),"dimensions":[640,480]})
 receipt={"schema":"openazrael.kg001.demo_book_restore","version":171,"status":"PASS","books":rows,"missing_source_declared":[{"object":"R7P1","status":"SOURCE_INCOMPLETE","reason":"opcode 0x21 is present in WORLD but R7P1.BOK/page is absent from supplied ATDEMO"}]}
 p=ROOT/".tmp/kg001/demo_book_restore_v171.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(receipt,indent=2)+"\n");print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
