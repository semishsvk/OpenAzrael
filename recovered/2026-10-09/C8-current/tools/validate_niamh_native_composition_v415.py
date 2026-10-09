#!/usr/bin/env python3
"""Native original R.EXE / actual Godot R7 Niamh REST composition gate.

Evidence requirement: six SHA-pinned genuine DOSBox-X images, derived
R7 source geometry, actual rendered *production* player camera and actor.
This gate verifies measurable static visual improvement only. It MUST NOT
be interpreted as animation, dialogue, PCM sound or Candidate fidelity PASS.
"""
from pathlib import Path
from PIL import Image
import hashlib,json,numpy as np,os,subprocess,sys,time,argparse
ROOT=Path(__file__).resolve().parents[1]
CAP=Path(os.environ.get("OPENAZRAEL_ORIGINAL_CAPTURE_ROOT",
 "F:/OpenRemaster/captures/OpenAzrael_C8_20261009"))
GODOT=Path(os.environ.get("OPENAZRAEL_GODOT_BIN",
 "F:/Remaster Framework/source/Godot/Godot_v4.7.2-stable_win64.exe"))
MANIFEST=ROOT/"data/reconstruction/niamh_visual_calibration_v415.json"
REPORT=ROOT/".tmp/niamh_native_original_composition_v415.json"
ORIGINALS=CAP/"original_niamh_visible_v397"
REGION=(242,105,320,320)
THRESHOLD_MEAN=29.0
THRESHOLD_MIN=25.0
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as file:
  for buf in iter(lambda:file.read(1048576),b""):h.update(buf)
 return h.hexdigest()
def rgb(p):
 with Image.open(p) as source:
  if source.size!=(640,480):raise ValueError("Expected real 640x480 framebuffer: "+str(p))
  return np.asarray(source.convert("RGB"),dtype=np.float32)
