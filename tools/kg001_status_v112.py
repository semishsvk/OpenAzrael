#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]

def load_optional(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

contract=json.loads((ROOT/"data/kg001_acceptance_contract.json").read_text(encoding="utf-8"))
v108=json.loads((ROOT/"data/tests/kg001_state_space_v108.json").read_text(encoding="utf-8"))
source=load_optional(ROOT/"data/tests/kg001_source_validation_v112.json")
r109=load_optional(ROOT/"data/tests/kg001_headless_runtime_v109.json")
r110=load_optional(ROOT/"data/tests/kg001_room_trigger_runtime_v110.json")
r111=load_optional(ROOT/"data/tests/kg001_full_demo_runtime_v111.json")
pppv_suite=load_optional(ROOT/"data/tests/kg001_pppv_scenario_suite.json")
pppv_suite_integrity=load_optional(ROOT/"data/tests/pppv_scenario_suite_integrity.json")
pppv_playthrough=load_optional(ROOT/"data/tests/kg001_pppv_playthrough_evaluation.json")
pppv_determinism=load_optional(ROOT/"data/tests/kg001_pppv_determinism.json")
pppv_determinism_integrity=load_optional(ROOT/"data/tests/pppv_determinism_integrity.json")
fresh=load_optional(ROOT/"data/tests/kg001_fresh_checkout.json")
manual=load_optional(ROOT/"data/tests/kg001_manual_sanity.json")

def is_pass(obj):
    return isinstance(obj,dict) and obj.get("status")=="PASS"

source_pass=is_pass(source)
v109_pass=is_pass(r109)
v110_pass=is_pass(r110)
v111_pass=is_pass(r111)
pppv_suite_pass=is_pass(pppv_suite)
pppv_suite_integrity_pass=is_pass(pppv_suite_integrity)
pppv_playthrough_pass=is_pass(pppv_playthrough)
pppv_determinism_pass=is_pass(pppv_determinism)
pppv_determinism_integrity_pass=is_pass(pppv_determinism_integrity)
fresh_pass=is_pass(fresh)
manual_pass=is_pass(manual)

gates={
 "G00":{"name":"context_integrity","status":"PASS" if source_pass else "PENDING_RECORDED_SOURCE_VALIDATION"},
 "G01":{"name":"data_validation","status":"PASS" if source_pass else "PENDING_RECORDED_SOURCE_VALIDATION"},
 "G02":{"name":"unit_gameplay_logic","status":"PASS" if source_pass and v109_pass else "RUNTIME_PENDING"},
 "G03":{"name":"puzzle_state_space","status":"PASS" if source_pass and v108.get("status")=="PASS" else "PENDING"},
 "G04":{"name":"room_transition_state","status":"PASS" if v110_pass and pppv_suite_pass and pppv_suite_integrity_pass else ("FAIL" if any(isinstance(x,dict) and x.get("status")=="FAIL" for x in (r110,pppv_suite,pppv_suite_integrity)) else "RUNTIME_PENDING")},
 "G05":{"name":"trigger_semantics","status":"PASS" if v110_pass and pppv_suite_pass and pppv_suite_integrity_pass else ("FAIL" if any(isinstance(x,dict) and x.get("status")=="FAIL" for x in (r110,pppv_suite,pppv_suite_integrity)) else "RUNTIME_PENDING")},
 "G06":{"name":"audio_event_stream","status":"PASS" if v109_pass and v111_pass else "RUNTIME_PENDING"},
 "G07":{"name":"save_load_state_hash","status":"PASS" if v109_pass else "RUNTIME_PENDING"},
 "G08":{"name":"synthetic_full_demo_playthrough","status":"PASS" if v111_pass and pppv_playthrough_pass and pppv_determinism_pass and pppv_determinism_integrity_pass else ("FAIL" if any(isinstance(x,dict) and x.get("status")=="FAIL" for x in (r111,pppv_playthrough,pppv_determinism,pppv_determinism_integrity)) else "RUNTIME_PENDING")},
 "G09":{"name":"fresh_checkout_build","status":"PASS" if fresh_pass and pppv_suite_integrity_pass and pppv_determinism_pass and pppv_determinism_integrity_pass else ("FAIL" if any(isinstance(x,dict) and x.get("status")=="FAIL" for x in (fresh,pppv_suite_integrity,pppv_determinism,pppv_determinism_integrity)) else "PENDING")},
 "G10":{"name":"manual_sanity","status":"PASS" if manual_pass else "PENDING_MANUAL_USER"}
}
all_pass=all(x["status"]=="PASS" for x in gates.values())
failed=[]
for gid,obj in (("source",source),("v109",r109),("v110",r110),("v111",r111),("pppv_suite",pppv_suite),("pppv_suite_integrity",pppv_suite_integrity),("pppv_playthrough",pppv_playthrough),("pppv_determinism",pppv_determinism),("pppv_determinism_integrity",pppv_determinism_integrity),("fresh",fresh),("manual",manual)):
    if isinstance(obj,dict) and obj.get("status")=="FAIL":
        failed.append(gid)
out={
 "schema":"openazrael.kg001.gate_status",
 "version":112,
 "target_tag":contract["target_tag"],
 "overall_status":"PASS" if all_pass else ("FAIL" if failed else "AWAITING_RUNTIME_OR_MANUAL"),
 "final_tag_allowed":all_pass,
 "failed_inputs":failed,
 "gates":gates,
 "release_boundary":"demo-known-good-001 is allowed only when every G00-G10 gate is literal PASS; G04/G05 require current-bundle PPPV suite integrity; G08 requires two matching guarded chained PPPV runs with independent determinism integrity; G09 requires both evidence-integrity checks."
}
print(json.dumps(out,indent=2))
sys.exit(1 if failed else 0)
