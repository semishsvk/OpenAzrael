#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_collision_parity_runner_v120.gd").read_text(encoding="utf-8")
room = (ROOT / "scripts/room_manager.gd").read_text(encoding="utf-8")
contract = json.loads(
    (ROOT / "data/tests/kg001_collision_parity_contract_v120.json").read_text(
        encoding="utf-8"
    )
)

checks = {
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.collision_parity_contract"
        and contract.get("version") == 120
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
    ),
    "all_demo_rooms": contract.get("scope") == ["R1", "R7", "R8"],
    "geometry_policy": (
        contract.get("geometry_policy", {}).get("walkable_normal_abs_y_min") == 0.65
        and contract.get("geometry_policy", {}).get("minimum_total_projected_area") == 150.0
        and contract.get("geometry_policy", {}).get("legacy_winding_policy")
        == "absolute normal Y; do not trust source winding"
    ),
    "independent_exemptions": (
        "GLOBAL_EXEMPT" in runner
        and "ROOM_EXEMPT" in runner
        and "_is_explicit_exempt" in runner
        and "explicit and audited" in contract.get(
            "explicit_non_solid_exemptions", {}
        ).get("rationale", "").lower()
    ),
    "mesh_surface_geometry_scan": all(
        token in runner
        for token in (
            "mesh.surface_get_arrays",
            "Mesh.ARRAY_VERTEX",
            "Mesh.ARRAY_INDEX",
            "absf(normal.y)",
            "projected := area * abs_y",
        )
    ),
    "visible_floor_like_policy": (
        "not mi.visible" in runner
        and "projected_area >= MIN_TOTAL_PROJECTED_AREA" in runner
    ),
    "runtime_collision_owner": (
        '"Collision_" + object_name' in runner
        and '"Collision_" + String(parent.name)' in runner
        and "_collision_body" in runner
        and "_find_named" in runner
        and "_collision_shape" in runner
        and "var grouped := _find_named(parent" in runner
    ),
    "collision_contract": all(
        token in runner
        for token in (
            "collision_layer",
            "collision_mask",
            "ConcavePolygonShape3D",
            "backface_collision",
        )
    ),
    "candidate3_object02_regression": all(
        token in runner
        for token in (
            'room_id == "R1" and object_name == "Object02"',
            "R1_Object02_generic_floor_detected",
            "R1_Object02_not_exempt",
            "R1_Object02_collision_present",
        )
    ),
    "r1_object02_source_fix_present": (
        'obj_name == "Object02" and room_id != "R1"' in room
        and 'obj_name in ["Object02", "Object03"' not in room
    ),
    "all_rooms_runtime_audited": (
        'for room_id in ["R1", "R7", "R8"]' in runner
        and "await _audit_room(manager, room_id)" in runner
    ),
    "result_marker": (
        "OPENAZRAEL_KG001_COLLISION_PARITY_V120" in runner
        and '"version": 120' in runner
        and "openazrael.kg001.collision_parity" in runner
    ),
    "no_synthetic_collision_fix": (
        "StaticBody3D.new()" not in runner
        and "CollisionShape3D.new()" not in runner
        and "create_trimesh_shape()" not in runner
    ),
    "runtime_boundary": "Asset-backed Godot execution is required" in contract.get(
        "evidence_boundary", ""
    ),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.collision_parity_contract_validation",
    "version": 120,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "NOT_EXECUTED",
    "checks": checks,
    "failed": failed,
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
