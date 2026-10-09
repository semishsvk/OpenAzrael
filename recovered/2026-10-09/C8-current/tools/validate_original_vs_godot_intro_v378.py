#!/usr/bin/env python3
"""Five exact R.EXE framebuffer vs rendered Godot viewport comparisons.

Original captures must originate from DOSBox-X native capture, not Remote Desktop Commander.
This contract authorizes only scoped MINDLOGO 0, INTRO 8/28/47, and TITLE 0 frame equivalence.
"""
from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
CAP=Path(os.environ.get("OPENAZRAEL_ORIGINAL_CAPTURES","F:/OpenRemaster/captures/OpenAzrael_C8_20261009"))
CONTRACT=ROOT/"data/tests/original_vga_visual_contract_v377.json"
GODOT_OUTPUT=ROOT/".tmp/intro_decode_v311"
PAIRS=(
 ("MINDLOGO",0,"main_mindscape_frame0.png","r_002.raw1.png"),
 ("INTRO",8,"main_ig_frame8.png","r_003.raw1.png"),
 ("INTRO",28,"main_ig_frame28.png","r_004.raw1.png"),
 ("INTRO",47,"main_ig_frame47.png","r_005.raw1.png"),
 ("TITLE",0,"source_title_before_poem.png","r_006.raw1.png")
)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def run():
 c=json.loads(CONTRACT.read_text(encoding="utf8"))
 report=json.loads((GODOT_OUTPUT/"godot_intro_main_tests.json").read_text(encoding="utf8"))
 require(report.get("status")=="PASS","rendered Godot intro/main test did not pass")
 require(not str(report.get("display","")).lower().startswith("headless"),"Godot source capture is headless")
 captures={r["name"]:r for r in report["captures"]}
 results=[]
 for clip,index,godot_filename,original_filename in PAIRS:
  key=godot_filename.removesuffix(".png")
  original=CAP/c["original_capture_dir_relative_to_capture_root"]/original_filename
  godot=GODOT_OUTPUT/godot_filename
  item=next((r for r in c["frames"] if r["clip"]==clip and r["index"]==index),None)
  require(item is not None and item["original"]==original_filename,"original capture mismatch: "+clip)
  require(original.is_file() and digest(original)==item["original_sha256"],"native oracle source differs from SHA pin "+clip)
  require(godot.is_file(),"Godot viewport screenshot missing: "+str(godot))
  evidence=captures.get(key)
  require(evidence is not None and evidence["pixel_exact"] and evidence["source_clip"]==clip and evidence["source_frame"]==index,"Godot capture reporter missing/evidence mismatch: "+key)
  require(evidence["origin"]=="Godot ViewportTexture","not a real Godot native framebuffer "+key)
  with Image.open(original) as ref,Image.open(godot) as new:
   require(ref.size==(640,480) and new.size==(640,480),"unexpected capture dimensions "+key)
   source_rgb=np.asarray(ref.convert("RGB"),dtype=np.uint8)
   actual_rgb=np.asarray(new.convert("RGB"),dtype=np.uint8)
  matching=int(np.all(source_rgb==actual_rgb,axis=2).sum())
  require(matching==307200,"Godot output differs from actual original renderer: "+key+" "+str(matching))
  results.append({"clip":clip,"frame_index":index,"godot_capture":godot_filename,
    "godot_sha256":digest(godot),"original_capture":original_filename,
    "original_sha256":digest(original),"matching_pixels":matching,
    "differing_pixels":0})
 return {
  "schema":"openazrael.c8.original_vs_godot_intro.v378",
  "status":"SCOPED_ORIGINAL_VS_GODOT_PIXEL_EXACT_PASS",
  "checks":len(results)*2+3,
  "images":results,
  "pixel_exact_capture_pairs":len(results),
  "total_exact_pixels":sum(x["matching_pixels"] for x in results),
  "original_hardware_emulation":"DOSBOX_X_NATIVE_ORIGINAL_R_EXE",
  "godot_runtime":"GODOT_4_7_2_RENDERED_VIEWPORT",
  "reproduction":"run main rendered intro test, then this validator",
  "remaining_fidelity_gates":["source_intro_frame_rate","fade_wallclock","intro_audio_latency","gameplay_camera","original_R7_runtime"],
  "candidate_fidelity":"HOLD",
  "fidelity_promotion_allowed":False}
def main():
 try:
  result=run()
 except Exception as error:
  result={"schema":"openazrael.c8.original_vs_godot_intro.v378","status":"BLOCKED_OR_FAIL",
      "reason":str(error),"fidelity_promotion_allowed":False}
 output=ROOT/".tmp/original_vs_godot_v378.json"
 output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
 print("OPENAZRAEL_ORIGINAL_GODOT_V378 "+json.dumps(result))
 return 0 if result["status"]=="SCOPED_ORIGINAL_VS_GODOT_PIXEL_EXACT_PASS" else 1
if __name__=="__main__":sys.exit(main())