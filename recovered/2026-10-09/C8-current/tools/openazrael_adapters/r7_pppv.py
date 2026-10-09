from __future__ import annotations

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    EvidenceSequence,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


def _approach(target: str, action_id: str) -> PlayerAction:
    return PlayerAction(
        action_id=action_id,
        kind=ActionKind.MOVE,
        execution_mode=ExecutionMode.INPUT,
        input_action="move_forward",
        parameters={
            "goal_target": target,
            "stop_when_interactable": True,
            "driver_policy": "rotate_then_apply_gameplay_input",
            "max_frames": 900,
            "stuck_frames": 150,
        },
    )


def _look(target: str, action_id: str) -> PlayerAction:
    return PlayerAction(
        action_id=action_id,
        kind=ActionKind.LOOK,
        execution_mode=ExecutionMode.INPUT,
        input_action="mouse_motion",
        parameters={"goal_target": target, "max_frames": 220},
    )


def _world_waypoint(point: tuple[float, float, float], action_id: str) -> PlayerAction:
    return PlayerAction(
        action_id=action_id,
        kind=ActionKind.MOVE,
        execution_mode=ExecutionMode.INPUT,
        input_action="move_forward",
        parameters={
            "goal_world_point": list(point),
            "driver_policy": "r7_switch_target_disambiguation",
            "max_frames": 900,
            "stuck_frames": 150,
            "reach_distance": 6.0,
        },
    )


def _interact(target: str, action_id: str) -> PlayerAction:
    return PlayerAction(
        action_id=action_id,
        kind=ActionKind.INTERACT,
        execution_mode=ExecutionMode.INTERACTION_PROBE,
        target=target,
    )


def build_r7_switchboard_scenarios() -> tuple[ValidationScenario, ...]:
    lever = "Interact_well_lev02"
    wheel = "Interact_well_weel3"
    setup = {
        "reset_room_state": True,
        "spawn_view": "view",
        "lock_room_transitions": True,
    }

    positive = ValidationScenario(
        scenario_id="openazrael.r7.water_switchboard",
        room="R7",
        setup=setup,
        actions=(
            _approach(lever, "approach_switch_1"),
            _look(lever, "aim_switch_1"),
            _interact(lever, "switch_1"),
            _approach(wheel, "approach_switch_2"),
            _look(wheel, "aim_switch_2"),
            _interact(wheel, "switch_2"),
            # The source controls have overlapping 16-unit interaction spheres.
            # A short physical sidestep puts the lever surface in front of the
            # wheel for the authored final lever pull; no target/camera snap.
            _world_waypoint((65.0, -41.45, 85.0), "separate_switch_targets"),
            _approach(lever, "approach_switch_3"),
            _look(lever, "aim_switch_3"),
            _interact(lever, "switch_3"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="switchboard_flag",
                kind="state_change",
                action_id="switch_3",
                match={
                    "path": "flags.R7waterswitchboard",
                    "before": False,
                    "after": True,
                },
            ),
            EvidenceRequirement(
                requirement_id="bath_drain_flag",
                kind="state_change",
                action_id="switch_3",
                match={
                    "path": "flags.R8BathDrain",
                    "before": False,
                    "after": True,
                },
                after_requirement="switchboard_flag",
            ),
            EvidenceRequirement(
                requirement_id="r8_water_cleared",
                kind="state_change",
                action_id="switch_3",
                match={
                    "path": "puzzle.R8Water",
                    "before": False,
                    "after": False,
                },
                after_requirement="bath_drain_flag",
            ),
            EvidenceRequirement(
                requirement_id="drain_audio",
                kind="audio",
                action_id="switch_3",
                match={"asset": "S152V2.WAV"},
                after_requirement="bath_drain_flag",
            ),
        ),
        sequences=(
            EvidenceSequence(
                sequence_id="switchboard_interaction_order",
                kind="trigger",
                field="target",
                expected=(lever, wheel, lever),
                match={
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
                exact=True,
            ),
        ),
        state_expectations=(
            StateExpectation("flags.R7waterswitchboard", False, True),
            StateExpectation("flags.R8BathDrain", False, True),
            StateExpectation("puzzle.R8Water", False, False),
        ),
        metadata={
            "coverage_targets": ["gameplay:R7_WATER_SWITCHBOARD_SOLVED"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_sequence": ["well_lev02", "well_weel3", "well_lev02"],
            "source_evidence": [
                "DemoState.switchboard_step",
                "data/gameplay_event_graph_v87.json",
            ],
        },
    )

    negative = ValidationScenario(
        scenario_id="openazrael.r7.water_switchboard.negative_wrong_sequence",
        room="R7",
        setup=setup,
        actions=(
            _approach(lever, "approach_wrong_1"),
            _interact(lever, "wrong_1"),
            _approach(lever, "approach_wrong_2"),
            _interact(lever, "wrong_2"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="wrong_sequence_first_dispatch",
                kind="trigger",
                action_id="wrong_1",
                match={
                    "target": lever,
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
            EvidenceRequirement(
                requirement_id="wrong_sequence_second_dispatch",
                kind="trigger",
                action_id="wrong_2",
                match={
                    "target": lever,
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
        ),
        forbidden=(
            EvidenceRequirement(
                requirement_id="no_drain_flag_on_wrong_sequence",
                kind="state_change",
                match={"path": "flags.R8BathDrain", "after": True},
            ),
            EvidenceRequirement(
                requirement_id="no_switchboard_flag_on_wrong_sequence",
                kind="state_change",
                match={"path": "flags.R7waterswitchboard", "after": True},
            ),
            EvidenceRequirement(
                requirement_id="no_drain_audio_on_wrong_sequence",
                kind="audio",
                match={"asset": "S152V2.WAV"},
            ),
        ),
        sequences=(
            EvidenceSequence(
                sequence_id="wrong_switchboard_interaction_order",
                kind="trigger",
                field="target",
                expected=(lever, lever),
                match={
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
                exact=True,
            ),
        ),
        state_expectations=(
            StateExpectation("flags.R7waterswitchboard", False, False),
            StateExpectation("flags.R8BathDrain", False, False),
        ),
        metadata={
            "coverage_targets": [
                "gameplay:R7_WATER_SWITCHBOARD_SOLVED:negative"
            ],
            "negative_precondition": True,
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_runtime": "DemoState.switchboard_step reset behavior",
        },
    )

    scenarios = (positive, negative)
    for scenario in scenarios:
        errors = scenario.validate()
        if errors:
            raise ValueError(
                f"{scenario.scenario_id}: " + "; ".join(errors)
            )
    return scenarios
