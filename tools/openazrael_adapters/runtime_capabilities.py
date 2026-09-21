from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CAPABILITY_SCHEMA = "openazrael.pppv_runtime_capabilities"
CAPABILITY_VERSION = 1


def _read(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def audit_runtime_capabilities(root: Path) -> dict[str, Any]:
    root = root.resolve()
    player = _read(root, "scripts/player.gd")
    probe = _read(root, "scripts/interaction_probe.gd")
    state = _read(root, "scripts/demo_state.gd")
    events = _read(root, "scripts/legacy_event_runner_v87.gd")
    diagnostics = _read(root, "scripts/candidate_diagnostics_v116.gd")
    well = _read(root, "scripts/well_key_interaction.gd")

    checks = {
        "production_player_real_input": (
            'Input.get_vector("move_left", "move_right", "move_forward", "move_back")'
            in player
        ),
        "production_player_move_and_slide": "move_and_slide()" in player,
        "interaction_probe_real_input": (
            'event.is_action_pressed("interact")' in probe
            and "_find_interactive()" in probe
        ),
        "interaction_probe_raycast": (
            "PhysicsRayQueryParameters3D.create" in probe
            and "intersect_ray" in probe
        ),
        "state_inventory_signal": "signal inventory_changed" in state,
        "state_flag_signal": "signal flag_changed" in state,
        "state_puzzle_signal": "signal puzzle_node_changed" in state,
        "state_canonical_hash": "func canonical_state_hash()" in state,
        "logical_audio_signal": "signal logical_audio_event" in events,
        "diagnostic_event_signal": "signal event_recorded" in diagnostics,
        "diagnostic_interaction_event": (
            'record_event("interaction"' in diagnostics
            and "func record_interaction" in diagnostics
        ),
        "diagnostic_world_trigger_event": (
            'record_event("trigger_"' in diagnostics
            and "func observe_trigger" in diagnostics
        ),
        "well_demo_action_step_signal": "signal demo_action_step" in well,
        "well_demo_action_trace": (
            '_step("remove_room:R7Key")' in well
            and '_step("play_sound:979TONGS.WAV")' in well
            and '_step("add_room:R7Key")' in well
            and '_step("remove_room:RustyTongR6")' in well
            and '_step("remove_inventory:TONG6")' in well
            and '_step("default_take:R7Key")' in well
        ),
        "well_uses_recovered_audio_graph": (
            'LegacyEvents.run("R7_WELL_TONGS_USE")' in well
        ),
        "well_consumes_tongs": (
            'DemoState.remove("rusty_tongs")' in well
        ),
    }

    core_keys = [
        "production_player_real_input",
        "production_player_move_and_slide",
        "interaction_probe_real_input",
        "interaction_probe_raycast",
        "state_inventory_signal",
        "state_flag_signal",
        "state_puzzle_signal",
        "state_canonical_hash",
        "logical_audio_signal",
        "diagnostic_event_signal",
        "diagnostic_interaction_event",
        "diagnostic_world_trigger_event",
    ]
    well_keys = [
        "well_demo_action_step_signal",
        "well_demo_action_trace",
        "well_uses_recovered_audio_graph",
        "well_consumes_tongs",
    ]

    core_ready = all(checks[key] for key in core_keys)
    well_exact_ready = core_ready and all(checks[key] for key in well_keys)

    blocked: list[str] = []
    if not core_ready:
        blocked.append("generic_pppv_runtime_core")
    if not well_exact_ready:
        blocked.append("well_tongs_exact_demo_evidence")

    status = "READY" if not blocked else ("PARTIAL" if core_ready else "BLOCKED")
    return {
        "schema": CAPABILITY_SCHEMA,
        "version": CAPABILITY_VERSION,
        "status": status,
        "checks": checks,
        "capabilities": {
            "generic_pppv_runtime_core": core_ready,
            "well_tongs_exact_demo_evidence": well_exact_ready,
        },
        "blocked": blocked,
        "boundary": (
            "Source preflight proves observability hooks exist; it does not prove "
            "a Godot runtime scenario passes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit OpenAzrael source/runtime hooks required by PPPV."
    )
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-core",
        action="store_true",
        help="Exit non-zero when generic PPPV core hooks are unavailable.",
    )
    parser.add_argument(
        "--require-well-exact",
        action="store_true",
        help="Exit non-zero when exact Well+Tongs evidence hooks are unavailable.",
    )
    args = parser.parse_args()

    report = audit_runtime_capabilities(args.root)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    caps = report["capabilities"]
    if args.require_core and not caps["generic_pppv_runtime_core"]:
        return 1
    if args.require_well_exact and not caps["well_tongs_exact_demo_evidence"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
