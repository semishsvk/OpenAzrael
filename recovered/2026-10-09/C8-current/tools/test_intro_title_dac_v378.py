#!/usr/bin/env python3
"""Exact 6-bit VGA DAC title conversion regression, independent of emulator availability."""
from pathlib import Path
import hashlib,json,os,sys
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
TITLE_SHA="d0fb123f1cad349cdabfd8e3dce2950be4a6fdcd54316d3bb62e04ea751222a2"
RAW=ROOT/"assets/intro_v311/TITLE/frame_0000.png"
DISPLAY=ROOT/"assets/intro_v311/TITLE/frame_0000_vga6.png"
MANIFEST=ROOT/"data/runtime_generated/intro_movies_v311.json"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,reason):
 if not ok:raise AssertionError(reason)
def main():
 checks=[]
 def check(label,truth):
  require(truth,label)
  checks.append(label)
 check("canonical_source_sha",sha(CORPUS/"TITLE.PCX")==TITLE_SHA)
 with Image.open(CORPUS/"TITLE.PCX") as original:
  source=np.asarray(original.convert("RGB"),dtype=np.uint8)
 with Image.open(RAW) as raw:
  saved=np.asarray(raw.convert("RGB"),dtype=np.uint8)
 check("source_size_631x474",source.shape==(474,631,3))
 check("raw_source_rgb_preserved",bool(np.array_equal(source,saved)))
 with Image.open(DISPLAY) as rendered:
  display=np.asarray(rendered.convert("RGB"),dtype=np.uint8)
 a=source.astype(np.uint16)
 expected=np.asarray(((a>>2)<<2)|((a>>2)>>4),dtype=np.uint8)
 check("vga_dac6_exact",bool(np.array_equal(expected,display)))
 check("vga6_6bit_channels",bool(np.all((display&3)==((display>>6)&3))))
 check("raw_rgb_different",bool(np.any(source!=display)))
 check("round_trip_is_idempotent",bool(np.array_equal(((display.astype(np.uint16)>>2)<<2)|((display.astype(np.uint16)>>2)>>4),display)))
 data=json.loads(MANIFEST.read_text(encoding="utf8"))
 clip=data["clips"]["TITLE"]
 record=clip["sequence"][0]
 check("manifest_display_path",record["path"]=="res://assets/intro_v311/TITLE/frame_0000_vga6.png")
 check("manifest_source_raw",record["source_raw_path"]=="res://assets/intro_v311/TITLE/frame_0000.png")
 check("manifest_pixel_hash",record["rgb_sha256"]==hashlib.sha256(display.tobytes()).hexdigest())
 check("manifest_original_hash",record["source_raw_rgb_sha256"]==hashlib.sha256(source.tobytes()).hexdigest())
 check("display_dac_policy",record["display_dac_policy"]=="PCX_RGB8_TRUNCATE_TO_DAC6_THEN_BIT_REPLICATE")
 result={"schema":"openazrael.c8.title_dac_source_test.v378","status":"PASS","checks":len(checks),
   "scope":"pure source-backed title RGB conversion, does not prove original emulator fade/cadence",
   "source_sha256":TITLE_SHA,"generated_display_sha256":sha(DISPLAY),
   "fidelity_promotion_allowed":False}
 print("OPENAZRAEL_C8_TITLE_DAC_V378 "+json.dumps(result))
 return 0
if __name__=="__main__":
 try:sys.exit(main())
 except Exception as e:
  print("OPENAZRAEL_C8_TITLE_DAC_V378 "+json.dumps({"status":"FAIL","error":str(e)}))
  sys.exit(1)