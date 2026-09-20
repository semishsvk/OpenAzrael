from __future__ import annotations

from typing import Any

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    ValidationScenario,
)


def adapt_physical_traversal_contract(
    payload: dict[str, Any],
) -> tuple[ValidationScenario, ...]:
    expected_schema = "openazrael.kg001.physical_traversal_contract"
    if payload.get("schema") != expected_schema:
        raise ValueError(f"expected schema {expected_schema}")

    floor = payload.get("floor_regression", {})
    floor_room = str(floor.get("room", "R1"))
    scenarios: list[ValidationScenario] = [
        ValidationScenario(
            scenario_id="openazrael.r1.floor_traversal",
            room=floor_room,
            setup={
                "spawn_view": floor.get("spawn_view"),
                "reset_velocity": True,
            },
            actions=(
                PlayerAction(
                    action_id="r1_forward",
                    kind=ActionKind.MOVE,
                    execution_mode=ExecutionMode.INPUT,
                    input_action="move_forward",
                    parameters={"direction": "canonical_forward"},
                ),
                PlayerAction(
                    action_id="r1_back",
                    kind=ActionKind.MOVE,
                    execution_mode=ExecutionMode.INPUT,
                    input_action="move_back",
                    parameters={"direction": "canonical_back"},
                ),
            ),
            requirements=(
                EvidenceRequirement(
                    requirement_id="r1_forward_support",
                    kind="collision_support",
                    match={
                        "action_id": "r1_forward",
                        "continuous": True,
                        "fell_through": False,
                    },
                ),
                EvidenceRequirement(
                    requirement_id="r1_back_support",
                    kind="collision_support",
                    match={
                        "action_id": "r1_back",
                        "continuous": True,
                        "fell_through": False,
                    },
                ),
                EvidenceRequirement(
                    requirement_id="r1_forward_progress",
                    kind="movement",
                    match={"action_id": "r1_forward", "progress_ok": True},
                ),
                EvidenceRequirement(
                    requirement_id="r1_back_progress",
                    kind="movement",
                    match={"action_id": "r1_back", "progress_ok": True},
                ),
            ),
            metadata={
                "source_version": payload.get("version"),
                "stationary_only_evidence_accepted": False,
                "direct_horizontal_velocity_injection_accepted": False,
                "production_path": payload.get("production_path", {}),
            },
        )
    ]

    for stair in payload.get("stair_regressions", []):
        mesh = str(stair["mesh"])
        room = str(stair.get("room", "R8"))
        safe = mesh.replace("/", "_").replace(" ", "_")
        scenarios.append(
            ValidationScenario(
                scenario_id=f"openazrael.{room.lower()}.stairs.{safe}",
                room=room,
                setup={
                    "stair_mesh": mesh,
                    "probe_real_landings": True,
                },
                actions=(
                    PlayerAction(
                        action_id="ascend",
                        kind=ActionKind.MOVE,
                        execution_mode=ExecutionMode.INPUT,
                        input_action="move_forward",
                        parameters={
                            "mesh": mesh,
                            "goal": "upper_landing",
                            "direction": "ascending",
                        },
                    ),
                    PlayerAction(
                        action_id="descend",
                        kind=ActionKind.MOVE,
                        execution_mode=ExecutionMode.INPUT,
                        input_action="move_forward",
                        parameters={
                            "mesh": mesh,
                            "goal": "lower_landing",
                            "direction": "descending",
                        },
                    ),
                ),
                requirements=(
                    EvidenceRequirement(
                        requirement_id="ascent",
                        kind="stair_traversal",
                        match={
                            "mesh": mesh,
                            "direction": "ascending",
                            "progress_ok": True,
                            "height_ok": True,
                            "fell_through": False,
                        },
                    ),
                    EvidenceRequirement(
                        requirement_id="descent",
                        kind="stair_traversal",
                        match={
                            "mesh": mesh,
                            "direction": "descending",
                            "progress_ok": True,
                            "height_ok": True,
                            "fell_through": False,
                        },
                    ),
                ),
                metadata={
                    "source_version": payload.get("version"),
                    "minimum_tread_levels": stair.get("minimum_tread_levels"),
                    "audited_total_rise": stair.get("audited_total_rise"),
                    "audited_horizontal_run": stair.get("audited_horizontal_run"),
                    "approximate_rise_per_step": stair.get(
                        "approximate_rise_per_step"
                    ),
                    "real_imported_geometry_required": True,
                    "fake_stair_fixture_allowed": False,
                },
            )
        )

    for scenario in scenarios:
        errors = scenario.validate()
        if errors:
            raise ValueError("; ".join(errors))
    return tuple(scenarios)
