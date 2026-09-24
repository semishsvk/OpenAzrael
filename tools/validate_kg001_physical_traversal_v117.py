#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_physical_traversal_runner_v117.gd").read_text(encoding="utf-8")
player = (ROOT / "scripts/player.gd").read_text(encoding="utf-8")
main = (ROOT / "main.tscn").read_text(encoding="utf-8")
project = (ROOT / "project.godot").read_text(encoding="utf-8")
room = (ROOT / "scripts/room_manager.gd").read_text(encoding="utf-8")
contract = json.loads(
    (ROOT / "data/tests/kg001_physical_traversal_contract_v117.json").read_text(
        encoding="utf-8"
    )
)

stair_contract = {
    row["mesh"]: row for row in contract.get("stair_regressions", [])
    if isinstance(row, dict) and row.get("mesh")
}

portal_spawn_section = runner.split("func _observe_portal_spawn", 1)[1].split(
    "func _exercise_input_walk", 1
)[0]
r1_floor_section = runner.split("func _exercise_r1_floor", 1)[1].split(
    "func _exercise_r8_stair_mesh", 1
)[0]

checks = {
    "tracked_contract": (
        contract.get("schema") == "openazrael.kg001.physical_traversal_contract"
        and contract.get("version") == 117
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
        and contract.get("runtime_status") == "NOT_EXECUTED_ON_THIS_BRANCH"
    ),
    "tracked_contract_production_player": (
        contract.get("production_path", {}).get("body") == "CharacterBody3D"
        and contract.get("production_path", {}).get("collision_layer") == 4
        and contract.get("production_path", {}).get("collision_mask") == 1
        and contract.get("production_path", {}).get("capsule_radius") == 11.0
        and contract.get("production_path", {}).get("capsule_height") == 52.0
    ),
    "tracked_contract_stair_geometry": (
        stair_contract.get("step011__mesh", {}).get("audited_tread_levels") == 4
        and stair_contract.get("stairs__STAIR2", {}).get("audited_tread_levels") == 8
        and stair_contract.get("step011__mesh", {}).get("audited_total_rise", 0) > 15.0
        and stair_contract.get("stairs__STAIR2", {}).get("audited_total_rise", 0) > 87.0
        and stair_contract.get("stairs__STAIR2", {}).get("approximate_rise_per_step", 0) > 12.0
    ),
    "tracked_contract_spawn_regressions": (
        len(contract.get("portal_spawn_regressions", [])) == 4
        and sum(1 for row in contract.get("portal_spawn_regressions", [])
                if row.get("pre_fix_penetration") is True) == 3
        and all(row.get("clearance_added") == 4.0
                for row in contract.get("portal_spawn_regressions", []))
        and contract.get("floor_regression", {}).get(
            "test_may_normalize_player_to_floor"
        ) is False
    ),
    "tracked_contract_stair_assist": (
        contract.get("production_path", {}).get("step_up", {}).get(
            "max_step_height"
        ) == 14.0
        and contract.get("production_path", {}).get("step_up", {}).get(
            "floor_snap_length"
        ) == 16.0
        and contract.get("production_path", {}).get("step_up", {}).get(
            "safe_margin"
        ) == 0.25
        and contract.get("production_path", {}).get("step_up", {}).get(
            "step_surface_epsilon"
        ) == 0.75
        and contract.get("production_path", {}).get("step_up", {}).get(
            "minimum_forward_settle"
        ) == 2.0
        and contract.get("production_path", {}).get("step_up", {}).get(
            "post_step_floor_snap"
        ) is True
    ),
    "runner_version_marker": (
        '"version": 117' in runner
        and "OPENAZRAEL_KG001_PHYSICAL_V117" in runner
        and "openazrael.kg001.physical_traversal" in runner
    ),
    "loads_real_main_scene": 'load("res://main.tscn")' in runner,
    "asset_preflight": all(
        value in runner
        for value in ("R1.glb", "R7.glb", "R8.glb", "BLOCKED_MISSING_ASSETS")
    ),
    "production_player_is_character_body": "extends CharacterBody3D" in player,
    "production_player_uses_real_input": 'Input.get_vector("move_left", "move_right", "move_forward", "move_back")' in player,
    "production_player_uses_move_and_slide": "move_and_slide()" in player,
    "production_player_has_collision_tested_step_up": all(
        value in player
        for value in (
            "@export var max_step_height := 14.0",
            "@export var step_probe_distance := 14.0",
            "@export var step_clearance := 0.35",
            "@export var step_surface_epsilon := 0.75",
            "@export var traversal_safe_margin := 0.25",
            "floor_snap_length = max_step_height + 2.0",
            "safe_margin = traversal_safe_margin",
            "if not test_move(",
            "var floor_hit := _step_floor_probe",
            "probe_distances: Array[float]",
            "query.hit_back_faces = true",
            "absf(normal.y) < cos(floor_max_angle)",
            "if test_move(",
            "var raised := global_transform",
            "raised.origin += lift",
            "global_position += lift",
            "var settle_motion := direction * maxf(horizontal_motion.length(), 2.0)",
            "global_position += settle_motion",
            "apply_floor_snap()",
        )
    ),
    "production_step_up_winding_safe_and_diagnostic": all(
        value in player
        for value in (
            "Legacy tread winding is inconsistent",
            "best_step_height",
            "step_debug_snapshot",
            "step_reject_no_tread",
            "step_reject_lift_blocked",
            "step_reject_forward_blocked",
            "step_success",
        )
    ),
    "production_step_up_only_when_blocked": (
        "Only engage stair assist when normal horizontal movement is actually"
        in player
        and "horizontal_motion.length_squared() < 0.000001" in player
        and "if not is_on_floor()" in player
    ),
    "production_capsule_contract": (
        '[sub_resource type="CapsuleShape3D" id="Capsule_player"]' in main
        and "radius = 11.0" in main
        and "height = 52.0" in main
        and "collision_layer = 4" in main
        and "collision_mask = 1" in main
    ),
    "project_input_actions_exist": all(
        f"{action}=" in project
        for action in ("move_forward", "move_back", "move_left", "move_right")
    ),
    "runtime_drives_input_actions": (
        'Input.action_press(action, 1.0)' in runner
        and 'Input.action_press("move_forward", 1.0)' in runner
        and "Input.action_release" in runner
    ),
    "runtime_advances_physics_frames": "await physics_frame" in runner,
    "runtime_records_step_debug": (
        '"step_debug": step_debug' in runner
        and 'player.has_method("clear_step_debug")' in runner
        and 'debug_player.has_method("step_debug_snapshot")' in runner
    ),
    "runtime_bridges_real_measurements_into_pppv_evidence": all(
        value in runner
        for value in (
            "pppv_evidence_bus.gd",
            'record_player_action("r1_forward", "input"',
            'record("collision_support"',
            'record("movement"',
            'record_player_action("ascend", "input"',
            'record_player_action("descend", "input"',
            'record("stair_traversal"',
            '"pppv_evidence": pppv_evidence.bundle()',
        )
    ),
    "natural_portal_spawn_regression": all(
        value in runner
        for value in (
            "_observe_portal_spawn",
            '"R1", "spaview", "R1_spaview"',
            '"R1", "entcori", "R1_entcori"',
            '"R7", "view", "R7_view"',
            '"R8", "Object14", "R8_Object14"',
            "_natural_spawn_no_fall_through",
            "_natural_spawn_reaches_floor",
            "_natural_spawn_floor_height",
            "_natural_spawn_floor_contact",
        )
    ),
    "runner_does_not_normalize_spawn_to_floor": (
        "Candidate 2 failed immediately after the real portal spawn" in r1_floor_section
        and "player.global_position = Vector3(" not in portal_spawn_section
        and "player.global_position = Vector3(" not in r1_floor_section
        and "player.global_position = origin" in r1_floor_section
    ),
    "production_portal_spawn_avoids_adjacent_geometry": (
        contract.get("portal_spawn_policy", {}).get("default_normal_offset") == 120.0
        and contract.get("portal_spawn_policy", {}).get("r8_object14_expected_offset") == 115.0
        and contract.get("portal_spawn_policy", {}).get("hardcoded_per_portal_offsets_forbidden") is True
        and "func _portal_spawn_distance" in room
        and "PORTAL_SPAWN_DISTANCE_CANDIDATES" in room
        and "intersect_shape" in room
        and "support_collider" in room
        and "spawn_distance := _portal_spawn_distance" in room
    ),
    "r1_canonical_spawn_floor_walk": all(
        value in runner
        for value in (
            '"R1", "spaview"',
            "R1_forward_walk_no_fall_through",
            "R1_back_walk_no_fall_through",
            "R1_walk_has_real_horizontal_progress",
            "R1_walk_retains_floor_contact",
        )
    ),
    "r1_uses_real_floor_collision": (
        "PhysicsRayQueryParameters3D.create" in runner
        and "direct_space_state.intersect_ray" in runner
    ),
    "r1_tracks_local_support_while_moving": all(
        value in runner
        for value in (
            "support_missing_frames",
            "max_below_support",
            "below_support > 2.5",
            "R1_forward_walk_support_continuous",
            "R1_back_walk_support_continuous",
        )
    ),
    "r8_uses_imported_real_stairs": all(
        value in runner
        for value in (
            "step011__mesh",
            "stairs__STAIR2",
            "_exercise_r8_stair_mesh",
            "_stair_tread_levels",
            "Mesh.ARRAY_VERTEX",
            "mesh_instance.global_transform",
        )
    ),
    "r8_covers_both_walkable_stair_profiles": all(
        value in runner
        for value in (
            '"step011__mesh", "R8_step011"',
            '"stairs__STAIR2", "R8_main_stairs"',
            "4, 14.0, 28.0",
            "8, 80.0, 120.0",
        )
    ),
    "stair_profile_does_not_trust_legacy_winding": (
        "absf(normal.y) < 0.75" in runner
        and "Issue #6 proved source winding is not a safe semantic oracle" in runner
    ),
    "stair_real_landings_are_probed": all(
        value in runner
        for value in (
            "_floor_at",
            'check_prefix + "_lower_landing_present"',
            'check_prefix + "_upper_landing_present"',
            'check_prefix + "_lower_landing_floor_contact"',
            'check_prefix + "_upper_landing_floor_contact"',
            'check_prefix + "_full_path_nontrivial"',
        )
    ),
    "stair_ascent_is_motion_assertion": all(
        value in runner
        for value in (
            'check_prefix + "_up_progress"',
            'check_prefix + "_up_height"',
            'check_prefix + "_up_no_fall_through"',
            'check_prefix + "_up_floor_contact"',
        )
    ),
    "stair_descent_is_motion_assertion": all(
        value in runner
        for value in (
            'check_prefix + "_down_progress"',
            'check_prefix + "_down_height"',
            'check_prefix + "_down_no_fall_through"',
            'check_prefix + "_down_floor_contact"',
            '"final_on_floor"',
            '"final_y"',
        )
    ),
    "stair_runs_are_near_landing_to_landing": (
        runner.count("ascent_distance * 0.98") >= 2
        and "ascent_distance * 0.94" in runner
    ),
    "no_fake_stair_fixture": (
        "BoxShape3D.new()" not in runner
        and "StaticBody3D.new()" not in runner
    ),
    "runner_does_not_replace_player_motion": "player.move_and_slide" not in runner,
    "no_direct_velocity_drive_for_horizontal_motion": (
        "player.velocity.x =" not in runner
        and "player.velocity.z =" not in runner
    ),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.physical_traversal_contract",
    "version": 117,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "godot_runtime_status": "NOT_EXECUTED",
    "requires_local_room_assets": True,
    "checks": checks,
    "failed": failed,
    "boundary": (
        "Source validation proves the runner uses the production Player/Input/collision path. "
        "Only a Godot runtime PASS with restored R1/R7/R8 assets proves physical traversal."
    ),
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
