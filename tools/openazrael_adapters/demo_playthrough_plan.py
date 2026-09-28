from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.remaster_framework.playthrough import (
    PlaythroughStep,
    StepKind,
    StepStatus,
    build_playthrough_plan,
)


COMPLETE_HASH = "b695fb49c389376c8815af54d743aba20e2f9753852342c8619187b2f4ab6b9d"

# Runtime-derived, source-geometry-backed physical routes needed only when
# scenarios are chained continuously instead of starting at canonical portals.
R7_WELL_TO_SWITCHBOARD_ROUTE = (
    (-21.4, -47.57, 51.4),
    (-24.0, -47.57, 78.0),
    (-8.0, -41.45, 78.0),
    (25.0, -41.45, 70.0),
    (45.0, -41.45, 80.0),
)
R7_SWITCHBOARD_TO_EXIT_ROUTE = (
    (45.0, -41.45, 60.0),
    (38.0, -41.45, 30.0),
    (30.0, -41.45, 0.0),
    (30.0, -41.45, -35.0),
    (50.0, -41.56, -55.0),
    (65.0, -41.56, -85.0),
)

def _entry_route(points, prefix: str, policy: str) -> list[dict[str, Any]]:
    return [
        {
            "action_id": f"{prefix}_{index:02d}",
            "kind": "move",
            "execution_mode": "input",
            "input_action": "move_forward",
            "parameters": {
                "goal_world_point": list(point),
                "driver_policy": policy,
                "max_frames": 900,
                "stuck_frames": 150,
                "reach_distance": 8.0,
            },
        }
        for index, point in enumerate(points)
    ]


def _scenario_ids(bundle: dict[str, Any]) -> set[str]:
    rows = bundle.get("scenarios", [])
    if not isinstance(rows, list):
        return set()
    return {
        str(row.get("scenario_id"))
        for row in rows
        if isinstance(row, dict) and row.get("scenario_id")
    }


def _scenario_step(
    step_id: str,
    room: str,
    desired_scenario_id: str,
    available: set[str],
    *,
    required_state_paths: tuple[str, ...] = (),
    purpose: str,
    playthrough_entry_actions: list[dict[str, Any]] | None = None,
    skip_action_prefixes: tuple[str, ...] = (),
) -> PlaythroughStep:
    ready = desired_scenario_id in available
    return PlaythroughStep(
        step_id=step_id,
        kind=StepKind.SCENARIO,
        status=StepStatus.READY if ready else StepStatus.AUTHORING_REQUIRED,
        room=room,
        scenario_id=desired_scenario_id if ready else None,
        required_state_paths=required_state_paths,
        metadata={
            "desired_scenario_id": desired_scenario_id,
            "purpose": purpose,
            **(
                {"playthrough_entry_actions": playthrough_entry_actions}
                if playthrough_entry_actions
                else {}
            ),
            **(
                {"skip_action_prefixes": list(skip_action_prefixes)}
                if skip_action_prefixes
                else {}
            ),
        },
    )


def _transition_step(
    step_id: str,
    source_room: str,
    destination_room: str,
    trigger: str,
    desired_scenario_id: str,
    available: set[str],
    *,
    purpose: str,
    playthrough_entry_actions: list[dict[str, Any]] | None = None,
) -> PlaythroughStep:
    ready = desired_scenario_id in available
    return PlaythroughStep(
        step_id=step_id,
        kind=StepKind.TRANSITION,
        status=StepStatus.READY if ready else StepStatus.AUTHORING_REQUIRED,
        scenario_id=desired_scenario_id if ready else None,
        source_room=source_room,
        destination_room=destination_room,
        trigger=trigger,
        metadata={
            "desired_scenario_id": desired_scenario_id,
            "purpose": purpose,
            "forbid_trigger_centroid_teleport": True,
            **(
                {"playthrough_entry_actions": playthrough_entry_actions}
                if playthrough_entry_actions
                else {}
            ),
        },
    )

