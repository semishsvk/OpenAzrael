from __future__ import annotations

from typing import Any

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    EvidenceSequence,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


def _step(row: dict[str, Any]) -> str:
    semantic = str(row.get("semantic", ""))
    if semantic == "remove_room_object":
        return f"remove_room:{row.get('object')}"
    if semantic == "add_room_object":
        return f"add_room:{row.get('object')}"
    if semantic == "remove_inventory":
        return f"remove_inventory:{row.get('object')}"
    if semantic == "play_sound":
        return f"play_sound:{row.get('asset')}"
    return semantic


def adapt_well_tongs_contract(
    payload: dict[str, Any],
) -> tuple[ValidationScenario, ValidationScenario]:
    expected_schema = "openazrael.kg001.well_tongs_animation_contract"
    if payload.get("schema") != expected_schema:
        raise ValueError(f"expected schema {expected_schema}")

    room = str(payload.get("room", "R7"))
    target = str(payload["interaction"])
    item = str(payload["inventory_precondition"])
    compiled = list(payload.get("exact_compiled_action_sequence", []))
    if not compiled:
        raise ValueError("compiled action sequence is required")

    steps = [_step(row) for row in compiled]
    key_object = str(compiled[0].get("object", "R7Key"))
    steps.append(f"default_take:{key_object}")
    sound = str(payload.get("sound", {}).get("filename", "979TONGS.WAV"))

    actions = (
        PlayerAction(
            action_id="approach_well",
            kind=ActionKind.MOVE,
            execution_mode=ExecutionMode.INPUT,
            input_action="move_forward",
            parameters={
                "goal_target": target,
                "stop_when_interactable": True,
                "driver_policy": "rotate_then_apply_gameplay_input",
            },
        ),
        PlayerAction(
            action_id="aim_well",
            kind=ActionKind.LOOK,
            execution_mode=ExecutionMode.INPUT,
            input_action="mouse_motion",
            parameters={
                "goal_target": target,
                "max_frames": 180,
                "driver_policy": "aim_via_production_mouse_input",
            },
        ),
        PlayerAction(
            action_id="interact_well",
            kind=ActionKind.INTERACT,
            execution_mode=ExecutionMode.INTERACTION_PROBE,
            target=target,
        ),
    )

    forbidden: tuple[EvidenceRequirement, ...] = ()
    if (
        payload.get("dispatch_observation", {})
        .get("transform_or_rotation_opcode_present")
        is False
    ):
        forbidden = (
            EvidenceRequirement(
                requirement_id="no_invented_transform_tween",
                kind="animation",
                match={"kind": "invented_transform_tween"},
            ),
        )

    positive = ValidationScenario(
        scenario_id="openazrael.r7.well_tongs.positive",
        room=room,
        setup={
            "inventory": {item: True},
            "reset_room_state": True,
            "spawn_view": "view",
            "lock_room_transitions": True,
        },
        actions=actions,
        requirements=(
            EvidenceRequirement(
                requirement_id="well_target_reachable",
                kind="interaction_probe",
                action_id="aim_well",
                match={"target": target, "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="well_trigger",
                kind="trigger",
                action_id="interact_well",
                match={"target": target, "activated": True},
                after_requirement="well_target_reachable",
            ),
            EvidenceRequirement(
                requirement_id="well_audio",
                kind="audio",
                action_id="interact_well",
                match={"asset": sound},
                after_requirement="well_trigger",
            ),
        ),
        forbidden=forbidden,
        sequences=(
            EvidenceSequence(
                sequence_id="official_demo_action_order",
                kind="demo_action_step",
                field="step",
                expected=tuple(steps),
                exact=True,
            ),
        ),
        state_expectations=(
            StateExpectation(f"inventory.{item}", True, False),
            StateExpectation("inventory.well_key", False, True),
            StateExpectation("puzzle.R7KeyTake", False, True),
            StateExpectation("flags.R7key", False, True),
        ),
        metadata={
            "source_version": payload.get("version"),
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_action_steps": steps,
            "coverage_targets": ["gameplay:R7_WELL_TONGS_USE"],
        },
    )

    negative = ValidationScenario(
        scenario_id="openazrael.r7.well_tongs.negative_without_tongs",
        room=room,
        setup={
            "inventory": {item: False},
            "reset_room_state": True,
            "spawn_view": "view",
            "lock_room_transitions": True,
        },
        actions=actions,
        requirements=(
            EvidenceRequirement(
                requirement_id="well_target_reachable",
                kind="interaction_probe",
                action_id="aim_well",
                match={"target": target, "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="well_trigger_dispatched",
                kind="trigger",
                action_id="interact_well",
                match={"target": target, "activated": True},
                after_requirement="well_target_reachable",
            ),
        ),
        forbidden=(
            EvidenceRequirement(
                requirement_id="no_demo_steps_without_tongs",
                kind="demo_action_step",
            ),
            EvidenceRequirement(
                requirement_id="no_tongs_audio_without_tongs",
                kind="audio",
                match={"asset": sound},
            ),
        ),
        state_expectations=(
            StateExpectation(f"inventory.{item}", False, False),
            StateExpectation("inventory.well_key", False, False),
            StateExpectation("puzzle.R7KeyTake", False, False),
            StateExpectation("flags.R7key", False, False),
        ),
        metadata={
            "source_version": payload.get("version"),
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "negative_precondition": True,
            "coverage_targets": ["gameplay:R7_WELL_TONGS_USE:negative"],
        },
    )

    for scenario in (positive, negative):
        errors = scenario.validate()
        if errors:
            raise ValueError("; ".join(errors))
    return positive, negative
