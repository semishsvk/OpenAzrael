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
status = read("tools/kg001_status_v112.py")
room_manager = read("scripts/room_manager.gd")
r1_runner = read("scripts/kg001_r1_route_runner_v119.gd")
collision_runner = read("scripts/kg001_collision_parity_runner_v120.gd")

gates = {row.get("id"): row for row in acceptance.get("gates", []) if isinstance(row, dict)}

checks = {
    "contract_identity": (
        contract.get("schema") == "openazrael.kg001.candidate3_pppv_integration_contract"
        and contract.get("version") == 1
        and contract.get("candidate") == "KG-001 Candidate 3"
    ),
    "candidate3_runtime_authority_preserved": (
        '"r1_route_v119"' in candidate_runner
        and '"collision_v120"' in candidate_runner
        and "R1/Object02" in room_manager
        and "Collision_Object02" in r1_runner
        and "R1_Object02_not_exempt" in collision_runner
    ),
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
        and all(name in preflight for name in (
            "scenario_suite",
            "scenario_suite_integrity",
            "playthrough_evaluation",
            "determinism",
            "determinism_integrity",
        ))
    ),
    "source_gate_includes_framework": (
        "tools.remaster_framework.cli" in candidate_runner
        and "tools/remaster_framework/tests" in candidate_runner
        and "runtime_capabilities" in candidate_runner
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
