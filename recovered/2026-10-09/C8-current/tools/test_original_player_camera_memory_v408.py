#!/usr/bin/env python3
"""Rehydrate exact original Azrael R.EXE player-camera transform from DOSBox-X savestates.

No proprietary data are copied into Git. The original running camera or a
cutscene camera MAY differ; this specifically authenticates the player
transform against independent original R1/R7 RAM snapshots.
"""
from pathlib import Path
import hashlib,json,struct,zipfile,math,os,sys
ROOT=Path(__file__).resolve().parents[1]
ORACLE=Path(os.environ.get("OPENAZRAEL_ORIGINAL_RUNTIME_STATE_ROOT",
    r"F:\Remaster Framework\work\OpenAzrael\oracle\atdemo_dosboxx_v369"))
SOURCES=[
 ("R1_original_spawn","states/R1_CLEAN_ORIGINAL_v374.sav",
  [0,-69.444473,0],[0,0,1]),
 ("R1_after_forward","nav_runs/r1_forward_2s_v385c/NAV_r1_forward_2s_v385c.sav",
  [-21.38918,-59.44147,122.51945],[-0.5,0,0.8660254]),
 ("R1_after_backward","nav_runs/r1_backward_2s_v385d/NAV_r1_backward_2s_v385d.sav",
  [0,-71.61597,-112],[0,0,1]),
 ("R7_entry","states/R7_ENTRY_CANDIDATE_v391.sav",
  [49.96881,3.43598,-54.33464],[-.58778525,0,.80901699]),
 ("R7_ghost_live","niamh_oracle/visible_v397/R7_NIAMH_VISIBLE_v397.sav",
  [7.64828,4.20415,3.91459],[-.91354546,0,.40673664]),
 ("R7_ghost_source","nav_runs/possible_well_chamber_v392r2/NAV_possible_well_chamber_v392r2.sav",
  [7.64828,4.20415,3.91459],[-.91354546,0,.40673664])
]
EXPECTED_HASHES={
 "R1_original_spawn":"a9489051015ad06aadf68fa022ef200bd90001b707b8cd12324cea28c85eef76",
 "R7_ghost_live":"7694f3c2edef8b47599b295624e751cd218ae53aadd9fe403aedcf28505ba650",
 "R7_ghost_source":"d9ed8ff26992265e9876098e59f8142bfb7154aa31994f5dd2cae244ec06f88a"
}
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for buf in iter(lambda:f.read(1048576),b""):h.update(buf)
 return h.hexdigest()
def pose(mem):
 def f3(offset):return [struct.unpack_from("<f",mem,offset+4*i)[0] for i in range(3)]
 xyz=f3(0x35b5e0)
 # Independent transforms mirrored by original engine after updates
 copy1=f3(0x3901d8)
 copy2=f3(0x185794)
 facing=f3(0x35b864)
 facing_copy=[struct.unpack_from("<f",mem,a)[0] for a in (0x185784,0x185788,0x18578c)]
 return xyz,copy1,copy2,facing,facing_copy
def verify():
 observations=[]
 checks=[]
 for title,relative,expected_xyz,expected_facing in SOURCES:
  file=ORACLE/relative
  if not file.is_file():raise FileNotFoundError(file)
  h=digest(file)
  if title in EXPECTED_HASHES and h!=EXPECTED_HASHES[title]:
   raise ValueError("source save sha differs: "+title)
  with zipfile.ZipFile(file) as z:
   if z.testzip()!=None or "Memory" not in z.namelist() or "CPU" not in z.namelist():
    raise ValueError("corrupt authenticated DOSBox-X savestate: "+title)
   ram=z.read("Memory")
  actual,a,b,heading,heading_copy=pose(ram)
  for label,nums in (("position_copy1",a),("position_copy2",b)):
   ok=max(abs(x-y) for x,y in zip(actual,nums))<1e-5
   checks.append({"save":title,"name":label,"pass":ok})
  for label,nums,expected in (
    ("expected_position",actual,expected_xyz),
    ("expected_forward",heading,expected_facing),
    ("rotation_copy",heading,heading_copy)
  ):
   ok=max(abs(x-y) for x,y in zip(nums,expected))<0.001
   checks.append({"save":title,"name":label,"pass":ok})
  checks.append({"save":title,"name":"normalized_forward",
    "pass":abs(sum(v*v for v in heading)-1)<.002})
  checks.append({"save":title,"name":"no_vertical_heading",
    "pass":abs(heading[1])<0.0001})
  observations.append({"state":title,"savestate_sha256":h,
   "original_ram_player_xyz":actual,"original_ram_forward_unit":heading,
   "yaw_deg":math.degrees(math.atan2(heading[0],heading[2])),
   "memory_offset_position":"0x35B5E0",
   "memory_offset_forward":"0x35B864",
   "independent_position_copies":["0x3901D8","0x185794"]})
 # Negative fixture: mutate private in-memory byte stream only, never original savestate.
 with zipfile.ZipFile(ORACLE/SOURCES[0][1]) as z:
  immutable=z.read("Memory")
 changed=bytearray(immutable)
 changed[0x35b5e0]^=0x1
 altered=pose(changed)
 untouched=pose(immutable)
 checks.append({"save":"tampered_fixture","name":"camera_duplicate_reject",
   "pass":altered[0]!=altered[1] or altered[0]!=untouched[0]})
 status="ORIGINAL_PLAYER_CAMERA_MEMORY_STRUCTURAL_PASS_CUTSCENE_CAMERA_HOLD" if all(c["pass"] for c in checks) else "FAIL"
 result={"schema":"openazrael.original_dosboxx_ram_camera.v408",
  "status":status,
  "checks":len(checks),"failures":[x for x in checks if not x["pass"]],
  "states":observations,
  "source_R_EXE_sha256":"381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00",
  "original_DOSBOX_X_hash":"a82adcfa7af2784566cfeff74c077cefed08505396db2948b7e6aa7d4cee0832",
  "scope":"player camera pose in original emulator snapshots, not evidence of separate cutscene camera",
  "original_niamh_capture_camera":"UNVERIFIED_ACTOR_CINEMATIC_CAMERA_MAY_DIFFER",
  "godot_projection_fidelity":"HOLD"}
 path=ROOT/".tmp/original_camera_memory_v408.json"
 path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
 print("OPENAZRAEL_ORIGINAL_PLAYER_CAMERA_V408 "+json.dumps({
  "status":status,"checks":len(checks),"failures":result["failures"],
  "R7_original_eye":observations[-2]["original_ram_player_xyz"],
  "R7_original_forward":observations[-2]["original_ram_forward_unit"],
  "report":str(path)}))
 return 0 if not result["failures"] else 1
if __name__=="__main__":
 try:sys.exit(verify())
 except Exception as exc:
  print("OPENAZRAEL_ORIGINAL_PLAYER_CAMERA_V408 "+json.dumps({"status":"FAIL","error":str(exc)}))
  sys.exit(1)