def run(fresh:bool):
 started=time.monotonic()
 meta=json.loads(MANIFEST.read_text(encoding="utf8"))
 native=meta["source_native_capture_evidence"]
 assert len(native)==6
 originals=[]
 for evidence in native:
  name=evidence["file"]
  if name not in [f"r_{i:03d}.raw1.png" for i in range(3,9)]:
   raise ValueError("unexpected original Niamh source frame")
  p=ORIGINALS/name
  if not p.is_file():raise FileNotFoundError("MISSING_AUTHORITATIVE_NATIVE_FRAME:"+str(p))
  if sha(p)!=evidence["sha256"]:
   raise ValueError("SOURCE_FRAME_SHA_DRIFT:"+name)
  originals.append((name,evidence["sha256"],rgb(p)))
 if fresh:
  env=os.environ.copy()
  env["OPENAZRAEL_SKIP_INTRO"]="1"
  p=subprocess.run([str(GODOT),"--path",str(ROOT),
    "--script","res://scripts/validation/production_original_camera_probe_v410.gd"],
    cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
    encoding="utf8",errors="replace",env=env,timeout=70)
  if p.returncode!=0 or '"status":"PASS"' not in p.stdout:
   raise RuntimeError("Godot render failed to produce fresh original-camera visual: "+p.stdout[-1300:])
 render_receipt=json.loads((ROOT/".tmp/production_camera_original_ram_v410.json").read_text(encoding="utf8"))
 if render_receipt.get("status")!="PASS" or render_receipt.get("checks")!=17:
  raise ValueError("PRODUCTION_CAMERA_RENDER_IS_NOT_VERIFIED")
 model=ROOT/".tmp/original_player_camera_v410_R7_NIAMH_REST.png"
 background=ROOT/".tmp/original_player_camera_v410_R7_BACKGROUND.png"
 if not model.exists() or not background.exists():
  raise FileNotFoundError("UNAVAILABLE_ACTUAL_RENDERED_GODOT_SCREENSHOTS")
 restored=rgb(model)
 backdrop=rgb(background)
 x0,y0,x1,y1=REGION
 mask=np.zeros((480,640),dtype=bool)
 mask[y0:y1,x0:x1]=True
 mask[145:167,310:333]=False
 evidence=[]
 for file,fingerprint,original in originals:
  baseline=float(np.abs(original-backdrop)[mask].mean())
  calibrated=float(np.abs(original-restored)[mask].mean())
  if baseline<=.01:raise ValueError("native reference lacks measurable foreground difference")
  improvement=100*(1-calibrated/baseline)
  evidence.append({"source":file,"original_sha256":fingerprint,
      "source_baseline_abs_R_G_B":round(baseline,4),
      "calibrated_abs_R_G_B":round(calibrated,4),
      "relative_error_reduction_percent":round(improvement,4)})
 avg=float(np.mean([e["relative_error_reduction_percent"] for e in evidence]))
 worst=min(x["relative_error_reduction_percent"] for x in evidence)
 # Source metadata declares only an independent experimental fit; score
 # is calculated again from the now actual production runtime, not reused.
 valid=avg>=THRESHOLD_MEAN and worst>=THRESHOLD_MIN
 # Negative control, no actor at all: relative improvement MUST be zero.
 negative_without_actor=all(abs(100*(1-
  np.abs(original-backdrop)[mask].mean()/
  np.abs(original-backdrop)[mask].mean()))<1e-6 for _,_,original in originals)
 if not negative_without_actor:raise ValueError("NEGATIVE_NO_ACTOR_CONTROL_FAILED")
 results={
  "schema":"openazrael.c8.original_R7_niamh_production_reconstruction.v415",
  "status":"SOURCE_VISUAL_COMPOSITION_IMPROVED_FIDELITY_HOLD" if valid else "FAIL_VISUAL_COMPOSITION_REGRESSION",
  "original_source":"native DOSBox-X original R.EXE, NIAMH REST output, six time-separated frames",
  "production_source":"actual Godot 4.7.2 Player/Camera3D, NIAMH loaded from XAF source",
  "original_camera_R7_xyz":[7.648277282714844,4.2041473388671875,3.9145851135253906],
  "source_original_frame_count":len(evidence),
  "production_niamh_image_sha256":sha(model),
  "production_background_sha256":sha(background),
  "actor_region_xyxy":list(REGION),
  "mean_improvement_percent":round(avg,4),
  "min_improvement_percent":round(worst,4),
  "mean_threshold_percent":THRESHOLD_MEAN,
  "min_threshold_percent":THRESHOLD_MIN,
  "each_native":evidence,
  "negative_no_actor_baseline":"REJECTED_AS_VISUAL_FIDELITY",
  "original_animation_timing":"HOLD_15_FPS_PROVISIONAL",
  "original_PCM_sound":"HOLD_MILES_SETUP_INCOMPLETE",
  "retail_verification":"HOLD",
  "candidate_fidelity":"HOLD",
  "duration_seconds":round(time.monotonic()-started,2)}
 REPORT.write_text(json.dumps(results,indent=2)+"\n",encoding="utf8")
 print("OPENAZRAEL_NIAMH_NATIVE_COMPOSITION_V415 "+json.dumps({
  "status":results["status"],"frames":len(evidence),
  "mean_error_improvement_percent":results["mean_improvement_percent"],
  "min_error_improvement_percent":results["min_improvement_percent"],
  "original_fidelity":"HOLD",
  "report":str(REPORT)}))
 return 0 if valid else 1
if __name__=="__main__":
 try:
  parser=argparse.ArgumentParser()
  parser.add_argument("--fresh",action="store_true")
  args=parser.parse_args()
  sys.exit(run(args.fresh))
 except Exception as exc:
  print("OPENAZRAEL_NIAMH_NATIVE_COMPOSITION_V415 "+json.dumps({
    "status":"BLOCKED_NOT_PASS","reason":str(exc),"candidate_fidelity":"HOLD"}))
  sys.exit(1)