#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

contract = json.loads(read("data/tests/kg001_candidate3_pppv_integration_contract.json"))
acceptance = json.loads(read("data/kg001_acceptance_contract.json"))
preflight = read("tools/run_candidate3_preflight.py")
pppv_runner = read("tools/run_candidate3_pppv_v2.py")
candidate_runner = read("tools/run_kg001_candidate_v112.py")
gate_manifest = read("tools/kg001_gate_manifest.py")
status = read("tools/kg001_status_v112.py")
room_manager = read("scripts/room_manager.gd")
r1_runner = read("scripts/kg001_r1_route_runner_v119.gd")
collision_runner = read("scripts/kg001_collision_parity_runner_v120.gd")
surface_runner = read("scripts/kg001_surface_collision_runner_v121.gd")
physical_runner = read("scripts/kg001_physical_traversal_runner_v117.gd")
transition_adapter = read("tools/openazrael_adapters/transition_pppv.py")

gates = {row.get("id"): row for row in acceptance.get("gates", []) if isinstance(row, dict)}

checks = {
    "contract_identity": (
        contract.get("schema") == "openazrael.kg001.candidate3_pppv_integration_contract"
        and contract.get("version") == 1
        and contract.get("candidate") == "KG-001 Candidate 3"
    ),
    "candidate3_runtime_authority_preserved": (
        '"r1_route_v119"' in gate_manifest
        and '"collision_v120"' in gate_manifest
        and "R1/Object02" in room_manager
        and "Collision_Object02" in r1_runner
        and "R1_Object02_not_exempt" in collision_runner
        and "OPENAZRAEL_KG001_SURFACE_COLLISION_V121" in surface_runner
    ),
    "candidate4_all_stair_directions_covered": all(token in physical_runner for token in (
        '"step011__mesh"',
        '"stairs__STAIR2"',
        "_up_progress",
        "_up_height",
        "_up_no_fall_through",
        "_down_progress",
        "_down_height",
        "_down_no_fall_through",
    )),
    "candidate4_all_room_transitions_authored": all(token in transition_adapter for token in (
        '"openazrael.transition.r1_to_r7"',
        '"openazrael.transition.r7_to_r1"',
        '"openazrael.transition.r1_to_r8"',
        '"openazrael.transition.r8_to_r1"',
        '"teleport_allowed_during_action": False',
        '"verify_destination_spawn": True',
        '"critical_if_transition_broken": True',
    )),
    "pppv_runner_isolated": (
        'TMP=ROOT/".tmp/kg001_pppv_v2"' in pppv_runner
        and "run_pppv_scenario_suite" in pppv_runner
        and "run_full_pppv" in pppv_runner
        and "pppv_runtime_guard.gd" not in pppv_runner
    ),
    "preflight_requires_pppv": (
        "PPPV_REQUIRED_EVIDENCE" in preflight
        and "PPPV_V2_RUNTIME_FAILED" in preflight
        and "PPPV_V2_EVIDENCE_MISSING" in preflight
        and "PPPV_V2_INVARIANT_FAILED" in preflight
        and all(name in gate_manifest for name in (
            "scenario_suite",
            "scenario_suite_integrity",
            "playthrough_evaluation",
            "determinism",
            "determinism_integrity",
        ))
    ),
    "source_gate_includes_framework": (
        "tools.remaster_framework.cli" in gate_manifest
        and "tools/remaster_framework/tests" in gate_manifest
        and "runtime_capabilities" in gate_manifest
    ),
    "acceptance_policy_requires_pppv": (
        acceptance.get("release_policy", {}).get("candidate3_pppv_v2_required") is True
        and acceptance.get("release_policy", {}).get("broken_required_room_transition_is_critical") is True
        and gates.get("G08", {}).get("minimum_identical_runs") == 2
        and "pppv" in json.dumps(gates.get("G04", {})).lower()
        and "pppv" in json.dumps(gates.get("G05", {})).lower()
        and "pppv" in json.dumps(gates.get("G08", {})).lower()
        and "pppv" in json.dumps(gates.get("G09", {})).lower()
    ),
    "status_gates_require_pppv": all(token in status for token in (
        "pppv_suite_pass",
        "pppv_suite_integrity_pass",
        "pppv_playthrough_pass",
        "pppv_determinism_pass",
        "pppv_determinism_integrity_pass",
        '"G04"',
        '"G05"',
        '"G08"',
        '"G09"',
    )),
    "known_good_still_fail_closed": (
        "final_tag_allowed" in status
        and "known_release_blockers" in status
        and "demo-known-good-001" in status
    ),
}

failed = [name for name, ok in checks.items() if not ok]
print("OpenAzrael Candidate 3 + PPPV v2 integration contract:", "PASS" if not failed else "FAIL")
for name, ok in checks.items():
    print(f" - {name}: {'PASS' if ok else 'FAIL'}")
sys.exit(1 if failed else 0)