def build_openazrael_demo_playthrough_plan(
    scenario_bundle: dict[str, Any],
) -> dict[str, Any]:
    available = _scenario_ids(scenario_bundle)
    steps: list[PlaythroughStep] = [
        _scenario_step(
            "S01_OPEN_DOOR1",
            "R1",
            "openazrael.r1.open_door1",
            available,
            required_state_paths=("flags.R1Door1Open",),
            purpose=(
                "Open the physical R1 corridor before attempting the TONG6 "
                "route, matching the audited v119/v141 traversal."
            ),
        ),
        _scenario_step(
            "S02_PICKUP_TONGS",
            "R1",
            "openazrael.r1.pickup_tongs",
            available,
            required_state_paths=(
                "flags.R1Door1Open",
                "inventory.rusty_tongs",
            ),
            purpose=(
                "Traverse the audited R1 corridor, acquire TONG6 through "
                "production pickup interaction, and return toward R7."
            ),
        ),
        _transition_step(
            "T03_R1_TO_R7",
            "R1",
            "R7",
            "zxcoriR5",
            "openazrael.transition.r1_to_r7",
            available,
            purpose="Cross the live transition by physical player movement.",
        ),
        _scenario_step(
            "S04_WELL_TONGS",
            "R7",
            "openazrael.r7.well_tongs.positive",
            available,
            required_state_paths=(
                "inventory.rusty_tongs",
                "inventory.well_key",
                "puzzle.R7KeyTake",
                "flags.R7key",
            ),
            purpose="Retrieve the Well Key with the recovered TONG6 action stream.",
        ),
        _scenario_step(
            "S05_SWITCHBOARD",
            "R7",
            "openazrael.r7.water_switchboard",
            available,
            required_state_paths=("flags.R8BathDrain",),
            purpose="Solve the R7 water switchboard through physical interactions.",
            playthrough_entry_actions=_entry_route(
                R7_WELL_TO_SWITCHBOARD_ROUTE,
                "route_from_well",
                "source_derived_r7_well_to_switchboard",
            ),
        ),
        PlaythroughStep(
            step_id="C06_POST_R7_SAVELOAD",
            kind=StepKind.CHECKPOINT,
            status=StepStatus.READY,
            room="R7",
            checkpoint_id="post_r7_solved",
            required_state_paths=(
                "inventory.well_key",
                "flags.R8BathDrain",
            ),
            metadata={
                "require_save_restore_hash_identity": True,
                "source_oracle": "KG-001 v109 canonical state roundtrip",
            },
        ),
        _transition_step(
            "T07_R7_TO_R1",
            "R7",
            "R1",
            "zxwell2R6",
            "openazrael.transition.r7_to_r1",
            available,
            purpose="Return to R1 by physically crossing the authored trigger.",
            playthrough_entry_actions=_entry_route(
                R7_SWITCHBOARD_TO_EXIT_ROUTE,
                "route_r7_exit",
                "source_derived_r7_exit_route",
            ),
        ),
        _scenario_step(
            "S08_OPEN_DOOR2",
            "R1",
            "openazrael.r1.open_door2",
            available,
            required_state_paths=("flags.R1Door2Open", "flags.FR1DoorUnlocked"),
            purpose="Unlock/open the R8 route using the Well Key.",
        ),
        _transition_step(
            "T09_R1_TO_R8",
            "R1",
            "R8",
            "zxcoriR2",
            "openazrael.transition.r1_to_r8",
            available,
            purpose="Enter R8 through the live production transition.",
        ),
        _scenario_step(
            "S10_TAKE_LENS",
            "R8",
            "openazrael.r8.take_lens",
            available,
            required_state_paths=("inventory.r8_lens", "flags.R8Lens"),
            purpose="Acquire the lens through production interaction.",
        ),
        _scenario_step(
            "S11_PLACE_LENS",
            "R8",
            "openazrael.r8.place_lens",
            available,
            required_state_paths=("puzzle.R8LensPlace",),
            purpose="Place the recovered lens on the stone Bible.",
        ),
        _scenario_step(
            "S11_OPTICAL_SEQUENCE",
            "R8",
            "openazrael.r8.optical_sequence",
            available,
            required_state_paths=("puzzle.R8LensPlace", "puzzle.DoorR8"),
            purpose="Place the lens, trigger the optical sequence and open DoorR8.",
        ),
        PlaythroughStep(
            step_id="C12_POST_DOOR_R8_SAVELOAD",
            kind=StepKind.CHECKPOINT,
            status=StepStatus.READY,
            room="R8",
            checkpoint_id="post_r8_secret_door",
            required_state_paths=("puzzle.R8LensPlace", "puzzle.DoorR8"),
            metadata={
                "require_save_restore_hash_identity": True,
                "source_oracle": "KG-001 v109 canonical state roundtrip",
            },
        ),
        _scenario_step(
            "S13_TAKE_SHIELD",
            "R8",
            "openazrael.r8.take_shield",
            available,
            required_state_paths=("inventory.shield", "flags.demo_complete"),
            purpose="Take the shield and reach demo completion.",
            skip_action_prefixes=("route_to_shield_",),
        ),
        PlaythroughStep(
            step_id="C14_FINAL_STATE",
            kind=StepKind.CHECKPOINT,
            status=StepStatus.READY,
            room="R8",
            checkpoint_id="demo_complete",
            required_state_paths=("inventory.shield", "flags.demo_complete"),
            metadata={
                "expected_state_sha256": COMPLETE_HASH,
                "require_save_restore_hash_identity": True,
            },
        ),
    ]

    return build_playthrough_plan(
        project="OpenAzrael",
        plan_id="kg001_demo_real_player_v1",
        steps=steps,
        success_state_sha256=COMPLETE_HASH,
        metadata={
            "route": ["R1", "R7", "R1", "R8"],
            "legacy_oracles": ["v109", "v110", "v111", "v117", "v118"],
            "v111_role": (
                "historical production-interaction regression oracle only; "
                "not accepted as real-player traversal evidence"
            ),
            "full_demo_real_player_required": True,
            "runtime_validation_status": "NOT_EXECUTED",
            "chained_execution_implemented": True,
            "status_meaning": "scenario_authoring_readiness_only",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the OpenAzrael real-player KG-001 demo orchestration plan."
    )
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.scenarios.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        raise ValueError("scenario bundle must be an object")
    plan = build_openazrael_demo_playthrough_plan(bundle)
    rendered = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
