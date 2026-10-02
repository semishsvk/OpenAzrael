#!/usr/bin/env python3
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"data/tests/kg001_candidate5_release_contract_v202.json"
OUT=ROOT/".tmp/kg001/candidate5_preflight_receipt.json"
def run(cmd): return subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--godot"); ap.add_argument("--demo-dir"); ap.add_argument("--soundfont"); ap.add_argument("--fluidsynth-lib"); a=ap.parse_args()
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.unlink(missing_ok=True)
 c=json.loads(C.read_text(encoding="utf-8")); rows=[]; source_ok=True
 base=[sys.executable,"tools/run_candidate4_preflight.py"]
 if a.godot: base+=["--godot",a.godot]
 if a.demo_dir: base+=["--demo-dir",a.demo_dir]
 if a.soundfont: base+=["--soundfont",a.soundfont]
 if a.fluidsynth_lib: base+=["--fluidsynth-lib",a.fluidsynth_lib]
 for tool in ["tools/validate_candidate5_release_contract_v202.py",*c["additional_source_gates"]]:
  p=run([sys.executable,tool]); rows.append({"tool":tool,"returncode":p.returncode,"status":"PASS" if p.returncode==0 else "FAIL","output_tail":p.stdout[-8000:]}); source_ok &= p.returncode==0
 if not source_ok:
  payload={"schema":"openazrael.kg001.candidate5_preflight","version":202,"status":"FAIL","build_allowed":False,"stage":"SOURCE_GATES","source":rows}; OUT.write_text(json.dumps(payload,indent=2)+"\n"); print(json.dumps(payload,indent=2)); return 1
 inherited=run(base)
 v201=run([sys.executable,"tools/validate_kg001_c4_runtime_evidence_v201.py"])
 head=run(["git","rev-parse","HEAD"]).stdout.strip()\n payload={"schema":"openazrael.kg001.candidate5_preflight","version":203,"status":"PASS" if inherited.returncode==0 and v201.returncode==0 else "BLOCKED","build_allowed":inherited.returncode==0 and v201.returncode==0,"commit_sha":head,"source":rows,"c5_headless_runtime":runtime_rows,"candidate4_preflight_returncode":inherited.returncode,"candidate4_preflight_output_tail":inherited.stdout[-12000:],"v201_returncode":v201.returncode,"v201_output_tail":v201.stdout[-12000:],"rule":"C5 build requires inherited C4 preflight plus exact-current-HEAD v201 runtime evidence."}
 OUT.write_text(json.dumps(payload,indent=2)+"\n"); print(json.dumps(payload,indent=2)); return 0 if payload["build_allowed"] else 2
if __name__=="__main__":sys.exit(main())
