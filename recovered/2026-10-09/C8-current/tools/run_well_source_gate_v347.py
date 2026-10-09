#!/usr/bin/env python3
"""Fail-closed LOCAL C8 source gate: regenerate ignored IR before tests.
Never use on source-safe CI without an authorized original ATDEMO corpus.
"""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDERS=("build_well_source_actions_v358.py",
          "build_well_condition_gates_v362.py",
          "build_well_interaction_source_v363.py")
TESTS=("test_well_actions_v317.py","test_well_source_contract_v346.py",
       "test_well_queue_lifecycle_v348.py","test_well_axis_contract_v361.py",
       "test_well_condition_dispatch_v362.py","test_well_interaction_source_v363.py","test_well_state_opcode_v365.py","test_well_callback_opcode_v366.py","test_well_plaque_order_v368.py")
def execute(name,role):
 try:
  proc=subprocess.run([sys.executable,str(ROOT/"tools"/name)],cwd=ROOT,text=True,
             encoding="utf8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
  return {"name":name,"role":role,"exit_code":proc.returncode,
          "output_tail":proc.stdout[-2500:]}
 except subprocess.TimeoutExpired:
  return {"name":name,"role":role,"exit_code":124,
          "output_tail":"TIMEOUT_90_SECONDS"}
def main():
 generated=[];tested=[]
 for name in BUILDERS:
  result=execute(name,"generator")
  generated.append(result)
  if result["exit_code"]!=0:break
 if len(generated)==len(BUILDERS) and all(r["exit_code"]==0 for r in generated):
  for name in TESTS:
   result=execute(name,"test")
   tested.append(result)
   if result["exit_code"]!=0:break
 source_ok=(len(generated)==len(BUILDERS) and len(tested)==len(TESTS)
            and all(r["exit_code"]==0 for r in generated+tested))
 status="STRUCTURAL_PASS_FIDELITY_HOLD" if source_ok else "BLOCKED_OR_FAILED_SOURCE_GATE"
 report={"schema":"openazrael.c8.well_source_gate.v347","status":status,
    "fidelity_promotion_allowed":False,"generators":generated,"results":tested,
    "requires_local_atdemo":True,"remaining":[
       "source_state_indices_to_gameplay_flags","opaque_WORLD_state_actions",
       "original_runtime_transform_replay","audio_timing","save_load_mid_action",
       "full_demo_fidelity"]}
 out=ROOT/".tmp/well_source_gate_v347.json"
 out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
 print(json.dumps({"status":status,"generators_passed":sum(r["exit_code"]==0 for r in generated),
                    "tests_passed":sum(r["exit_code"]==0 for r in tested),
                    "failed":[r["name"] for r in generated+tested if r["exit_code"]!=0],
                    "fidelity_promotion_allowed":False}))
 return 0 if source_ok else 1
if __name__=="__main__":sys.exit(main())