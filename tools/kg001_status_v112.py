#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]

def load_optional(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

contract=json.loads((ROOT/"data/kg001_acceptance_contract.json").read_text(encoding="utf-8"))
context=json.loads((ROOT/"data/project_context.json").read_text(encoding="utf-8"))
v108=json.loads((ROOT/"data/tests/kg001_state_space_v108.json").read_text(encoding="utf-8"))
source=load_optional(ROOT/"data/tests/kg001_source_validation_v112.json")
r109=load_optional(ROOT/"data/tests/kg001_headless_runtime_v109.json")
r110=load_optional(ROOT/"data/tests/kg001_room_trigger_runtime_v110.json")
r111=load_optional(ROOT/"data/tests/kg001_full_demo_runtime_v111.json")
audio=load_optional(ROOT/"data/tests/kg001_audio_runtime_v116.json")
physical=load_optional(ROOT/"data/tests/kg001_physical_traversal_runtime_v117.json")
well_tongs=load_optional(ROOT/"data/tests/kg001_well_tongs_animation_runtime_v118.json")
fresh=load_optional(ROOT/"data/tests/kg001_fresh_checkout.json")
manual=load_optional(ROOT/"data/tests/kg001_manual_sanity.json")
manual_validation=load_optional(
    ROOT/"data/tests/kg001_manual_sanity_validation_v118.json"
)

def is_pass(obj):
    return isinstance(obj,dict) and obj.get("status")=="PASS"

source_pass=is_pass(source)
v109_pass=is_pass(r109)
v110_pass=is_pass(r110)
v111_pass=is_pass(r111)
audio_pass=is_pass(audio)
physical_pass=is_pass(physical)
well_tongs_pass=is_pass(well_tongs)
fresh_pass=is_pass(fresh)
manual_pass=(
    is_pass(manual)
    and is_pass(manual_validation)
    and manual.get("version")==2
    and manual_validation.get("version")==118
    and isinstance(fresh,dict)
    and manual.get("candidate_commit")==fresh.get("commit_sha")
    and manual_validation.get("candidate_commit")==fresh.get("commit_sha")
)

gates={
 "G00":{"name":"context_integrity","status":"PASS" if source_pass else "PENDING_RECORDED_SOURCE_VALIDATION"},
 "G01":{"name":"data_validation","status":"PASS" if source_pass else "PENDING_RECORDED_SOURCE_VALIDATION"},
 "G02":{"name":"unit_gameplay_logic","status":"PASS" if source_pass and v109_pass else "RUNTIME_PENDING"},
 "G03":{"name":"puzzle_state_space","status":"PASS" if source_pass and v108.get("status")=="PASS" else "PENDING"},
 "G04":{"name":"room_transition_and_physical_traversal","status":"PASS" if v110_pass and physical_pass else "RUNTIME_PENDING"},
 "G05":{"name":"trigger_semantics_and_recovered_interaction_effects","status":"PASS" if v110_pass and well_tongs_pass else "RUNTIME_PENDING"},
 "G06":{"name":"audio_event_stream","status":"PASS" if v109_pass and v111_pass and audio_pass else "RUNTIME_PENDING"},
 "G07":{"name":"save_load_state_hash","status":"PASS" if v109_pass else "RUNTIME_PENDING"},
 "G08":{"name":"synthetic_full_demo_playthrough","status":"PASS" if v111_pass else "RUNTIME_PENDING"},
 "G09":{"name":"fresh_checkout_build","status":"PASS" if fresh_pass else "PENDING"},
 "G10":{"name":"manual_sanity","status":"PASS" if manual_pass else "PENDING_MANUAL_USER"}
}
release_blockers=sorted([
    key for key,value in context.get("quality",{}).items()
    if key.startswith("kg001_release_blocked_by_") and value is True
])
defect_clear=not release_blockers
all_gates_pass=all(x["status"]=="PASS" for x in gates.values())
all_pass=all_gates_pass and defect_clear
failed=[]
for gid,obj in (
    ("source",source),
    ("v109",r109),
    ("v110",r110),
    ("v111",r111),
    ("audio_v116",audio),
    ("physical_v117",physical),
    ("well_tongs_v118",well_tongs),
    ("fresh",fresh),
    ("manual",manual),
    ("manual_validation_v118",manual_validation),
):
    if isinstance(obj,dict) and obj.get("status")=="FAIL":
        failed.append(gid)
out={
 "schema":"openazrael.kg001.gate_status",
 "version":112,
 "target_tag":contract["target_tag"],
 "overall_status":"PASS" if all_pass else ("FAIL" if failed else ("BLOCKED_KNOWN_BUGS" if release_blockers else "AWAITING_RUNTIME_OR_MANUAL")),
 "final_tag_allowed":all_pass,
 "failed_inputs":failed,
 "known_release_blockers":release_blockers,
 "manual_sanity_receipt_bound":manual_pass,
 "manual_sanity_candidate_commit":(
     manual.get("candidate_commit","")
     if isinstance(manual,dict) else ""
 ),
 "fresh_checkout_candidate_commit":(
     fresh.get("commit_sha","")
     if isinstance(fresh,dict) else ""
 ),
 "gates":gates,
 "release_boundary":"demo-known-good-001 is allowed only when every G00-G10 gate is literal PASS and no recorded KG-001 release blocker remains."
}
print(json.dumps(out,indent=2))
sys.exit(1 if failed else 0)
