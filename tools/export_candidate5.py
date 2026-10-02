#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; TMP=ROOT/".tmp/kg001"; P=TMP/"candidate5_preflight_receipt.json"; F=TMP/"candidate5_frozen_release_receipt.json"; ID=ROOT/"data/runtime_build_identity.json"
def run(c):return subprocess.run(c,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def sha(p):\n h=hashlib.sha256()\n with p.open("rb") as f:\n  for b in iter(lambda:f.read(1048576),b""):h.update(b)\n return h.hexdigest()\ndef marker(s,m):
 for line in reversed(s.splitlines()):
  if m in line:
   try:return json.loads(line.split(m,1)[1].strip())
   except:return {"status":"FAIL"}
 return {"status":"FAIL"}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--godot");ap.add_argument("--out",default="exports/OpenAzrael-KG001-Candidate5.exe");a=ap.parse_args()
 if not P.is_file() or not F.is_file(): print('{"status":"FAIL","reason":"C5_PREFLIGHT_OR_FREEZE_MISSING"}');return 1
 p=json.loads(P.read_text());f=json.loads(F.read_text());head=run(["git","rev-parse","HEAD"]).stdout.strip()
 if p.get("status")!="PASS" or p.get("build_allowed") is not True or p.get("commit_sha")!=head or f.get("status")!="PASS" or f.get("commit_sha")!=head or f.get("preflight_receipt_sha256")!=sha(P): print('{"status":"FAIL","reason":"C5_GATE_NOT_OPEN"}');return 1
 if run(["git","status","--porcelain","--untracked-files=normal"]).stdout.strip(): print('{"status":"FAIL","reason":"DIRTY_GIT"}');return 1
 if not a.godot: print('{"status":"FAIL","reason":"GODOT_REQUIRED"}');return 1
 ident={"schema":"openazrael.runtime_build_identity","version":1,"candidate":"KG-001 Candidate 5","commit_sha":head,"preset":"Windows Candidate 5"}
 ID.write_text(json.dumps(ident,indent=2)+"\n")
 out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);out.unlink(missing_ok=True);out.with_suffix(".pck").unlink(missing_ok=True)
 r=run([a.godot,"--headless","--path",str(ROOT),"--export-release","Windows Candidate 5",str(out)])
 errs=[x for x in r.stdout.splitlines() if x.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))]
 if r.returncode or errs or not out.is_file() or not out.with_suffix(".pck").is_file(): ID.unlink(missing_ok=True);print(json.dumps({"status":"FAIL","reason":"EXPORT_FAILED","engine_errors":errs,"output_tail":r.stdout[-12000:]},indent=2));return 1
 specs=[
  ("origin","res://scripts/kg001_candidate5_packaged_origin_runner_v203.gd","OPENAZRAEL_KG001_C5_PACKAGED_ORIGIN_V203"),
  ("parity","res://scripts/kg001_packaged_parity_runner_v128.gd","OPENAZRAEL_KG001_PACKAGED_PARITY_V128"),
  ("transitions","res://scripts/kg001_all_transition_runner_v141.gd","OPENAZRAEL_KG001_ALL_TRANSITIONS_V141"),
  ("cursor","res://scripts/kg001_interaction_cursor_runner_v143.gd","OPENAZRAEL_KG001_CURSOR_V143"),
  ("menu","res://scripts/kg001_legacy_menu_runner_v145.gd","OPENAZRAEL_KG001_MENU_V145"),
  ("inventory","res://scripts/kg001_inventory_hud_runner_v157.gd","OPENAZRAEL_KG001_INVENTORY_HUD_V157")
 ]
 results={}
 for name,script,m in specs:
  q=run([str(out),"--headless","--script",script]); z=marker(q.stdout,m); results[name]=z
  if q.returncode or z.get("status")!="PASS":
   ID.unlink(missing_ok=True);print(json.dumps({"status":"FAIL","reason":"PACKAGED_RUNTIME_FAILED","test":name,"result":z,"output_tail":q.stdout[-12000:]},indent=2));return 1
 ID.unlink(missing_ok=True)
 print(json.dumps({"schema":"openazrael.kg001.candidate5_export","version":204,"status":"PASS","commit_sha":head,"preflight_receipt_sha256":sha(P),"freeze_receipt_sha256":sha(F),"artifacts":{str(out.relative_to(ROOT)):{"bytes":out.stat().st_size,"sha256":sha(out)},str(out.with_suffix(".pck").relative_to(ROOT)):{"bytes":out.with_suffix(".pck").stat().st_size,"sha256":sha(out.with_suffix(".pck"))}},"packaged":results},indent=2));return 0
if __name__=="__main__":sys.exit(main())
