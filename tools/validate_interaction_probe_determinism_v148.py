#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_interaction_probe_determinism_contract_v148.json").read_text(encoding="utf-8"))
probe=(ROOT/"scripts/interaction_probe.gd").read_text(encoding="utf-8")
runner=(ROOT/"scripts/kg001_interaction_probe_determinism_runner_v148.gd").read_text(encoding="utf-8")
expected=["interaction_priority_desc","view_angle_asc","distance_asc","stable_path_asc"]
checks={
    "schema":contract.get("schema")=="openazrael.kg001.interaction_probe_determinism_contract" and contract.get("version")==148,
    "raycast_primary":contract.get("raycast_remains_primary") is True and "intersect_ray(q)" in probe and "if hit:" in probe,
    "selection_order":contract.get("selection_order")==expected,
    "priority_default":contract.get("explicit_priority_default")==0 and 'get_meta("interaction_priority", 0)' in probe,
    "deterministic_sort":all(token in probe for token in ("_select_overlap_candidate","_candidate_less","sort_custom","stable_path","angle_error","distance")),
    "fallback_uses_selector":"return _select_overlap_candidate(overlaps, from, direction)" in probe,
    "two_overlapping_areas":all(token in runner for token in ("OverlapLowerPriority","OverlapPreferred","overlaps_area")),
    "repeated_runs":contract.get("repeated_runtime_runs")==64 and "REPEATED_RUNS := 64" in runner,
    "production_path_repeated":"probe.current_interactive()" in runner and "repeated_runtime_selection_is_stable" in runner,
    "input_order_regression":"forward_order_prefers_explicit_priority" in runner and "reverse_order_prefers_explicit_priority" in runner,
    "angle_tiebreak_regression":"angle_tiebreak_forward" in runner and "angle_tiebreak_reverse" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
    "schema":"openazrael.kg001.interaction_probe_determinism_validation",
    "version":148,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
