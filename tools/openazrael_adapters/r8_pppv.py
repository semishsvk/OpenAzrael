from __future__ import annotations

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


# Source-derived R8 ingress to the drained-bath/lens side of the Baptistery.
# Object14 enters on Object01, step011 raises the player to the main floor,
# and the authored right-hand broken mirror is the passage through the
# BAPFRONT wall. These are physical navigation goals, never teleport targets.
R8_LENS_INGRESS_ROUTE = (
    (-278.067350, -87.124025, 394.941924),
    # step011 source-derived horizontal tread centers. Traversing each tread
    # individually keeps the production CharacterBody on the authored stairs
    # instead of asking the navigator to cut across multiple vertical risers.
    (-254.067350, -79.249800, 394.941936),
    (-243.696350, -74.195030, 394.941940),
    (-233.238082, -69.118450, 394.941948),
    (-222.866992, -64.063640, 394.941952),
    (-208.866992, -63.785391, 394.941959),
    (-101.798000, -63.785391, 160.000000),
    (-101.798000, -63.572091, 136.000000),
    (-67.000000, -63.572091, 93.000000),
    (-55.000000, -63.572091, 92.000000),
    (8.000000, -63.572091, 93.000000),
)


def _world_waypoint(
    point: tuple[float, float, float],
    action_id: str,
    *,
    reach_distance: float = 12.0,
) -> PlayerAction:
    return PlayerAction(
        action_id=action_id,
        kind=ActionKind.MOVE,
        execution_mode=ExecutionMode.INPUT,
        input_action="move_forward",
        parameters={
            "goal_world_point": list(point),
            "driver_policy": "source_derived_r8_world_waypoint",
            "max_frames": 900,
            "stuck_frames": 150,
            "reach_distance": reach_distance,
        },
    )


def _r8_ingress_actions(prefix: str) -> tuple[PlayerAction, ...]:
    rows: list[PlayerAction] = []
    for index, point in enumerate(R8_LENS_INGRESS_ROUTE):
        reach = 3.0 if index in {1, 2, 3, 4} else (1.0 if index in {6, 7} else 12.0)
        rows.append(
            _world_waypoint(
                point,
                f"{prefix}_{index:02d}",
                reach_distance=reach,
            )
        )
    return tuple(rows)


def _actions(
    target: str, prefix: str
) -> tuple[PlayerAction, PlayerAction, PlayerAction]:
    return (
        PlayerAction(
            action_id=f"approach_{prefix}",
            kind=ActionKind.MOVE,
            execution_mode=ExecutionMode.INPUT,
            input_action="move_forward",
            parameters={
                "goal_target": target,
                "stop_when_interactable": True,
                "driver_policy": "rotate_then_apply_gameplay_input",
                "max_frames": 1200,
                "stuck_frames": 180,
            },
        ),
        PlayerAction(
            action_id=f"aim_{prefix}",
            kind=ActionKind.LOOK,
            execution_mode=ExecutionMode.INPUT,
            input_action="mouse_motion",
            parameters={"goal_target": target, "max_frames": 240},
        ),
        PlayerAction(
            action_id=f"interact_{prefix}",
            kind=ActionKind.INTERACT,
            execution_mode=ExecutionMode.INTERACTION_PROBE,
            target=target,
        ),
    )


