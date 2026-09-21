from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .validation import ValidationScenario


SCHEMA = "remaster.playthrough_consistency"
VERSION = 1
BOOLEAN_GROUPS = {"inventory", "flags", "puzzle"}


def _scenario_map(bundle: dict[str, Any]) -> dict[str, ValidationScenario]:
    rows = bundle.get("scenarios", [])
    if not isinstance(rows, list):
        raise ValueError("scenario bundle scenarios must be a list")
    out: dict[str, ValidationScenario] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("scenario row must be an object")
        scenario = ValidationScenario.from_dict(raw)
        if scenario.scenario_id in out:
            raise ValueError(
                f"duplicate scenario_id: {scenario.scenario_id}"
            )
        out[scenario.scenario_id] = scenario
    return out


def _state_path(group: str, key: str) -> str:
    return f"{group}.{key}"


def _require_value(
    known: dict[str, Any],
    path: str,
    expected: Any,
    errors: list[str],
    context: str,
) -> None:
    if path in known:
        if known[path] != expected:
            errors.append(
                f"{context}: {path} requires {expected!r}, "
                f"known state is {known[path]!r}"
            )
        return

    group = path.split(".", 1)[0]
    if group in BOOLEAN_GROUPS and expected is False:
        known[path] = False
        return

    errors.append(
        f"{context}: precondition {path}={expected!r} is not "
        "proven by earlier chained state"
    )


def _check_setup(
    scenario: ValidationScenario,
    known: dict[str, Any],
    errors: list[str],
) -> None:
    for group in ("inventory", "flags", "puzzle", "values"):
        values = scenario.setup.get(group, {})
        if not isinstance(values, dict):
            continue
        for raw_key, expected in values.items():
            _require_value(
                known,
                _state_path(group, str(raw_key)),
                expected,
                errors,
                scenario.scenario_id,
            )


def _transition_destination(
    scenario: ValidationScenario,
) -> str | None:
    destinations = {
        str(action.parameters.get("destination_room"))
        for action in scenario.actions
        if action.kind.value == "move"
        and action.parameters.get("destination_room")
    }
    if not destinations:
        return None
    if len(destinations) != 1:
        raise ValueError(
            f"{scenario.scenario_id}: ambiguous transition destinations "
            f"{sorted(destinations)}"
        )
    return next(iter(destinations))


def audit_playthrough_consistency(
    plan: dict[str, Any],
    scenario_bundle: dict[str, Any],
) -> dict[str, Any]:
    scenarios = _scenario_map(scenario_bundle)
    errors: list[str] = []
    warnings: list[str] = []
    known: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []
    current_room: str | None = None

    if plan.get("schema") != "remaster.playthrough_plan":
        raise ValueError("unsupported playthrough plan schema")
    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("playthrough plan steps must be a list")

    if plan.get("status") != "READY":
        errors.append(
            f"playthrough plan is not authoring-ready: "
            f"{plan.get('status')!r}"
        )

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"step {index}: plan step must be an object")
            continue

        step_id = str(step.get("step_id", f"step_{index}"))
        kind = str(step.get("kind", ""))
        before_room = current_room

        if kind == "checkpoint":
            trace.append({
                "step_id": step_id,
                "kind": kind,
                "room_before": before_room,
                "room_after": current_room,
                "known_state_count": len(known),
                "status": "PRESERVES_STATE",
            })
            continue

        scenario_id = str(step.get("scenario_id", ""))
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            errors.append(
                f"{step_id}: missing scenario {scenario_id!r}"
            )
            trace.append({
                "step_id": step_id,
                "kind": kind,
                "scenario_id": scenario_id,
                "status": "MISSING_SCENARIO",
            })
            continue

        scenario_errors = scenario.validate()
        errors.extend(
            f"{step_id}: {item}" for item in scenario_errors
        )

        if current_room is None:
            current_room = scenario.room
        elif scenario.room != current_room:
            errors.append(
                f"{step_id}: scenario room {scenario.room} does not "
                f"continue from current room {current_room}"
            )

        _check_setup(scenario, known, errors)

        for expectation in scenario.state_expectations:
            _require_value(
                known,
                expectation.path,
                expectation.before,
                errors,
                scenario.scenario_id,
            )

        for expectation in scenario.state_expectations:
            known[expectation.path] = expectation.after

        destination = _transition_destination(scenario)
        if kind == "transition":
            planned_source = str(step.get("source_room", ""))
            planned_destination = str(
                step.get("destination_room", "")
            )
            if planned_source and planned_source != scenario.room:
                errors.append(
                    f"{step_id}: planned source {planned_source} does "
                    f"not match scenario room {scenario.room}"
                )
            if destination is None:
                errors.append(
                    f"{step_id}: transition scenario has no "
                    "destination_room action parameter"
                )
            else:
                if (
                    planned_destination
                    and destination != planned_destination
                ):
                    errors.append(
                        f"{step_id}: scenario destination {destination} "
                        f"does not match planned {planned_destination}"
                    )
                current_room = destination
        elif destination is not None:
            warnings.append(
                f"{step_id}: non-transition step contains destination "
                f"{destination}"
            )
            current_room = destination

        trace.append({
            "step_id": step_id,
            "kind": kind,
            "scenario_id": scenario.scenario_id,
            "room_before": before_room,
            "room_after": current_room,
            "known_state_count": len(known),
            "status": "CONSISTENT",
        })

    expected_route = plan.get("metadata", {}).get("route", [])
    if isinstance(expected_route, list) and expected_route:
        observed_rooms = []
        for row in trace:
            room_after = row.get("room_after")
            if (
                isinstance(room_after, str)
                and room_after
                and (
                    not observed_rooms
                    or observed_rooms[-1] != room_after
                )
            ):
                observed_rooms.append(room_after)
        first_room = None
        for row in trace:
            value = row.get("room_before")
            if isinstance(value, str) and value:
                first_room = value
                break
        if first_room is not None:
            observed_rooms.insert(0, first_room)
            deduped = [observed_rooms[0]]
            for room in observed_rooms[1:]:
                if room != deduped[-1]:
                    deduped.append(room)
            observed_rooms = deduped
        if observed_rooms and observed_rooms != expected_route:
            errors.append(
                f"room route mismatch: {observed_rooms!r} "
                f"!= {expected_route!r}"
            )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("plan_sha256"),
        "status": "CONSISTENT" if not errors else "INCONSISTENT",
        "errors": errors,
        "warnings": warnings,
        "step_count": len(steps),
        "known_state": dict(sorted(known.items())),
        "trace": trace,
        "boundary": (
            "Static consistency proves chained precondition/state/room "
            "compatibility only. It does not prove navigation, collision, "
            "interaction reachability, timing, audio playback or runtime PASS."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit static chained-state and room consistency."
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit_playthrough_consistency(
        _load(args.plan),
        _load(args.scenarios),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "CONSISTENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
