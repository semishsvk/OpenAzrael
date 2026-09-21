from __future__ import annotations

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


def _approach_and_interact(
    *,
    target: str,
    approach_id: str,
    interact_id: str,
) -> tuple[PlayerAction, PlayerAction]:
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
            "puzzle": {"PickupCollected:rusty_tongs": False},
        },
        actions=_approach_and_interact(
            target="Interact_TONG6",
            approach_id="approach_tongs",
            interact_id="take_tongs",
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="tongs_reachable",
                kind="interaction_probe",
                action_id="approach_tongs",
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
            EvidenceRequirement(
                requirement_id="tongs_pickup_marker_change",
                kind="state_change",
                action_id="take_tongs",
                match={
                    "path": "puzzle.PickupCollected:rusty_tongs",
                    "before": False,
                    "after": True,
                },
                after_requirement="tongs_interaction_dispatched",
            ),
        ),
        state_expectations=(
            StateExpectation("inventory.rusty_tongs", False, True),
            StateExpectation(
                "puzzle.PickupCollected:rusty_tongs",
                False,
                True,
            ),
        ),
        metadata={
            "coverage_targets": ["interaction:R1:TONG6"],
            "physical_approach_required": True,
            "direct_interact_call_allowed": False,
            "source_runtime": "RoomManager.PICKUPS + pickup.gd",
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
                action_id="approach_door1",
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
        },
        actions=_approach_and_interact(
            target="Interact_doorcor2",
            approach_id="approach_door2",
            interact_id="open_door2",
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="door2_reachable",
                kind="interaction_probe",
                action_id="approach_door2",
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
        },
        actions=_approach_and_interact(
            target="Interact_doorcor2",
            approach_id="approach_locked_door2",
            interact_id="try_locked_door2",
        ),
        requirements=(
            EvidenceRequirement(
                requirement_id="locked_door2_reachable",
                kind="interaction_probe",
                action_id="approach_locked_door2",
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
