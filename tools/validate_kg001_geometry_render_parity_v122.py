#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_geometry_render_parity_runner_v122.gd").read_text(encoding="utf-8")
contract = json.loads(
    (ROOT / "data/tests/kg001_geometry_render_parity_contract_v122.json").read_text(encoding="utf-8")
)

assets = contract.get("expected_assets", {})
checks = {
    "strict_geometry_policy": (
        contract.get("policy", {}).get("source_derived_only") is True
        and contract.get("policy", {}).get("complete_room_required") is True
        and contract.get("policy", {}).get("partial_import_forbidden") is True
        and contract.get("policy", {}).get("invented_or_approximate_geometry_forbidden") is True
        and contract.get("policy", {}).get("missing_geometry_action") == "BLOCKED_MISSING_SOURCE_GEOMETRY"
        and contract.get("policy", {}).get("geometry_defect_severity") == "CRITICAL"
    ),
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.geometry_render_parity_contract"
        and contract.get("version") == 122
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
        and contract.get("candidate_target") == "KG-001 Candidate 4"
    ),
    "all_demo_rooms": contract.get("scope") == ["R1", "R7", "R8"],
    "expected_counts": (
        assets.get("R1", {}).get("mesh_instances") == 69
        and assets.get("R1", {}).get("triangles") == 593
        and assets.get("R7", {}).get("mesh_instances") == 48
        and assets.get("R7", {}).get("triangles") == 689
        and assets.get("R8", {}).get("mesh_instances") == 87
        and assets.get("R8", {}).get("triangles") == 1050
    ),
    "r1_rock_required": (
        "save__mesh" in assets.get("R1", {}).get("critical_visible_meshes", [])
        and "ROCKFACE1" in json.dumps(assets.get("R1", {}))
        and "save__mesh" in runner
    ),
    "direct_import_audit": all(token in runner for token in (
        "_audit_direct",
        "_scene_geometry_summary",
        "_mesh_triangle_count",
        "ResourceLoader.exists",
        "packed.instantiate()",
    )),
    "runtime_room_manager_audit": all(token in runner for token in (
        "_audit_runtime",
        'scene.get_node_or_null("RoomManager")',
        "manager.load_room(room_id, false)",
        "manager.current_room",
    )),
    "no_stale_generated_hash_pin": all(
        "sha256" not in assets.get(room, {}) and "bytes" not in assets.get(room, {})
        for room in ("R1", "R7", "R8")
    ),
    "critical_visibility_check": all(token in runner for token in (
        "critical_visible",
        "_runtime_visible_",
        "is_visible_in_tree()",
    )),
    "no_substitute_geometry": all(token not in runner for token in (
        "MeshInstance3D.new()",
        "ArrayMesh.new()",
        "SurfaceTool.new()",
        "BoxMesh.new()",
        "PlaneMesh.new()",
    )),
    "result_marker": (
        "OPENAZRAEL_KG001_GEOMETRY_RENDER_PARITY_V122" in runner
        and '"version": 122' in runner
    ),
    "runtime_boundary": "asset-backed Godot v122 PASS" in contract.get("evidence_boundary", ""),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.geometry_render_parity_contract_validation",
    "version": 122,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "NOT_EXECUTED",
    "checks": checks,
    "failed": failed,
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
