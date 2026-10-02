#!/usr/bin/env python3
"""Fail-closed Candidate 5 build preparation/orchestration."""
from pathlib import Path
import argparse,json,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
TMP=ROOT/".tmp/kg001_candidate5"
def run(cmd):
 p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 return p
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--godot",required=True);ap.add_argument("--demo-dir");ap.add_argument("--soundfont");ap.add_argument("--fluidsynth-lib")
 ap.add_argument("--pacing-capture",type=Path);ap.add_argument("--visual-checks",type=Path)
 ap.add_argument("--ffmpeg");ap.add_argument("--ffprobe");ap.add_argument("--prepare-only",action="store_true")
 ap.add_argument("--out",default="exports/OpenAzrael-KG001-Candidate5.exe");a=ap.parse_args()
 TMP.mkdir(parents=True,exist_ok=True); head=run(["git","rev-parse","HEAD"]).stdout.strip()
 stages=[]
 def stage(name,cmd,ok=(0,)):
  p=run(cmd); row={"name":name,"command":cmd,"returncode":p.returncode,"status":"PASS" if p.returncode in ok else "BLOCKED","output_tail":p.stdout[-12000:]};stages.append(row)
  return p
 if run(["git","status","--porcelain","--untracked-files=normal"]).stdout.strip():
  print(json.dumps({"status":"BLOCKED","reason":"DIRTY_GIT","commit_sha":head},indent=2));return 2
 preset=(ROOT/"export_presets.cfg").read_text(encoding="utf-8")
 project=(ROOT/"project.godot").read_text(encoding="utf-8")
 if 'name="Windows Candidate 5"' not in preset or 'config/name="OpenAzrael KG-001 Candidate 5"' not in project or 'config/version="KG001-Candidate-5"' not in project:
  return finish(head,stages,"CANDIDATE5_EXPORT_IDENTITY_INVALID")
 p=stage("candidate4_preflight",[sys.executable,"tools/run_candidate4_preflight.py","--godot",a.godot]+(["--demo-dir",a.demo_dir] if a.demo_dir else [])+(["--soundfont",a.soundfont] if a.soundfont else [])+(["--fluidsynth-lib",a.fluidsynth_lib] if a.fluidsynth_lib else []))
 if p.returncode: return finish(head,stages,"CANDIDATE4_PREFLIGHT_FAILED")
 p=stage("pppv_current_head",[sys.executable,"tools/run_candidate3_pppv_v2.py","--godot",a.godot,"--fresh-checkout"])
 if p.returncode: return finish(head,stages,"PPPV_FAILED")
 p=stage("candidate4_freeze",[sys.executable,"tools/freeze_candidate4_release.py"])
 if p.returncode: return finish(head,stages,"CANDIDATE4_FREEZE_FAILED")
 p=stage("graphical_proof",[sys.executable,"tools/capture_candidate4_proof_video.py"]+(["--ffmpeg",a.ffmpeg] if a.ffmpeg else [])+(["--ffprobe",a.ffprobe] if a.ffprobe else []))
 if p.returncode: return finish(head,stages,"GRAPHICAL_PROOF_FAILED")
 if not a.visual_checks or not a.visual_checks.is_file():
  return finish(head,stages,"VISUAL_CHECKPOINT_ATTESTATION_REQUIRED",{"required_checks":["menu_hud_visible","cursor_visible_and_contextual","inventory_items_visible","keyhole_orientation_matches_reference","room3_windows_orientation_matches_reference","stairs_traversal_observed"]})
 p=stage("visual_closure",[sys.executable,"tools/build_c4_current_head_visual_attestation_v207.py","--checks",str(a.visual_checks)])
 if p.returncode:return finish(head,stages,"VISUAL_CLOSURE_FAILED")
 if not a.pacing_capture or not a.pacing_capture.is_file():
  return finish(head,stages,"ORIGINAL_DOSBOX_V199_CAPTURE_REQUIRED",{"contract":"data/tests/kg001_legacy_scene_update_pacing_capture_contract_v199.json"})
 pacing_out=ROOT/".tmp/kg001_c4_closure/original_runtime_pacing_validation_v199.json";pacing_out.parent.mkdir(parents=True,exist_ok=True)
 p=stage("original_runtime_pacing_v199",[sys.executable,"tools/validate_kg001_legacy_scene_update_pacing_v199.py","--capture",str(a.pacing_capture),"--out",str(pacing_out)])
 if p.returncode:return finish(head,stages,"V199_PACING_FAILED")
 p=stage("v201_runtime_evidence",[sys.executable,"tools/validate_kg001_c4_runtime_evidence_v201.py"])
 if p.returncode:return finish(head,stages,"V201_RUNTIME_EVIDENCE_FAILED")
 c5=[sys.executable,"tools/run_candidate5_preflight.py","--godot",a.godot]+(["--demo-dir",a.demo_dir] if a.demo_dir else [])+(["--soundfont",a.soundfont] if a.soundfont else [])+(["--fluidsynth-lib",a.fluidsynth_lib] if a.fluidsynth_lib else [])
 p=stage("candidate5_preflight",c5)
 if p.returncode:return finish(head,stages,"CANDIDATE5_PREFLIGHT_FAILED")
 p=stage("candidate5_freeze",[sys.executable,"tools/freeze_candidate5_release.py"])
 if p.returncode:return finish(head,stages,"CANDIDATE5_FREEZE_FAILED")
 if a.prepare_only:return finish(head,stages,None,{"build_ready":True,"export_executed":False})
 p=stage("candidate5_export",[sys.executable,"tools/export_candidate5.py","--godot",a.godot,"--out",a.out])
 if p.returncode:return finish(head,stages,"CANDIDATE5_EXPORT_FAILED")
 out=ROOT/a.out;pck=out.with_suffix(".pck")
 return finish(head,stages,None,{"build_ready":True,"export_executed":True,"artifacts":{str(out.relative_to(ROOT)):sha(out),str(pck.relative_to(ROOT)):sha(pck)}})
def finish(head,stages,reason=None,extra=None):
 payload={"schema":"openazrael.kg001.candidate5_build_orchestration","version":208,"status":"PASS" if reason is None else "BLOCKED","commit_sha":head,"reason":reason,"stages":stages}
 if extra:payload.update(extra)
 p=TMP/"candidate5_build_orchestration_receipt.json";p.write_text(json.dumps(payload,indent=2)+"\n");print(json.dumps(payload,indent=2));return 0 if reason is None else 2
if __name__=="__main__":sys.exit(main())
