from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.kg001_state_space_v108 import (
    ACTION_NAMES,
    SWITCH_SOLUTION,
    DemoState,
    Model,
    explore,
    validate_inputs,
    validate_source_contract,
)
from tools.remaster_framework.state_fuzz import (
    StateFuzzConfig,
    run_state_fuzz,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "openazrael.kg001.state_fuzz"
VERSION = 119
ALLOWED_ROOMS = {"R1", "R7", "R8"}
CONSUMABLE_INVENTORY = {"rusty_tongs", "r8_lens"}
ACTION_AUDIO = {
    "retrieve_well_key": {"979TONGS.WAV"},
    "switch_well_lev02": {"S152V2.WAV"},
    "place_r8_lens": {"S137.WAV"},
    "start_optical_sequence": {"S121.WAV"},
    "finish_optical_sequence": {"799SECDR.WAV"},
}
MONOTONIC_FLAGS = {
    "R1Door1Open",
    "FR1DoorUnlocked",
    "R1Door2Open",
    "R7key",
    "R7waterswitchboard",
    "R8BathDrain",
    "R8Lens",
    "demo_complete",
}
MONOTONIC_PUZZLE = {
    "PickupCollected:rusty_tongs",
    "R7KeyTake",
    "R8LensPlace",
    "R8LensLook",
    "R8RaiseTimer",
    "R8Counter",
    "DoorR8",
    "R8TakeShield",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state_key(state: DemoState) -> str:
    payload = [
        state.room,
        list(state.inventory),
        list(state.flags),
        list(state.puzzle_nodes),
        list(state.values),
        state.sequence_running,
    ]
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dict(items: tuple) -> dict[str, Any]:
    return dict(items)


def _state_invariants(state: DemoState) -> list[str]:
    errors: list[str] = []
    inventory = _dict(state.inventory)
    flags = _dict(state.flags)
    puzzle = _dict(state.puzzle_nodes)
    values = _dict(state.values)

    if state.room not in ALLOWED_ROOMS:
        errors.append(f"unknown room {state.room!r}")

    step = values.get("R7SwitchStep", 0)
    if not isinstance(step, int) or isinstance(step, bool):
        errors.append("R7SwitchStep must be an integer")
    elif not 0 <= step <= len(SWITCH_SOLUTION):
        errors.append(f"R7SwitchStep out of range: {step}")

    tongs_collected = puzzle.get(
        "PickupCollected:rusty_tongs",
        False,
    )
    if inventory.get("rusty_tongs", False) and not tongs_collected:
        errors.append(
            "rusty_tongs inventory requires persistent pickup marker"
        )

    if inventory.get("well_key", False):
        if not tongs_collected:
            errors.append(
                "well_key requires prior persistent TONG6 pickup marker"
            )
        if inventory.get("rusty_tongs", False):
            errors.append("well_key acquired while rusty_tongs still present")
        if not puzzle.get("R7KeyTake", False):
            errors.append("well_key requires R7KeyTake")
        if not flags.get("R7key", False):
            errors.append("well_key requires R7key")

    if puzzle.get("R7KeyTake", False) or flags.get("R7key", False):
        if not inventory.get("well_key", False):
            errors.append("R7 key state requires well_key inventory")

    if flags.get("R1Door2Open", False):
        if not flags.get("FR1DoorUnlocked", False):
            errors.append("R1Door2Open requires FR1DoorUnlocked")
        if not inventory.get("well_key", False):
            errors.append("R1Door2Open requires persistent well_key")

    if puzzle.get("R8LensPlace", False):
        if inventory.get("r8_lens", False):
            errors.append("placed R8 lens cannot remain in inventory")
        if not flags.get("R8BathDrain", False):
            errors.append("R8LensPlace requires drained bath")
        if not flags.get("R8Lens", False):
            errors.append("R8LensPlace requires R8Lens acquisition flag")

    if puzzle.get("R8LensLook", False) and not puzzle.get(
        "R8LensPlace", False
    ):
        errors.append("R8LensLook requires R8LensPlace")

    if puzzle.get("R8RaiseTimer", False) and not puzzle.get(
        "R8LensLook", False
    ):
        errors.append("R8RaiseTimer requires R8LensLook")

    if puzzle.get("DoorR8", False):
        if not puzzle.get("R8RaiseTimer", False):
            errors.append("DoorR8 requires R8RaiseTimer")
        if not puzzle.get("R8LensPlace", False):
            errors.append("DoorR8 requires R8LensPlace")

    if flags.get("demo_complete", False):
        if not puzzle.get("DoorR8", False):
            errors.append("demo_complete requires DoorR8")
        if not puzzle.get("R8TakeShield", False):
            errors.append("demo_complete requires R8TakeShield")
        if not inventory.get("shield", False):
            errors.append("demo_complete requires shield inventory")

    if state.sequence_running:
        if state.room != "R8":
            errors.append("optical sequence may run only in R8")
        if not puzzle.get("R8LensPlace", False):
            errors.append("running optical sequence requires R8LensPlace")
        if puzzle.get("DoorR8", False):
            errors.append("optical sequence cannot run after DoorR8")

    return errors


def _transition_invariants(
    before: DemoState,
    action: str,
    after: DemoState,
    audio: tuple[str, ...],
) -> list[str]:
    errors: list[str] = []
    before_flags = _dict(before.flags)
    after_flags = _dict(after.flags)
    before_puzzle = _dict(before.puzzle_nodes)
    after_puzzle = _dict(after.puzzle_nodes)
    before_inventory = _dict(before.inventory)
    after_inventory = _dict(after.inventory)

    for key in MONOTONIC_FLAGS:
        if before_flags.get(key, False) and not after_flags.get(key, False):
            errors.append(f"monotonic flag regressed: {key}")

    for key in MONOTONIC_PUZZLE:
        if before_puzzle.get(key, False) and not after_puzzle.get(key, False):
            errors.append(f"monotonic puzzle node regressed: {key}")

    for key, value in before_inventory.items():
        if (
            value
            and key not in CONSUMABLE_INVENTORY
            and not after_inventory.get(key, False)
        ):
            errors.append(f"persistent inventory item disappeared: {key}")

    if action == "pickup_rusty_tongs" and after != before:
        if not after_inventory.get("rusty_tongs", False):
            errors.append("pickup_rusty_tongs did not grant inventory item")
        if not after_puzzle.get(
            "PickupCollected:rusty_tongs",
            False,
        ):
            errors.append(
                "pickup_rusty_tongs did not persist collection marker"
            )

    allowed_audio = ACTION_AUDIO.get(action, set())
    unexpected_audio = sorted(set(audio) - allowed_audio)
    if unexpected_audio:
        errors.append(
            f"unexpected audio for {action}: {unexpected_audio}"
        )

    if action.startswith("transition_"):
        if before.persistent_hash() != after.persistent_hash():
            errors.append(
                f"{action} mutated persistent state during room transition"
            )

    if action == "retrieve_well_key" and after != before:
        if after_inventory.get("rusty_tongs", False):
            errors.append("retrieve_well_key did not consume rusty_tongs")
        if not after_inventory.get("well_key", False):
            errors.append("retrieve_well_key did not grant well_key")
        if tuple(audio) != ("979TONGS.WAV",):
            errors.append(
                "retrieve_well_key must emit exactly 979TONGS.WAV"
            )

    if action == "place_r8_lens" and after != before:
        if after_inventory.get("r8_lens", False):
            errors.append("place_r8_lens did not consume r8_lens")

    return errors


def build_state_fuzz_report(
    event_graph: dict[str, Any],
    trigger_ir: dict[str, Any],
    *,
    config: StateFuzzConfig | None = None,
) -> dict[str, Any]:
    input_errors = validate_inputs(event_graph, trigger_ir)
    source_checks = validate_source_contract()
    input_errors.extend(
        key for key, value in source_checks.items() if not value
    )
    if input_errors:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "FAIL",
            "errors": input_errors,
        }

    model = Model(event_graph, trigger_ir)
    (
        initial,
        states,
        _edges,
        success,
        softlocks,
        _dead,
        _attempts,
        _noops,
        _win,
        shortest_path,
        _audio,
    ) = explore(model)

    reachable_keys = {_state_key(state) for state in states}
    recoverable_keys = {
        _state_key(state) for state in states if state not in softlocks
    }

    fuzz = run_state_fuzz(
        initial_state=initial,
        actions=ACTION_NAMES,
        transition=model.attempt,
        state_key=_state_key,
        invariant_errors=_state_invariants,
        transition_errors=_transition_invariants,
        reachable_state_keys=reachable_keys,
        recoverable_state_keys=recoverable_keys,
        is_success=lambda state: state.flag("demo_complete"),
        config=config
        or StateFuzzConfig(
            seed_base=0xA2A3E1,
            seed_count=96,
            steps_per_seed=192,
            repeat_previous_probability=0.24,
            restart_probability=0.05,
        ),
    )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": fuzz["status"],
        "scope": (
            "source-safe adversarial random walks over the exhaustive KG-001 "
            "logical model; runtime PPPV remains the physical-player oracle"
        ),
        "exhaustive_reference": {
            "reachable_states": len(states),
            "recoverable_states": len(states) - len(softlocks),
            "success_states": len(success),
            "shortest_success_action_count": len(shortest_path),
            "shortest_success_path": shortest_path,
        },
        "source_contract_checks": source_checks,
        "fuzz": fuzz,
        "properties": {
            "transition_determinism": True,
            "noop_purity": True,
            "state_invariants": True,
            "transition_invariants": True,
            "reachable_graph_membership": True,
            "liveness_to_success": True,
            "success_monotonicity": True,
        },
        "forensic_boundary": {
            "does_not_replace_exhaustive_state_space": True,
            "does_not_replace_guarded_runtime_pppv": True,
            "does_not_prove_original_timing_or_motion": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic adversarial KG-001 state fuzzing."
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--seed-count", type=int, default=96)
    parser.add_argument("--steps-per-seed", type=int, default=192)
    args = parser.parse_args()

    graph_path = ROOT / "data/gameplay_event_graph_v87.json"
    trigger_path = ROOT / "data/xaf_trigger_evidence.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    triggers = json.loads(trigger_path.read_text(encoding="utf-8"))

    report = build_state_fuzz_report(
        graph,
        triggers,
        config=StateFuzzConfig(
            seed_base=0xA2A3E1,
            seed_count=args.seed_count,
            steps_per_seed=args.steps_per_seed,
            repeat_previous_probability=0.24,
            restart_probability=0.05,
        ),
    )
    report["inputs"] = {
        "gameplay_event_graph_v87_sha256": _sha256(graph_path),
        "xaf_trigger_evidence_sha256": _sha256(trigger_path),
    }

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
