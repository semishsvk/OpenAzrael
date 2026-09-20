#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_physical_traversal_runner_v117.gd").read_text(encoding="utf-8")
player = (ROOT / "scripts/player.gd").read_text(encoding="utf-8")
main = (ROOT / "main.tscn").read_text(encoding="utf-8")
project = (ROOT / "project.godot").read_text(encoding="utf-8")

checks = {
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
        )
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
