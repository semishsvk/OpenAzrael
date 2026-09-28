from __future__ import annotations

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


# Recovered/audited physical R1 corridor route from v119/v141. These are not
# teleport destinations: each point is reached through production player input.
R1_ROUTE = (
    (-203.801173, -84.921990, 300.265764),
    (-168.693718, -91.949649, 281.939643),
    (-113.787899, -107.514682, 201.650247),
    (-72.816896, -114.240783, 116.816224),
    (-75.0, -114.300000, 70.0),
    (-75.0, -114.300000, 20.0),
    (-50.0, -114.300000, -20.0),
    (0.0, -115.000000, -50.0),
    (38.260757, -115.691564, -50.391974),
    (95.934301, -117.355663, -127.453640),
    (141.988445, -115.622030, -209.540090),
    (119.250000, -114.455000, -261.236000),
    (156.921000, -114.276000, -313.508000),
    (203.566000, -114.275000, -324.678000),
    (210.088000, -114.364000, -410.699000),
    (266.328000, -114.240000, -415.593000),
    (299.061000, -110.726000, -486.612000),
    (356.752000, -108.708000, -475.156000),
    (405.288000, -99.161000, -522.654000),
    (449.221720, -93.255052, -498.865461),
    (476.420000, -85.030000, -514.950000),
    (529.295811, -84.205500, -513.041569),
)
R1_PRE_DOOR2_ROUTE = R1_ROUTE[:-1]


def _world_waypoint(point: tuple[float, float, float], action_id: str) -> PlayerAction:
    return PlayerAction(
        action_id=action_id,
        kind=ActionKind.MOVE,
        execution_mode=ExecutionMode.INPUT,
        input_action="move_forward",
        parameters={
            "goal_world_point": list(point),
            "driver_policy": "audited_world_waypoint_v119_v141",
            "max_frames": 900,
            "stuck_frames": 150,
            "reach_distance": 18.0,
        },
    )


def _route_actions(
    points: tuple[tuple[float, float, float], ...],
    prefix: str,
) -> tuple[PlayerAction, ...]:
    return tuple(
        _world_waypoint(point, f"{prefix}_{index:02d}")
        for index, point in enumerate(points)
    )


def _approach_and_interact(
    *,
    target: str,
    approach_id: str,
    interact_id: str,
) -> tuple[PlayerAction, PlayerAction, PlayerAction]:
    return (
        PlayerAction(
            action_id=approach_id,
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
        ),
        PlayerAction(
            action_id=approach_id + "_aim",
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
            action_id=interact_id,
            kind=ActionKind.INTERACT,
            execution_mode=ExecutionMode.INTERACTION_PROBE,
            target=target,
        ),
    )


