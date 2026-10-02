#!/usr/bin/env python3
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; TMP=ROOT/".tmp/kg001"; P=TMP/"candidate5_preflight_receipt.json"; F=TMP/"candidate5_frozen_release_receipt.json"
def run(c):return subprocess.run(c,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--godot");ap.add_argument("--out",default="exports/OpenAzrael-KG001-Candidate5.exe");a=ap.parse_args()
 if not P.is_file() or not F.is_file(): print('{"status":"FAIL","reason":"C5_PREFLIGHT_OR_FREEZE_MISSING"}');return 1
 p=json.loads(P.read_text());f=json.loads(F.read_text());head=run(["git","rev-parse","HEAD"]).stdout.strip()
 if p.get("status")!="PASS" or p.get("build_allowed") is not True or f.get("status")!="PASS" or f.get("commit_sha")!=head: print('{"status":"FAIL","reason":"C5_GATE_NOT_OPEN"}');return 1
 godot=a.godot or ""; 
 if not godot: print('{"status":"FAIL","reason":"GODOT_REQUIRED"}');return 1
 out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True)
 r=run([godot,"--headless","--path",str(ROOT),"--export-release","Windows Candidate 5",str(out)])
 errs=[x for x in r.stdout.splitlines() if x.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))]
 status="PASS" if r.returncode==0 and not errs and out.is_file() else "FAIL"
 print(json.dumps({"schema":"openazrael.kg001.candidate5_export","version":202,"status":status,"commit_sha":head,"artifact":str(out.relative_to(ROOT)) if out.is_file() else None,"engine_errors":errs,"output_tail":r.stdout[-12000:]},indent=2));return 0 if status=="PASS" else 1
if __name__=="__main__":sys.exit(main())