def build_r8_interaction_scenarios() -> tuple[ValidationScenario, ...]:
    base_setup = {
        "reset_room_state": True,
        "spawn_view": "Object14",
        "lock_room_transitions": True,
    }

    lens_pickup = ValidationScenario(
        scenario_id="openazrael.r8.take_lens",
        room="R8",
        setup={
            **base_setup,
            "flags": {"R8BathDrain": True},
            "inventory": {"r8_lens": False},
        },
        actions=(
            *_r8_ingress_actions("route_to_lens"),
            *_actions("Interact_R8Lens", "lens"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="lens_reachable",
                kind="interaction_probe",
                action_id="approach_lens",
                match={"target": "Interact_R8Lens", "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="lens_dispatch",
                kind="trigger",
                action_id="interact_lens",
                match={
                    "target": "Interact_R8Lens",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
                after_requirement="lens_reachable",
            ),
            EvidenceRequirement(
                requirement_id="lens_inventory_change",
                kind="state_change",
                action_id="interact_lens",
                match={
                    "path": "inventory.r8_lens",
                    "before": False,
                    "after": True,
                },
                after_requirement="lens_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="lens_flag_change",
                kind="state_change",
                action_id="interact_lens",
                match={
                    "path": "flags.R8Lens",
                    "before": False,
                    "after": True,
                },
                after_requirement="lens_dispatch",
            ),
        ),
        state_expectations=(
            StateExpectation("flags.R8BathDrain", True, True),
            StateExpectation("inventory.r8_lens", False, True),
            StateExpectation("flags.R8Lens", False, True),
        ),
        metadata={
            "coverage_targets": ["interaction:R8:lens_pickup"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_runtime": "r8_lens_interaction.gd",
        },
    )

    lens_blocked = ValidationScenario(
        scenario_id="openazrael.r8.take_lens.negative_water_not_drained",
        room="R8",
        setup={
            **base_setup,
            "flags": {"R8BathDrain": False},
            "inventory": {"r8_lens": False},
        },
        actions=(
            *_r8_ingress_actions("route_to_submerged_lens"),
            *_actions("Interact_R8Lens", "submerged_lens"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="submerged_lens_dispatch",
                kind="trigger",
                action_id="interact_submerged_lens",
                match={
                    "target": "Interact_R8Lens",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
        ),
        forbidden=(
            EvidenceRequirement(
                requirement_id="no_lens_without_drain",
                kind="state_change",
                match={"path": "inventory.r8_lens", "after": True},
            ),
            EvidenceRequirement(
                requirement_id="no_r8lens_flag_without_drain",
                kind="state_change",
                match={"path": "flags.R8Lens", "after": True},
            ),
        ),
        state_expectations=(
            StateExpectation("flags.R8BathDrain", False, False),
            StateExpectation("inventory.r8_lens", False, False),
            StateExpectation("flags.R8Lens", False, False),
        ),
        metadata={
            "coverage_targets": ["interaction:R8:lens_pickup:negative"],
            "negative_precondition": True,
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
        },
    )

    lens_place = ValidationScenario(
        scenario_id="openazrael.r8.place_lens",
        room="R8",
        setup={
            **base_setup,
            "inventory": {"r8_lens": True},
            "flags": {"R8Lens": True, "R8BathDrain": True},
            "puzzle": {"R8LensPlace": False},
        },
        actions=(
            *_r8_ingress_actions("route_to_bible_place_lens"),
            *_actions("Interact_R8Bible", "bible_place_lens"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="bible_lens_dispatch",
                kind="trigger",
                action_id="interact_bible_place_lens",
                match={
                    "target": "Interact_R8Bible",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
            EvidenceRequirement(
                requirement_id="lens_removed_from_inventory",
                kind="state_change",
                action_id="interact_bible_place_lens",
                match={
                    "path": "inventory.r8_lens",
                    "before": True,
                    "after": False,
                },
                after_requirement="bible_lens_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="lens_place_node",
                kind="state_change",
                action_id="interact_bible_place_lens",
                match={
                    "path": "puzzle.R8LensPlace",
                    "before": False,
                    "after": True,
                },
                after_requirement="bible_lens_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="lens_place_audio",
                kind="audio",
                action_id="interact_bible_place_lens",
                match={"asset": "S137.WAV"},
                after_requirement="lens_place_node",
            ),
        ),
        state_expectations=(
            StateExpectation("inventory.r8_lens", True, False),
            StateExpectation("flags.R8Lens", True, True),
            StateExpectation("puzzle.R8LensPlace", False, True),
        ),
        metadata={
            "coverage_targets": ["gameplay:R8_LENS_PLACE"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_evidence": "gameplay:R8_LENS_PLACE",
        },
    )

    optical = ValidationScenario(
        scenario_id="openazrael.r8.optical_sequence",
        room="R8",
        setup={
            **base_setup,
            "flags": {"R8BathDrain": True},
            "inventory": {"r8_lens": False},
            "puzzle": {
                "R8LensPlace": True,
                "R8LensLook": False,
                "R8RaiseTimer": False,
                "R8Counter": False,
                "DoorR8": False,
            },
        },
        actions=(
            *_r8_ingress_actions("route_to_optical"),
            PlayerAction(
                action_id="enter_zxplate",
                kind=ActionKind.MOVE,
                execution_mode=ExecutionMode.INPUT,
                input_action="move_forward",
                parameters={
                    "goal_trigger": "zxplate",
                    "source_room": "R8",
                    "max_frames": 1200,
                    "stuck_frames": 180,
                    "reach_distance": 4.0,
                    "driver_policy": "steer_to_trigger_via_gameplay_input",
                },
            ),
            PlayerAction(
                action_id="aim_bible_from_zxplate",
                kind=ActionKind.LOOK,
                execution_mode=ExecutionMode.INPUT,
                input_action="mouse_motion",
                parameters={
                    "goal_target": "Interact_R8Bible",
                    "max_frames": 240,
                },
            ),
            PlayerAction(
                action_id="activate_optical_sequence",
                kind=ActionKind.INTERACT,
                execution_mode=ExecutionMode.INTERACTION_PROBE,
                target="Interact_R8Bible",
            ),
            PlayerAction(
                action_id="wait_optical_sequence",
                kind=ActionKind.WAIT,
                execution_mode=ExecutionMode.PHYSICS_WAIT,
                frames=600,
            ),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="zxplate_enter",
                kind="trigger",
                action_id="enter_zxplate",
                match={
                    "room": "R8",
                    "target": "zxplate",
                    "activated": True,
                    "edge": "ENTER",
                    "mechanism": "world_trigger",
                },
            ),
            EvidenceRequirement(
                requirement_id="bible_probe_from_plate",
                kind="interaction_probe",
                action_id="aim_bible_from_zxplate",
                match={
                    "target": "Interact_R8Bible",
                    "reachable": True,
                },
                after_requirement="zxplate_enter",
            ),
            EvidenceRequirement(
                requirement_id="bible_optical_dispatch",
                kind="trigger",
                action_id="activate_optical_sequence",
                match={
                    "target": "Interact_R8Bible",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
                after_requirement="bible_probe_from_plate",
            ),
            EvidenceRequirement(
                requirement_id="lens_look_state",
                kind="state_change",
                action_id="activate_optical_sequence",
                match={
                    "path": "puzzle.R8LensLook",
                    "before": False,
                    "after": True,
                },
                after_requirement="bible_optical_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="raise_timer_state",
                kind="state_change",
                action_id="activate_optical_sequence",
                match={
                    "path": "puzzle.R8RaiseTimer",
                    "before": False,
                    "after": True,
                },
                after_requirement="lens_look_state",
            ),
            EvidenceRequirement(
                requirement_id="optical_start_audio",
                kind="audio",
                action_id="activate_optical_sequence",
                match={"asset": "S121.WAV"},
                after_requirement="raise_timer_state",
            ),
            EvidenceRequirement(
                requirement_id="secret_door_state",
                kind="state_change",
                action_id="wait_optical_sequence",
                match={
                    "path": "puzzle.DoorR8",
                    "before": False,
                    "after": True,
                },
                after_requirement="optical_start_audio",
            ),
            EvidenceRequirement(
                requirement_id="secret_door_audio",
                kind="audio",
                action_id="wait_optical_sequence",
                match={"asset": "799SECDR.WAV"},
                after_requirement="secret_door_state",
            ),
            EvidenceRequirement(
                requirement_id="lens_visual_moved",
                kind="scene_change",
                action_id="wait_optical_sequence",
                match={
                    "observation_id": "r8_lens_motion",
                    "transform_changed": True,
                },
                after_requirement="bible_optical_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="secret_door_visual_rotated",
                kind="scene_change",
                action_id="wait_optical_sequence",
                match={
                    "observation_id": "r8_secret_door_motion",
                    "rotation_changed": True,
                },
                after_requirement="secret_door_state",
            ),
            EvidenceRequirement(
                requirement_id="shield_became_visible",
                kind="scene_change",
                action_id="wait_optical_sequence",
                match={
                    "observation_id": "r8_shield_visibility",
                    "visibility_changed": True,
                    "after_visible": True,
                },
                after_requirement="secret_door_state",
            ),
        ),
        state_expectations=(
            StateExpectation("flags.R8BathDrain", True, True),
            StateExpectation("puzzle.R8LensPlace", True, True),
            StateExpectation("puzzle.R8LensLook", False, True),
            StateExpectation("puzzle.R8RaiseTimer", False, True),
            StateExpectation("puzzle.DoorR8", False, True),
        ),
        metadata={
            "coverage_targets": [
                "gameplay:R8_OPTICAL_START",
                "gameplay:R8_SECRET_DOOR_OPEN",
            ],
            "physical_approach_required": True,
            "activation_trigger": "zxplate",
            "direct_interact_call_allowed": False,
            "scene_observations": [
                {
                    "observation_id": "r8_lens_motion",
                    "node": "lenstop",
                },
                {
                    "observation_id": "r8_secret_door_motion",
                    "node": "door",
                },
                {
                    "observation_id": "r8_shield_visibility",
                    "node": "r8s1",
                },
            ],
            "source_evidence": [
                "gameplay:R8_OPTICAL_START",
                "gameplay:R8_SECRET_DOOR_OPEN",
                "r8_bible_interaction.gd activation-zone boundary",
            ],
            "non_gating_reconstruction": {
                "puzzle.R8Counter": "UNKNOWN opcode semantics",
                "lens_timing": "reconstructed",
                "secret_door_timing": "reconstructed",
            },
        },
    )

    shield = ValidationScenario(
        scenario_id="openazrael.r8.take_shield",
        room="R8",
        setup={
            **base_setup,
            "puzzle": {"DoorR8": True, "R8TakeShield": False},
            "inventory": {"shield": False},
            "flags": {"demo_complete": False},
        },
        actions=(
            *_r8_ingress_actions("route_to_shield"),
            *_actions("Interact_ShieldR8", "shield"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="shield_dispatch",
                kind="trigger",
                action_id="interact_shield",
                match={
                    "target": "Interact_ShieldR8",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
            EvidenceRequirement(
                requirement_id="shield_inventory",
                kind="state_change",
                action_id="interact_shield",
                match={
                    "path": "inventory.shield",
                    "before": False,
                    "after": True,
                },
                after_requirement="shield_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="shield_puzzle_node",
                kind="state_change",
                action_id="interact_shield",
                match={
                    "path": "puzzle.R8TakeShield",
                    "before": False,
                    "after": True,
                },
                after_requirement="shield_dispatch",
            ),
            EvidenceRequirement(
                requirement_id="demo_complete_flag",
                kind="state_change",
                action_id="interact_shield",
                match={
                    "path": "flags.demo_complete",
                    "before": False,
                    "after": True,
                },
                after_requirement="shield_dispatch",
            ),
        ),
        state_expectations=(
            StateExpectation("puzzle.DoorR8", True, True),
            StateExpectation("inventory.shield", False, True),
            StateExpectation("puzzle.R8TakeShield", False, True),
            StateExpectation("flags.demo_complete", False, True),
        ),
        metadata={
            "coverage_targets": ["gameplay:R8_TAKE_SHIELD"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_evidence": "gameplay:R8_TAKE_SHIELD",
        },
    )

    scenarios = (
        lens_pickup,
        lens_blocked,
        lens_place,
        optical,
        shield,
    )
    for scenario in scenarios:
        errors = scenario.validate()
        if errors:
            raise ValueError(
                f"{scenario.scenario_id}: " + "; ".join(errors)
            )
    return scenarios
