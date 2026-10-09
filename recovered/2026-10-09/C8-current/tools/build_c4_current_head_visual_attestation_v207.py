#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_PROOF=ROOT/".tmp/kg001_proof_capture/kg001_proof_capture_receipt_v152.json"
DEFAULT_OUT=ROOT/".tmp/kg001_c4_closure/current_head_visual_runtime.json"
C4_PREFLIGHT=ROOT/".tmp/kg001/candidate4_preflight_receipt.json"
REQUIRED=["menu_hud_visible","cursor_visible_and_contextual","inventory_items_visible","keyhole_orientation_matches_reference","room3_windows_orientation_matches_reference","stairs_traversal_observed"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def head():
 return subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,text=True,stdout=subprocess.PIPE).stdout.strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--proof",type=Path,default=DEFAULT_PROOF);ap.add_argument("--checks",type=Path,required=True);ap.add_argument("--out",type=Path,default=DEFAULT_OUT);a=ap.parse_args()
 try:p=json.loads(a.proof.read_text());c=json.loads(a.checks.read_text())
 except Exception as e: print(json.dumps({"status":"FAIL","reason":"INPUT_INVALID","error":str(e)}));return 1
 h=head(); checks=c.get("checks",{})
 proof_preflight_sha=p.get("preflight_receipt",{}).get("sha256")
 ok=(C4_PREFLIGHT.is_file() and proof_preflight_sha==sha(C4_PREFLIGHT) and p.get("status")=="PASS" and p.get("commit_sha")==h and p.get("ai_generated_visuals") is False and p.get("noclip_or_fly_camera") is False and p.get("direct_gameplay_state_injection") is False and c.get("commit_sha")==h and all(checks.get(k) is True for k in REQUIRED))
 out={"schema":"openazrael.kg001.c4_current_head_visual_runtime","version":207,"status":"PASS" if ok else "FAIL","commit_sha":h,"ai_generated":False,"checks":{k:checks.get(k) is True for k in REQUIRED},"candidate4_preflight_sha256":sha(C4_PREFLIGHT) if C4_PREFLIGHT.is_file() else None,"proof_capture":{"path":str(a.proof.relative_to(ROOT)),"sha256":sha(a.proof)},"checkpoint_attestation":{"path":str(a.checks.relative_to(ROOT)) if a.checks.is_relative_to(ROOT) else str(a.checks),"sha256":sha(a.checks)}}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2));return 0 if ok else 1
if __name__=="__main__":sys.exit(main())
