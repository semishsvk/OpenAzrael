#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_surface_collision_runner_v121.gd").read_text(encoding="utf-8")
contract = json.loads(
    (ROOT / "data/tests/kg001_surface_collision_contract_v121.json").read_text(
        encoding="utf-8"
    )
)

checks = {
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.surface_collision_coverage_contract"
        and contract.get("version") == 121
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
        and contract.get("candidate_target") == "KG-001 Candidate 4"
    ),
    "all_demo_rooms": contract.get("scope") == ["R1", "R7", "R8"],
    "walkable_triangle_scan": all(token in runner for token in (
        "mesh.surface_get_arrays",
        "Mesh.ARRAY_VERTEX",
        "Mesh.ARRAY_INDEX",
        "absf(normal.y)",
        "projected_area",
    )),
    "four_interior_samples": all(token in runner for token in (
        "(a + b + c) / 3.0",
        "a * 0.60 + b * 0.20 + c * 0.20",
        "a * 0.20 + b * 0.60 + c * 0.20",
        "a * 0.20 + b * 0.20 + c * 0.60",
    )),
    "physics_support_probe": (
        "PhysicsRayQueryParameters3D.create" in runner
        and "intersect_ray" in runner
        and "hit_back_faces = true" in runner
        and "SUPPORT_TOLERANCE_Y" in runner
    ),
    "explicit_exemptions": (
        "GLOBAL_EXEMPT" in runner
        and "ROOM_EXEMPT" in runner
        and "_is_explicit_exempt" in runner
    ),
    "r8_hidden_support_included": (
        'room_id == "R8" and object_name == "Object01"' in runner
    ),
    "no_synthetic_collision": all(token not in runner for token in (
        "StaticBody3D.new()",
        "CollisionShape3D.new()",
        "create_trimesh_shape()",
    )),
    "all_rooms_runtime_audited": (
        'for room_id in ["R1", "R7", "R8"]' in runner
        and "await _audit_room(scene, manager, room_id)" in runner
    ),
    "fail_closed_samples": all(token in runner for token in (
        "missing_collision_support",
        "collision_support_below_visual_floor",
        "_no_missing_support",
        "_no_support_below_visual",
        "hit_y < point.y - SUPPORT_TOLERANCE_Y",
    )),
    "one_sided_support_semantics": (
        contract.get("runtime_policy", {}).get(
            "above_surface_collision_is_obstruction_not_hole"
        ) is True
        and "support_semantics" in contract.get("geometry_policy", {})
        and all(name in runner for name in (
            "save", "nibody", "well_pzpi1", "well_pzpi2",
            "r8s1", "door", "door01", "bible", "fontbot02",
        ))
    ),
    "result_marker": (
        "OPENAZRAEL_KG001_SURFACE_COLLISION_V121" in runner
        and '"version": 121' in runner
    ),
    "runtime_boundary": "asset-backed Godot v121 PASS" in contract.get(
        "evidence_boundary", ""
    ),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.surface_collision_contract_validation",
    "version": 121,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "NOT_EXECUTED",
    "checks": checks,
    "failed": failed,
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
