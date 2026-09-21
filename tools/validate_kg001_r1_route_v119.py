#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_r1_route_runner_v119.gd").read_text(encoding="utf-8")
room = (ROOT / "scripts/room_manager.gd").read_text(encoding="utf-8")
contract = json.loads(
    (ROOT / "data/tests/kg001_r1_route_contract_v119.json").read_text(
        encoding="utf-8"
    )
)

checks = {
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.r1_route_contract"
        and contract.get("version") == 119
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
    ),
    "candidate3_bug_bound": (
        contract.get("candidate3_bug", {}).get("room") == "R1"
        and contract.get("candidate3_bug", {}).get("trigger") == "zxcoriR5"
        and contract.get("candidate3_bug", {}).get("candidate3_g10") == "FAIL"
        and contract.get("candidate3_bug", {}).get("expected_support_mesh")
        == "Object02__mesh"
        and contract.get("candidate3_bug", {}).get("expected_collision_body")
        == "Collision_Object02"
    ),
    "bug_position_exact": (
        contract.get("candidate3_bug", {}).get("player_position")
        == [-264.159088134766, -114.801208496094, 381.168426513672]
        and "BUG_POINT := Vector3(-264.159088134766, -83.86095602785532, 381.168426513672)"
        in runner
    ),
    "r1_asset_bound": (
        contract.get("r1_asset", {}).get("sha256")
        == "8a35e60b3f26d1fa656653cc7d3d5875c0927c77882189a6f073bf7ed16a3a6c"
        and contract.get("r1_asset", {}).get("bytes") == 535916
    ),
    "room_aware_object02_fix": all(
        value in room
        for value in (
            'obj_name == "Object02" and room_id != "R1"',
            "R1/Object02 is a",
            "visible authored floor segment under zxcoriR5",
        )
    ),
    "global_object02_exclusion_removed": (
        'obj_name in ["Object02", "Object03"' not in room
    ),
    "no_replacement_floor_policy": (
        contract.get("collision_policy", {}).get(
            "no_invisible_replacement_floor"
        ) is True
        and contract.get("collision_policy", {}).get(
            "no_fall_recovery_teleport"
        ) is True
        and "BoxShape3D.new()" not in runner
        and "StaticBody3D.new()" not in runner
    ),
    "runner_marker": (
        '"version": 119' in runner
        and "OPENAZRAEL_KG001_R1_ROUTE_V119" in runner
        and "openazrael.kg001.r1_route" in runner
    ),
    "real_main_scene": 'load("res://main.tscn")' in runner,
    "real_r1_asset": 'res://assets/rooms/R1.glb' in runner,
    "natural_spaview_spawn": (
        'manager.call("_spawn_at_portal", "R1", "spaview")' in runner
    ),
    "object02_collision_asserted": all(
        value in runner
        for value in (
            '"Object02__mesh"',
            '"Collision_Object02"',
            "R1_Object02_collision_present",
            "R1_bug_point_support_is_Object02",
            "R1_Object02_cross_used_Object02_support",
        )
    ),
    "real_input_movement": (
        'Input.action_press("move_forward", 1.0)' in runner
        and "await physics_frame" in runner
        and "player.rotation.y = atan2" in runner
    ),
    "continuous_support_tracking": all(
        value in runner
        for value in (
            "support_missing_max_consecutive",
            "player.global_position.y < support_y - 4.0",
            "floor_contact_ratio",
            "R1_Object02_cross",
        )
    ),
    "route_is_not_short_smoke": (
        len(contract.get("canonical_route_waypoints", [])) == 15
        and "for index in range(ROUTE.size())" in runner
        and "R1_route_reached_tunnel07" in runner
    ),
    "object02_detour_is_two_triangle_crossing": (
        len(contract.get("object02_detour", [])) == 3
        and "OBJECT02_FAR" in runner
        and "TUNNEL03_CENTER" in runner
    ),
    "doors_are_pre_solved_for_collision_isolation": all(
        value in runner
        for value in (
            'state.set_flag("R1Door1Open")',
            'state.acquire("well_key")',
            'state.set_flag("FR1DoorUnlocked")',
            'state.set_flag("R1Door2Open")',
        )
    ),
    "transitions_disabled": "manager.transition_cooldown = 999.0" in runner,
    "historical_v117_not_rewritten": (
        contract.get("evidence_boundary", "").startswith(
            "v119 supersedes the Candidate 3 blind spot"
        )
    ),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.r1_route_contract_validation",
    "version": 119,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "godot_runtime_status": "NOT_EXECUTED",
    "checks": checks,
    "failed": failed,
    "boundary": (
        "Source validation proves the room-aware Object02 fix and v119 route "
        "oracle are present. Only Godot runtime execution over restored R1.glb "
        "can prove Candidate 3's floor hole is fixed."
    ),
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
