#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
policy = json.loads((ROOT / "data/source_geometry_policy.json").read_text(encoding="utf-8"))
parity = json.loads((ROOT / "data/tests/kg001_geometry_render_parity_contract_v122.json").read_text(encoding="utf-8"))
doc = (ROOT / "docs/SOURCE_GEOMETRY_FIDELITY.md").read_text(encoding="utf-8")

rules = policy.get("runtime_rules", {})
gate = policy.get("candidate_gate", {})
demo = policy.get("demo_expected", {})
assets = parity.get("expected_assets", {})

checks = {
    "policy_schema": (
        policy.get("schema") == "openazrael.source_geometry_policy"
        and policy.get("version") == 1
        and policy.get("status") == "NON_NEGOTIABLE"
        and policy.get("fail_closed") is True
    ),
    "source_only": rules.get("source_derived_only") is True,
    "complete_room_required": rules.get("complete_room_required") is True,
    "partial_forbidden": rules.get("partial_import_forbidden") is True,
    "invented_forbidden": rules.get("invented_geometry_forbidden") is True,
    "approximation_forbidden": rules.get("approximate_geometry_forbidden") is True,
    "ai_runtime_geometry_forbidden": rules.get("ai_generated_runtime_geometry_forbidden") is True,
    "procedural_substitute_forbidden": rules.get("procedural_substitute_geometry_forbidden") is True,
    "fail_closed_missing_source": rules.get("missing_source_action") == "BLOCKED_MISSING_SOURCE_GEOMETRY",
    "no_masking_replacement_floor": rules.get("replacement_floor_to_mask_missing_geometry_forbidden") is True,
    "compatibility_fixes_do_not_change_shape": rules.get("engine_compatibility_fixes_may_change_shape") is False,
    "state_variants_source_exact": rules.get("state_variants_require_original_authored_geometry") is True,
    "critical_release_gate": (
        gate.get("geometry_parity_required_for_every_included_room") is True
        and gate.get("geometry_defect_severity") == "CRITICAL"
        and gate.get("blocks_known_good") is True
        and gate.get("blocks_release") is True
    ),
    "demo_counts_bound_to_v122": all(
        demo.get(room, {}).get("mesh_instances") == assets.get(room, {}).get("mesh_instances")
        and demo.get(room, {}).get("triangles") == assets.get(room, {}).get("triangles")
        for room in ("R1", "R7", "R8")
    ),
    "r1_rock_bound": (
        demo.get("R1", {}).get("critical_visible_mesh") == "save__mesh"
        and "save__mesh" in assets.get("R1", {}).get("critical_visible_meshes", [])
    ),
    "doc_states_non_negotiable": (
        "NON-NEGOTIABLE / FAIL-CLOSED" in doc
        and "No architectural geometry may be invented" in doc
        and "Partial-room imports are release blockers" in doc
        and "BLOCKED_MISSING_SOURCE_GEOMETRY" in doc
    ),
}

failed = [name for name, ok in checks.items() if not ok]
result = {
    "schema": "openazrael.source_geometry_policy_validation",
    "version": 1,
    "status": "PASS" if not failed else "FAIL",
    "checks": checks,
    "failed": failed,
}
print(json.dumps(result, indent=2))
sys.exit(1 if failed else 0)
