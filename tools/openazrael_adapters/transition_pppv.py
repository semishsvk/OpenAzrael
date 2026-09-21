from __future__ import annotations

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


def _transition_scenario(
    *,
    scenario_id: str,
    source_room: str,
    spawn_view: str,
    trigger: str,
    destination_room: str,
    setup_flags: dict[str, bool],
    preserved_state: tuple[StateExpectation, ...] = (),
) -> ValidationScenario:
    scenario = ValidationScenario(
        scenario_id=scenario_id,
        room=source_room,
        setup={
            "reset_room_state": True,
            "spawn_view": spawn_view,
            "flags": setup_flags,
        },
        actions=(
            PlayerAction(
                action_id="cross_" + trigger,
                kind=ActionKind.MOVE,
                execution_mode=ExecutionMode.INPUT,
                input_action="move_forward",
                parameters={
                    "goal_trigger": trigger,
                    "source_room": source_room,
                    "destination_room": destination_room,
                    "max_frames": 1200,
                    "stuck_frames": 180,
                    "reach_distance": 8.0,
                    "driver_policy": "steer_to_trigger_via_gameplay_input",
                    "verify_destination_spawn": True,
                    "spawn_position_tolerance": 14.0,
                    "spawn_yaw_tolerance": 0.35,
                },
            ),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="trigger_enter_" + trigger,
                kind="trigger",
                action_id="cross_" + trigger,
                match={
                    "room": source_room,
                    "target": trigger,
                    "activated": True,
                    "edge": "ENTER",
                    "mechanism": "world_trigger",
                },
            ),
            EvidenceRequirement(
                requirement_id="room_transition_" + trigger,
                kind="room_transition",
                action_id="cross_" + trigger,
                match={
                    "source_room": source_room,
                    "trigger": trigger,
                    "destination_room": destination_room,
                },
                after_requirement="trigger_enter_" + trigger,
            ),
        ),
        state_expectations=preserved_state,
        metadata={
            "coverage_targets": [
                f"transition:{source_room}:{trigger}:{destination_room}"
            ],
            "physical_crossing_required": True,
            "trigger_centroid_role": "steering_target_only",
            "teleport_allowed_during_action": False,
            "destination_spawn_validation_required": True,
            "critical_if_transition_broken": True,
            "source_evidence": "data/xaf_trigger_evidence.json",
        },
    )
    errors = scenario.validate()
    if errors:
        raise ValueError(f"{scenario_id}: " + "; ".join(errors))
    return scenario


def build_transition_scenarios() -> tuple[ValidationScenario, ...]:
    return (
        _transition_scenario(
            scenario_id="openazrael.transition.r1_to_r7",
            source_room="R1",
            spawn_view="spaview",
            trigger="zxcoriR5",
            destination_room="R7",
            setup_flags={"R1Door1Open": True},
            preserved_state=(
                StateExpectation("flags.R1Door1Open", True, True),
            ),
        ),
        _transition_scenario(
            scenario_id="openazrael.transition.r7_to_r1",
            source_room="R7",
            spawn_view="view",
            trigger="zxwell2R6",
            destination_room="R1",
            setup_flags={},
        ),
        _transition_scenario(
            scenario_id="openazrael.transition.r1_to_r8",
            source_room="R1",
            spawn_view="entcori",
            trigger="zxcoriR2",
            destination_room="R8",
            setup_flags={"R1Door2Open": True, "FR1DoorUnlocked": True},
            preserved_state=(
                StateExpectation("flags.R1Door2Open", True, True),
                StateExpectation("flags.FR1DoorUnlocked", True, True),
            ),
        ),
        _transition_scenario(
            scenario_id="openazrael.transition.r8_to_r1",
            source_room="R8",
            spawn_view="Object14",
            trigger="zxorrery",
            destination_room="R1",
            setup_flags={},
        ),
    )
