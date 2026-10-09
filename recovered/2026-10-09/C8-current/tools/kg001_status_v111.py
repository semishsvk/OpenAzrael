#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/kg001_acceptance_contract.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

contract=load(CONTRACT)
v108=load(ROOT/"data/tests/kg001_state_space_v108.json")
v109=load(ROOT/"data/tests/kg001_headless_contract_v109.json")
v110=load(ROOT/"data/tests/kg001_room_trigger_contract_v110.json")
v111=load(ROOT/"data/tests/kg001_full_demo_contract_v111.json")

runtime109=ROOT/"data/tests/kg001_headless_runtime_v109.json"
runtime110=ROOT/"data/tests/kg001_room_trigger_runtime_v110.json"
runtime111=ROOT/"data/tests/kg001_full_demo_runtime_v111.json"
runtime117=ROOT/"data/tests/kg001_physical_traversal_runtime_v117.json"
fresh=ROOT/"data/tests/kg001_fresh_checkout.json"
manual=ROOT/"data/tests/kg001_manual_sanity.json"

def runtime_status(path):
    if not path.is_file():
        return "RUNTIME_PENDING"
    data=load(path)
    return "PASS" if data.get("status")=="PASS" else "FAIL"

status109=runtime_status(runtime109)
status110=runtime_status(runtime110)
status111=runtime_status(runtime111)
status117=runtime_status(runtime117)

def combined_status(*values):
    if all(value=="PASS" for value in values):
        return "PASS"
    if "FAIL" in values:
        return "FAIL"
    return "SOURCE_CONTRACT_PASS_RUNTIME_PENDING"

gates={
 "G00":{"name":"context_integrity","status":"READY_VALIDATOR_PRESENT","evidence":["tools/validate_project_context.py"]},
 "G01":{"name":"data_validation","status":"READY_VALIDATOR_PRESENT","evidence":["tools/validate_demo_runtime_ir.py","tools/audit_gameplay_event_graph_v87.py"]},
 "G02":{"name":"unit_gameplay_logic","status":"SOURCE_MODEL_PASS_RUNTIME_PENDING" if v108.get("status")=="PASS" else "FAIL","evidence":["data/tests/kg001_state_space_v108.json","scripts/kg001_headless_runner_v109.gd"]},
 "G03":{"name":"puzzle_state_space","status":"SOURCE_MODEL_PASS","evidence":["data/tests/kg001_state_space_v108.json"]},
 "G04":{"name":"room_transition_and_physical_traversal","status":combined_status(status110,status117),"evidence":["data/tests/kg001_room_trigger_contract_v110.json","scripts/kg001_room_trigger_runner_v110.gd","tools/validate_kg001_physical_traversal_v117.py","scripts/kg001_physical_traversal_runner_v117.gd","data/tests/kg001_physical_traversal_runtime_v117.json"]},
 "G05":{"name":"trigger_semantics","status":"PASS" if status110=="PASS" else ("FAIL" if status110=="FAIL" else "SOURCE_CONTRACT_PASS_RUNTIME_PENDING"),"evidence":["data/tests/kg001_room_trigger_contract_v110.json","scripts/kg001_room_trigger_runner_v110.gd"]},
 "G06":{"name":"audio_event_stream","status":"PASS" if status109=="PASS" and status111=="PASS" else ("FAIL" if "FAIL" in (status109,status111) else "SOURCE_CONTRACT_PASS_RUNTIME_PENDING"),"evidence":["data/tests/kg001_headless_contract_v109.json","data/tests/kg001_full_demo_contract_v111.json"]},
 "G07":{"name":"save_load_state_hash","status":"PASS" if status109=="PASS" else ("FAIL" if status109=="FAIL" else "SOURCE_CONTRACT_PASS_RUNTIME_PENDING"),"evidence":["scripts/kg001_headless_runner_v109.gd","data/tests/kg001_headless_contract_v109.json"]},
 "G08":{"name":"synthetic_full_demo_playthrough","status":"PASS" if status111=="PASS" else ("FAIL" if status111=="FAIL" else "SOURCE_CONTRACT_PASS_RUNTIME_PENDING"),"evidence":["scripts/kg001_full_demo_runner_v111.gd","data/tests/kg001_full_demo_contract_v111.json"]},
 "G09":{"name":"fresh_checkout_build","status":"PASS" if fresh.is_file() and load(fresh).get("status")=="PASS" else "PENDING","evidence":["docs/BACKUP_VERSIONING_POLICY.md","docs/GIT_BASELINE.md"]},
 "G10":{"name":"manual_sanity","status":"PASS" if manual.is_file() and load(manual).get("status")=="PASS" else "PENDING","evidence":["docs/KG001_ACCEPTANCE_PLAN.md"]}
}

failed=[gid for gid,g in gates.items() if g["status"]=="FAIL"]
final_pass=all(g["status"]=="PASS" for g in gates.values())
out={
 "schema":"openazrael.kg001.gate_status",
 "version":111,
 "target_tag":contract["target_tag"],
 "overall_status":"PASS" if final_pass else ("FAIL" if failed else "PRE_RUNTIME_READY"),
 "final_tag_allowed":final_pass,
 "failed_gates":failed,
 "runtime_inputs":{"v109":status109,"v110":status110,"v111":status111,"v117_physical_traversal":status117},
 "gates":gates,
 "release_boundary":"Only literal PASS for all G00-G10 allows demo-known-good-001. SOURCE_* and READY_* are not release PASS."
}
print(json.dumps(out,indent=2))
sys.exit(1 if failed else 0)
