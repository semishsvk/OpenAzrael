#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_well_tongs_animation_runner_v118.gd").read_text(encoding="utf-8")
interaction = (ROOT / "scripts/well_key_interaction.gd").read_text(encoding="utf-8")
state = (ROOT / "scripts/demo_state.gd").read_text(encoding="utf-8")
contract = json.loads(
    (ROOT / "data/tests/kg001_well_tongs_animation_contract_v118.json").read_text(
        encoding="utf-8"
    )
)

checks = {
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.well_tongs_animation_contract"
        and contract.get("version") == 118
    ),
    "runner_marker": (
        '"version": 118' in runner
        and "OPENAZRAEL_KG001_WELL_TONGS_V118" in runner
        and "openazrael.kg001.well_tongs_animation" in runner
    ),
    "real_main_scene": 'load("res://main.tscn")' in runner,
    "real_r7_asset_preflight": 'res://assets/rooms/R7.glb' in runner,
    "production_interaction_node": '"Interact_WellKey"' in runner,
    "production_key_visual": '"nibdyky01"' in runner,
    "negative_without_tongs": all(
        value in runner for value in (
            "without_tongs_no_key",
            "without_tongs_no_retrieval_node",
            "without_tongs_no_R7key_flag",
            "without_tongs_visual_transform_unchanged",
            "without_tongs_visual_stays_visible",
            "without_tongs_interaction_remains",
        )
    ),
    "positive_uses_real_inventory_precondition": (
        'state.acquire("rusty_tongs")' in runner
        and 'DemoState.has("rusty_tongs")' in interaction
    ),
    "positive_state_effects": all(
        value in runner for value in (
            "with_tongs_well_key_acquired",
            "with_tongs_R7KeyTake_set",
            "with_tongs_R7key_flag_set",
        )
    ),
    "state_retrieval_contract": (
        'set_puzzle_node("R7KeyTake")' in state
        and 'set_flag("R7key")' in state
        and 'acquire("well_key")' in state
    ),
    "multi_frame_observer": (
        "OBSERVE_FRAMES := 60" in runner
        and "for frame in range(OBSERVE_FRAMES)" in runner
        and "await process_frame" in runner
    ),
    "instant_hide_not_accepted": (
        "An instantaneous hide/removal is not an animation" in runner
        and "changed_frames.size() >= 2" in runner
    ),
    "visual_motion_or_staged_activity": (
        "transform_change_frames.size() >= 2" in runner
        and "visibility_change_frames.size() >= 2" in runner
        and "new_node_frames.size() >= 2" in runner
    ),
    "animation_assertion": "with_tongs_animation_activity_observed" in runner,
    "mechanism_not_prescribed": (
        "AnimationPlayer" not in contract.get("animation_requirement", {}).get(
            "accepted_evidence", []
        )
        and contract.get("animation_requirement", {}).get(
            "implementation_mechanism_not_prescribed"
        ) is True
    ),
    "original_animation_details_stay_hold": (
        contract.get("evidence_boundary", {}).get("original_animation_trajectory")
        == "HOLD_NOT_RECOVERED"
        and contract.get("evidence_boundary", {}).get("original_animation_timing")
        == "HOLD_NOT_RECOVERED"
    ),
    "current_source_known_missing_animation": (
        "create_tween" not in interaction
        and "AnimationPlayer" not in interaction
        and "animation" not in interaction.lower()
        and contract.get("current_implementation_observation", {}).get(
            "explicit_animation_trigger_present"
        ) is False
    ),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.well_tongs_animation_contract_validation",
    "version": 118,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "NOT_EXECUTED",
    "current_runtime_expectation": (
        "FAIL_MISSING_ANIMATION_TRIGGER"
        if checks["current_source_known_missing_animation"]
        else "IMPLEMENTATION_PRESENT_REQUIRES_RUNTIME"
    ),
    "checks": checks,
    "failed": failed,
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
