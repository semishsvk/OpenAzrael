#!/usr/bin/env python3
"""Source-original-vs-production-camera R1/R7 bounded reconstruction regression.

Native DOSBox-X original source images and genuine Godot render captures must
both exist. This gate cannot substitute an inferred camera, source GLB
textures, or RDC frame. It is structural visual registration, not fidelity PASS.
"""
from pathlib import Path
from PIL import Image,ImageFilter
import hashlib,json,numpy as np,os,subprocess,sys,time,argparse
ROOT=Path(__file__).resolve().parents[1]
CAP=Path(os.environ.get("OPENAZRAEL_ORIGINAL_CAPTURE_ROOT",
 "F:/OpenRemaster/captures/OpenAzrael_C8_20261009"))
GODOT=Path(os.environ.get("OPENAZRAEL_GODOT_BIN",
 "F:/Remaster Framework/source/Godot/Godot_v4.7.2-stable_win64.exe"))
TEMPLATES={
 "R1":(CAP/"original_state_reload_v374"/"r_000.raw1.png",ROOT/".tmp/original_player_camera_v410_R1.png"),
 "R7":(CAP/"original_niamh_visible_v397"/"r_003.raw1.png",ROOT/".tmp/original_player_camera_v410_R7_BACKGROUND.png")}
EXPECTED_ORIGINAL={
 # filled against actual SHA-256 original native source before gate closure
}
THRESHOLDS={"R1":{"luma_ncc":.94,"edge_ncc":.84},
            "R7":{"luma_ncc":.95,"edge_ncc":.82}}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def features(im):
 a=np.asarray(im.convert("RGB"),dtype=np.float32)
 gray=.299*a[:,:,0]+.587*a[:,:,1]+.114*a[:,:,2]
 blur=np.asarray(Image.fromarray(np.uint8(gray)).filter(ImageFilter.GaussianBlur(1.6)),dtype=np.float32)
 gy,gx=np.gradient(blur)
 return gray,blur,np.sqrt(gx*gx+gy*gy)
def compare(room,source,dest,flip=False,scaled=False):
 a=Image.open(source).convert("RGB")
 b=Image.open(dest).convert("RGB")
 if a.size!=(640,480) or b.size!=(640,480):raise ValueError("expected original and Godot 640x480")
 a=a.crop((44,50,596,330))
 b=b.resize((552,280),Image.Resampling.BILINEAR) if scaled else b.crop((44,50,596,330))
 if flip:b=b.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 mask=np.ones((280,552),dtype=bool)
 mask[:5,:]=False;mask[-4:,:]=False;mask[:,:5]=False;mask[:,-5:]=False
 if room=="R1":
  mask[:220,375:]=False
 elif room=="R7":
  mask[35:265,195:302]=False
  mask[25:85,445:]=False
 else:raise ValueError("unknown room")
 u=features(a);v=features(b)
 def ncc(i):
  x=u[i][mask];y=v[i][mask]
  if x.std()<.0001 or y.std()<.0001:return None
  return float(np.corrcoef(x,y)[0,1])
 return {"luma_ncc":round(ncc(1),5),
         "edge_ncc":round(ncc(2),5),
         "luma_mae":round(float(np.abs(u[0]-v[0])[mask].mean()),4),
         "compared_pixels":int(mask.sum())}
def good(room,metrics):
 return all(metrics[k] >= threshold for k,threshold in THRESHOLDS[room].items())
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--fresh",action="store_true")
 a=ap.parse_args()
 started=time.monotonic()
 for room,(source,image) in TEMPLATES.items():
  if not source.is_file():raise FileNotFoundError("no original DOSBox-X native capture "+str(source))
  if room in EXPECTED_ORIGINAL and sha(source)!=EXPECTED_ORIGINAL[room]:
   raise ValueError("original source screenshot SHA changed")
 if a.fresh:
  env=os.environ.copy()
  env["OPENAZRAEL_SKIP_INTRO"]="1"
  p=subprocess.run([str(GODOT),"--path",str(ROOT),
    "--script","res://scripts/validation/production_original_camera_probe_v410.gd"],
    cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
    text=True,encoding="utf8",errors="replace",timeout=60)
  if p.returncode or '"status":"PASS"' not in p.stdout:
   raise RuntimeError("Godot actual capture failed: "+p.stdout[-1500:])
 evidence=ROOT/".tmp/production_camera_original_ram_v410.json"
 if not evidence.is_file():raise RuntimeError("no Godot render identity manifest")
 report=json.loads(evidence.read_text(encoding="utf8"))
 if report.get("status")!="PASS" or report.get("checks")!=17:
  raise RuntimeError("Godot source player camera report not PASS")
 cases=[]
 for room,(source,generated) in TEMPLATES.items():
  if not generated.is_file():raise FileNotFoundError("Godot rendered capture missing: "+str(generated))
  metrics=compare(room,source,generated)
  flipped=compare(room,source,generated,flip=True)
  scaled=compare(room,source,generated,scaled=True)
  base_pass=good(room,metrics)
  negative_flip=(not good(room,flipped))
  negative_scale=(not good(room,scaled))
  cases.append({"room":room,"native_original_sha256":sha(source),
     "actual_godot_png_sha256":sha(generated),
     "measured":metrics,"flipped_control":flipped,"scaled_control":scaled,
     "baseline_registration_pass":base_pass,
     "negative_flip_detects_failure":negative_flip,
     "negative_wrong_crop_detects_failure":negative_scale})
 passed=all(c["baseline_registration_pass"] and c["negative_flip_detects_failure"]
            and c["negative_wrong_crop_detects_failure"] for c in cases)
 status="TWO_ROOM_PRODUCTION_CAMERA_REGISTRATION_PASS_ACTOR_FIDELITY_HOLD" if passed else "FAIL"
 out={"schema":"openazrael.c8.camera_r1_r7_native_replay.v410",
  "status":status,"real_godot_camera":"Player/Camera3D frustum, parity/reflection preserved",
  "native_original_3d_crop":[44,50,552,280],
  "native_source":"DOSBOX_X_REAL_R_EXE_FRAMES",
  "cases":cases,"duration_seconds":round(time.monotonic()-started,2),
  "negative_controls":"MIRROR_AND_WRONG_SCALE_MUST_BOTH_FAIL",
  "NiAMH_MASK_R7":"actor central zone excluded from environmental comparison",
  "NIAMH_fidelity":"HOLD_ACTOR_MATERIAL_POSITION_AND_TIMING",
  "production_code_changed":False,
  "candidate_fidelity":"HOLD"}
 path=ROOT/".tmp/original_vs_production_camera_gate_v410.json"
 path.write_text(json.dumps(out,indent=2)+"\n",encoding="utf8")
 print("ORIGINAL_PRODUCTION_CAMERA_V410 "+json.dumps({
   "status":status,"cases":cases,"report":str(path)}))
 return 0 if passed else 1
if __name__=="__main__":
 try:sys.exit(main())
 except Exception as e:
  print("ORIGINAL_PRODUCTION_CAMERA_V410 "+json.dumps({"status":"BLOCKED","error":str(e)}))
  sys.exit(1)