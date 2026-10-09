#!/usr/bin/env python3
"""OpenAzrael C8 original framebuffer oracle with explicitly bounded pass scope."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
PY=Path(os.environ.get("OPENAZRAEL_PYTHON",sys.executable))
GODOT=Path(os.environ.get("OPENAZRAEL_GODOT_BIN",
 "F:/Remaster Framework/source/Godot/Godot_v4.7.2-stable_win64.exe"))
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS",
 "F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
OUT=ROOT/".tmp/original_vga_oracle_campaign_v378.json"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as s:
  for c in iter(lambda:s.read(1048576),b""):h.update(c)
 return h.hexdigest()
def run(name,cmd,expected_mark,limit=90,env=None,negative=False):
 started=time.monotonic()
 proc=subprocess.run([str(x) for x in cmd],cwd=ROOT,
    env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
    encoding="utf8",errors="replace",timeout=limit)
 observed=proc.stdout
 good=((proc.returncode!=0 if negative else proc.returncode==0)
       and expected_mark in observed)
 if name=="intro_main_viewport" and good:
  lines=[x.split("INTRO_MAIN_V312 ",1)[1] for x in observed.splitlines() if "INTRO_MAIN_V312 " in x]
  try:
   metadata=json.loads(lines[-1])
   good=(metadata.get("status")=="PASS" and metadata.get("failed")==0
     and metadata.get("checks",0)>=32 and metadata.get("captures",0)>=11)
  except (IndexError,ValueError,TypeError):
   good=False
 if name=="original_godot_5_views" and good:
  lines=[x.split("OPENAZRAEL_ORIGINAL_GODOT_V378 ",1)[1]
    for x in observed.splitlines() if "OPENAZRAEL_ORIGINAL_GODOT_V378 " in x]
  try:
   metadata=json.loads(lines[-1])
   good=(metadata.get("status")=="SCOPED_ORIGINAL_VS_GODOT_PIXEL_EXACT_PASS"
        and metadata.get("pixel_exact_capture_pairs")==5
        and metadata.get("total_exact_pixels")==1536000
        and metadata.get("candidate_fidelity")=="HOLD"
        and metadata.get("fidelity_promotion_allowed") is False)
  except (IndexError,ValueError,TypeError):
   good=False
 record={"name":name,"pass":good,"exit":proc.returncode,
    "duration_s":round(time.monotonic()-started,2),
    "log_tail":observed[-2500:]}
 print(json.dumps({"test":name,"pass":good,"exit":proc.returncode,
   "duration_s":record["duration_s"]}),flush=True)
 return record
def main():
 protected=("project.godot","export_presets.cfg")
 original_hash={p:sha(ROOT/p) for p in protected}
 tasks=[]
 env=os.environ.copy()
 env["OPENAZRAEL_CORPUS"]=str(CORPUS)
 bad_env=env.copy()
 bad_env["OPENAZRAEL_ORIGINAL_CAPTURES"]=str(ROOT/".tmp"/"DO_NOT_EXIST_VGA_ORACLE")
 jobs=[
  ("regen_assets",[PY,ROOT/"tools/build_intro_assets_v311.py",CORPUS,"--reuse-decoded"],"ASSETS_READY",90,env,False),
  ("godot_import",[GODOT,"--headless","--editor","--import","--path",ROOT],"Godot Engine",90,env,False),
  ("title_source_contract",[PY,ROOT/"tools/test_intro_title_dac_v378.py"],"OPENAZRAEL_C8_TITLE_DAC_V378",40,env,False),
  ("intro_runtime",[GODOT,"--headless","--path",ROOT,"res://scripts/validation/intro_runtime_test_v311.tscn"],"INTRO_RUNTIME_V311",60,env,False),
  ("intro_main_viewport",[GODOT,"--path",ROOT,"res://scripts/validation/intro_main_scene_test_v311.tscn"],"INTRO_MAIN_V312",90,env,False),
  ("intro_audio_video",[GODOT,"--path",ROOT,"res://scripts/validation/intro_av_test_v311.tscn"],"INTRO_AV_V311",60,env,False),
  ("negative_oracle_missing_capture",[PY,ROOT/"tools/validate_original_vga_visual_v377.py"],'"status": "BLOCKED_OR_FAIL"',40,bad_env,True),
  ("original_vga_5_frames",[PY,ROOT/"tools/validate_original_vga_visual_v377.py"],'"pixel_exact_source_frames": 5',45,env,False),
  ("original_godot_5_views",[PY,ROOT/"tools/validate_original_vs_godot_intro_v378.py"],'SCOPED_ORIGINAL_VS_GODOT_PIXEL_EXACT_PASS',45,env,False)
 ]
 for name,cmd,mark,limit,local_env,neg in jobs:
  try:res=run(name,cmd,mark,limit,local_env,neg)
  except Exception as exc:
   res={"name":name,"pass":False,"reason":str(exc)}
  tasks.append(res)
  if not res["pass"]:break
 changed=[p for p in protected if sha(ROOT/p)!=original_hash[p]]
 total=len(jobs)
 status="SCOPED_ORIGINAL_INTRO_FRAMEBUFFER_PASS_CANDIDATE_HOLD" if len(tasks)==total and all(t["pass"] for t in tasks) and not changed else "BLOCKED_OR_FAILED"
 result={"schema":"openazrael.c8.original_visual_oracle.v378",
   "status":status,"head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
   "authority_binary":"ATDEMO_R.EXE_IN_DOSBOXX",
   "scope":["original_source_frames_5_x_640x480","Godot_original_rendered_frame_pairs_5_x_640x480",
            "original_R1_savestate_and_8.27_s_gameplay_video_verified"],
   "unverified":["original_R7_camera_replay","motion_timing","full_intro_fades","audio_latency","candidate_release_safety"],
   "candidate_fidelity":"HOLD",
   "protected_config_changed":changed,"tests":tasks}
 OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
 print(json.dumps({"summary":status,"passed":sum(bool(t["pass"]) for t in tasks),
                   "total":total,"protected_changed":changed,"report":str(OUT)}),flush=True)
 return 0 if status.startswith("SCOPED_ORIGINAL_INTRO") else 1
if __name__=="__main__":sys.exit(main())