def build_r1_interaction_scenarios() -> tuple[ValidationScenario, ...]:
    common_setup = {
        "reset_room_state": True,
        "spawn_view": "spaview",
        "lock_room_transitions": True,
    }

    pickup = ValidationScenario(
        scenario_id="openazrael.r1.pickup_tongs",
        room="R1",
        setup={
            **common_setup,
            "inventory": {"rusty_tongs": False},
            "flags": {"R1Door1Open": True},
        },
        actions=(
            *_route_actions(R1_PRE_DOOR2_ROUTE, "route_to_tongs"),
            *_approach_and_interact(
                target="Interact_TONG6",
                approach_id="approach_tongs",
                interact_id="take_tongs",
            ),
            *_route_actions(
                tuple(reversed(R1_PRE_DOOR2_ROUTE)),
                "route_back_to_r7",
            ),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="tongs_reachable",
                kind="interaction_probe",
                action_id="approach_tongs_aim",
                match={"target": "Interact_TONG6", "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="tongs_interaction_dispatched",
                kind="trigger",
                action_id="take_tongs",
                match={"target": "Interact_TONG6", "activated": True},
                after_requirement="tongs_reachable",
            ),
            EvidenceRequirement(
                requirement_id="tongs_inventory_change",
                kind="state_change",
                action_id="take_tongs",
                match={
                    "path": "inventory.rusty_tongs",
                    "before": False,
                    "after": True,
                },
                after_requirement="tongs_interaction_dispatched",
            ),
        ),
        state_expectations=(
            StateExpectation("inventory.rusty_tongs", False, True),
            StateExpectation("flags.R1Door1Open", True, True),
        ),
        metadata={
            "coverage_targets": ["interaction:R1:TONG6"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_runtime": "RoomManager.PICKUPS + pickup.gd",
            "route_source": "v119/v141 audited R1 corridor",
            "route_policy": "production input only; no teleport",
        },
    )

    door1 = ValidationScenario(
        scenario_id="openazrael.r1.open_door1",
        room="R1",
        setup=common_setup,
        actions=_approach_and_interact(
            target="Interact_doorcor01",
            approach_id="approach_door1",
            interact_id="open_door1",
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="door1_reachable",
                kind="interaction_probe",
                action_id="approach_door1_aim",
                match={"target": "Interact_doorcor01", "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="door1_interaction_dispatched",
                kind="trigger",
                action_id="open_door1",
                match={"target": "Interact_doorcor01", "activated": True},
                after_requirement="door1_reachable",
            ),
            EvidenceRequirement(
                requirement_id="door1_flag_change",
                kind="state_change",
                action_id="open_door1",
                match={
                    "path": "flags.R1Door1Open",
                    "before": False,
                    "after": True,
                },
                after_requirement="door1_interaction_dispatched",
            ),
        ),
        state_expectations=(
            StateExpectation("flags.R1Door1Open", False, True),
        ),
        metadata={
            "coverage_targets": ["interaction:R1:doorcor01"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_runtime": "r1_door_interaction.gd",
        },
    )

    door2_positive = ValidationScenario(
        scenario_id="openazrael.r1.open_door2",
        room="R1",
        setup={
            **common_setup,
            "inventory": {"well_key": True},
            "flags": {"R1Door1Open": True},
        },
        actions=(
            *_route_actions(R1_PRE_DOOR2_ROUTE, "route_to_door2"),
            *_approach_and_interact(
                target="Interact_doorcor2",
                approach_id="approach_door2",
                interact_id="open_door2",
            ),
            _world_waypoint(R1_ROUTE[-1], "route_through_door2"),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="door2_reachable",
                kind="interaction_probe",
                action_id="approach_door2_aim",
                match={"target": "Interact_doorcor2", "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="door2_interaction_dispatched",
                kind="trigger",
                action_id="open_door2",
                match={"target": "Interact_doorcor2", "activated": True},
                after_requirement="door2_reachable",
            ),
            EvidenceRequirement(
                requirement_id="door2_unlock_flag",
                kind="state_change",
                action_id="open_door2",
                match={
                    "path": "flags.FR1DoorUnlocked",
                    "before": False,
                    "after": True,
                },
                after_requirement="door2_interaction_dispatched",
            ),
            EvidenceRequirement(
                requirement_id="door2_open_flag",
                kind="state_change",
                action_id="open_door2",
                match={
                    "path": "flags.R1Door2Open",
                    "before": False,
                    "after": True,
                },
                after_requirement="door2_unlock_flag",
            ),
        ),
        state_expectations=(
            StateExpectation("inventory.well_key", True, True),
            StateExpectation("flags.R1Door1Open", True, True),
            StateExpectation("flags.FR1DoorUnlocked", False, True),
            StateExpectation("flags.R1Door2Open", False, True),
        ),
        metadata={
            "coverage_targets": ["interaction:R1:doorcor2"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "precondition": "inventory.well_key",
            "source_runtime": "r1_door_interaction.gd",
        },
    )

    door2_negative = ValidationScenario(
        scenario_id="openazrael.r1.open_door2.negative_without_key",
        room="R1",
        setup={
            **common_setup,
            "inventory": {"well_key": False},
            "flags": {"R1Door1Open": True},
        },
        actions=(
            *_route_actions(R1_PRE_DOOR2_ROUTE, "route_to_locked_door2"),
            *_approach_and_interact(
                target="Interact_doorcor2",
                approach_id="approach_locked_door2",
                interact_id="try_locked_door2",
            ),
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="locked_door2_reachable",
                kind="interaction_probe",
                action_id="approach_locked_door2_aim",
                match={"target": "Interact_doorcor2", "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="locked_door2_dispatch",
                kind="trigger",
                action_id="try_locked_door2",
                match={"target": "Interact_doorcor2", "activated": True},
                after_requirement="locked_door2_reachable",
            ),
        ),
        forbidden=(
            EvidenceRequirement(
                requirement_id="no_unlock_without_key",
                kind="state_change",
                match={"path": "flags.FR1DoorUnlocked", "after": True},
            ),
            EvidenceRequirement(
                requirement_id="no_open_without_key",
                kind="state_change",
                match={"path": "flags.R1Door2Open", "after": True},
            ),
        ),
        state_expectations=(
            StateExpectation("inventory.well_key", False, False),
            StateExpectation("flags.FR1DoorUnlocked", False, False),
            StateExpectation("flags.R1Door2Open", False, False),
        ),
        metadata={
            "coverage_targets": ["interaction:R1:doorcor2:negative"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "negative_precondition": True,
            "source_runtime": "r1_door_interaction.gd",
        },
    )

    scenarios = (pickup, door1, door2_positive, door2_negative)
    for scenario in scenarios:
        errors = scenario.validate()
        if errors:
            raise ValueError(
                f"{scenario.scenario_id}: " + "; ".join(errors)
            )
    return scenarios
