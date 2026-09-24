from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts" / "room_manager.gd"
RUNNER = ROOT / "scripts" / "kg001_transition_continuity_runner_v163.gd"
GUARD = ROOT / "scripts" / "validation" / "pppv_runtime_guard.gd"


def check(name: str, ok: bool, failed: list[str]) -> None:
    if not ok:
        failed.append(name)


def main() -> int:
    manager = MANAGER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    guard = GUARD.read_text(encoding="utf-8")
    failed: list[str] = []

    process = manager.split("func _process", 1)[1]
    check("production_uses_continuity_transition_helper", "_transition_room_through_portal(tr)" in process, failed)
    check("production_no_fixed_portal_spawn_for_transition", "load_room_at_portal(dest, dest_view)" not in process, failed)
    check("source_portal_semantics_used", 'transition.get("source_view"' in manager, failed)
    check("destination_portal_semantics_used", 'transition.get("destination_view"' in manager, failed)
    check("source_depth_preserved", "source_depth" in manager and "preferred_depth" in manager, failed)
    check("lateral_offset_preserved", "desired_lateral" in manager and "-source_lateral" in manager, failed)
    check("floor_supported_solution", "_supported_transition_spawn" in manager, failed)
    check("velocity_mapped", "mapped_velocity" in manager, failed)
    check("continuity_evidence", '"continuity_logical_jump"' in manager, failed)
    check("fallback_exposed", '"continuity_fallback"' in manager, failed)

    for token in (
        '"R1_R7"', '"R7_R1"', '"R1_R8"', '"R8_R1"',
        'MAX_LOGICAL_JUMP := 8.0',
        'MAX_DEPTH_JUMP := 2.0',
        'MAX_LATERAL_JUMP := 2.0',
        'SUPPORT_FRAMES := 30',
        'Input.action_press(&"move_forward"',
        'portal_spawn_expectation',
        'continuity_fallback',
    ):
        check("runner_" + token.replace('"', "").replace(" ", "_"), token in runner, failed)
    check("runner_no_position_teleport", "player.global_position =" not in runner, failed)
    check("runner_no_direct_spawn_helper", "_spawn_at_portal" not in runner, failed)

    check("guard_continuity_threshold", "DEFAULT_MAX_TRANSITION_LOGICAL_JUMP := 8.0" in guard, failed)
    check("guard_rejects_fallback", "not continuity_fallback" in guard, failed)
    check("guard_uses_initial_position_error", "initial_position_error" in guard, failed)
    check("guard_support_30_frames", "for support_frame in range(30)" in guard, failed)

    payload = {
        "schema": "openazrael.kg001.transition_continuity_source_validation",
        "version": 163,
        "status": "PASS" if not failed else "FAIL",
        "failed": failed,
    }
    print(json.dumps(payload, separators=(",", ":")))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
