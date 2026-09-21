from __future__ import annotations

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    StateExpectation,
    ValidationScenario,
)


def _actions(target: str, prefix: str) -> tuple[PlayerAction, PlayerAction]:
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
        actions=_actions("Interact_R8Lens", "lens"),
        requirements=(
            EvidenceRequirement(
                requirement_id="lens_reachable",
                kind="interaction_probe",
                match={"target": "Interact_R8Lens", "reachable": True},
            ),
            EvidenceRequirement(
                requirement_id="lens_dispatch",
                kind="trigger",
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
        actions=_actions("Interact_R8Lens", "submerged_lens"),
        requirements=(
            EvidenceRequirement(
                requirement_id="submerged_lens_dispatch",
                kind="trigger",
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
        actions=_actions("Interact_R8Bible", "bible_place_lens"),
        requirements=(
            EvidenceRequirement(
                requirement_id="bible_lens_dispatch",
                kind="trigger",
                match={
                    "target": "Interact_R8Bible",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
            EvidenceRequirement(
                requirement_id="lens_removed_from_inventory",
                kind="state_change",
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

    shield = ValidationScenario(
        scenario_id="openazrael.r8.take_shield",
        room="R8",
        setup={
            **base_setup,
            "puzzle": {"DoorR8": True, "R8TakeShield": False},
            "inventory": {"shield": False},
            "flags": {"demo_complete": False},
        },
        actions=_actions("Interact_ShieldR8", "shield"),
        requirements=(
            EvidenceRequirement(
                requirement_id="shield_dispatch",
                kind="trigger",
                match={
                    "target": "Interact_ShieldR8",
                    "activated": True,
                    "mechanism": "interaction_dispatch",
                },
            ),
            EvidenceRequirement(
                requirement_id="shield_inventory",
                kind="state_change",
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

    scenarios = (lens_pickup, lens_blocked, lens_place, shield)
    for scenario in scenarios:
        errors = scenario.validate()
        if errors:
            raise ValueError(
                f"{scenario.scenario_id}: " + "; ".join(errors)
            )
    return scenarios
