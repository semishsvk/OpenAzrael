#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; TMP=ROOT/".tmp/kg001"; P=TMP/"candidate5_preflight_receipt.json"; OUT=TMP/"candidate5_frozen_release_receipt.json"
ROOTS=(ROOT/"assets/rooms",ROOT/"assets/audio",ROOT/"assets/textures/classic",ROOT/"assets/ui/mice",ROOT/"assets/ui/legacy_menu")
def run(c):return subprocess.run(c,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def main():
 OUT.unlink(missing_ok=True)
 if not P.is_file(): print('{"status":"FAIL","reason":"C5_PREFLIGHT_MISSING"}'); return 1
 x=json.loads(P.read_text()); 
 if x.get("status")!="PASS" or x.get("build_allowed") is not True: print('{"status":"FAIL","reason":"C5_PREFLIGHT_NOT_PASS"}'); return 1
 head=run(["git","rev-parse","HEAD"]).stdout.strip(); tree=run(["git","rev-parse","HEAD^{tree}"]).stdout.strip()
 if x.get("commit_sha")!=head: print('{"status":"FAIL","reason":"HEAD_CHANGED"}'); return 1
 if run(["git","status","--porcelain","--untracked-files=normal"]).stdout.strip(): print('{"status":"FAIL","reason":"DIRTY_GIT"}'); return 1
 files=sorted([p for r in ROOTS if r.is_dir() for p in r.rglob("*") if p.is_file()],key=lambda p:str(p))
 ident={str(p.relative_to(ROOT)):{"bytes":p.stat().st_size,"sha256":sha(p)} for p in files}
 digest=hashlib.sha256(json.dumps(ident,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 out={"schema":"openazrael.kg001.candidate5_frozen_release","version":202,"status":"PASS","candidate":"KG-001 Candidate 5","commit_sha":head,"source_tree_sha":tree,"preflight_receipt_sha256":sha(P),"runtime_asset_identity":{"file_count":len(ident),"canonical_sha256":digest},"source_safe":True,"commercial_payload_bytes_embedded":False}
 OUT.write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2)); return 0
if __name__=="__main__":sys.exit(main())
