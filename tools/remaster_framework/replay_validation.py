from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Iterable


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _action_id(action: dict[str, Any]) -> str:
    return str(action.get("action_id", ""))


def _parameters(action: dict[str, Any]) -> dict[str, Any]:
    value = action.get("parameters", {})
    return value if isinstance(value, dict) else {}


def _is_transition_action(action: dict[str, Any]) -> bool:
    params = _parameters(action)
    return bool(
        str(params.get("goal_trigger", ""))
        and str(params.get("destination_room", ""))
    )


def _finite_vector(
    value: Any,
    *,
    label: str,
    width: int = 3,
) -> list[str]:
    if not isinstance(value, list) or len(value) != width:
        return [f"{label} must be a {width}-element list"]
    errors: list[str] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            errors.append(f"{label}[{index}] must be numeric")
            continue
        if not math.isfinite(float(raw)):
            errors.append(f"{label}[{index}] must be finite")
    return errors


def _snapshot_errors(snapshot: Any, *, label: str) -> list[str]:
    if not isinstance(snapshot, dict):
        return [f"{label} snapshot must be an object"]

    errors: list[str] = []
    frame = snapshot.get("physics_frame")
    if not isinstance(frame, int) or isinstance(frame, bool) or frame < 0:
        errors.append(f"{label}.physics_frame must be a non-negative integer")

    room = snapshot.get("room")
    if not isinstance(room, str) or not room:
        errors.append(f"{label}.room must be a non-empty string")

    for field in ("position", "rotation", "velocity"):
        errors.extend(
            _finite_vector(snapshot.get(field), label=f"{label}.{field}")
        )

    state_sha = snapshot.get("state_sha256")
    if not isinstance(state_sha, str) or not _SHA256_RE.fullmatch(state_sha):
        errors.append(f"{label}.state_sha256 must be a lowercase SHA-256")

    return errors


def _trajectory_errors(
    trajectory: Any,
    *,
    action_id: str,
    before_frame: int | None,
    after_frame: int | None,
) -> list[str]:
    if not isinstance(trajectory, list):
        return [f"{action_id}: trajectory must be a list"]

    errors: list[str] = []
    previous_frame = before_frame

    for index, sample in enumerate(trajectory):
        label = f"{action_id}.trajectory[{index}]"
        if not isinstance(sample, dict):
            errors.append(f"{label} must be an object")
            continue

        frame = sample.get("physics_frame")
        if not isinstance(frame, int) or isinstance(frame, bool) or frame < 0:
            errors.append(f"{label}.physics_frame must be a non-negative integer")
        else:
            if previous_frame is not None and frame < previous_frame:
                errors.append(
                    f"{label}.physics_frame regressed: "
                    f"{frame} < {previous_frame}"
                )
            if after_frame is not None and frame > after_frame:
                errors.append(
                    f"{label}.physics_frame exceeds after snapshot: "
                    f"{frame} > {after_frame}"
                )
            previous_frame = frame

        room = sample.get("room")
        if not isinstance(room, str) or not room:
            errors.append(f"{label}.room must be a non-empty string")

        for field in ("position", "rotation", "velocity"):
            errors.extend(
                _finite_vector(sample.get(field), label=f"{label}.{field}")
            )

        for numeric in ("delta_y", "drop_from_action_start"):
            raw = sample.get(numeric)
            if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                errors.append(f"{label}.{numeric} must be numeric")
            elif not math.isfinite(float(raw)):
                errors.append(f"{label}.{numeric} must be finite")

    return errors


def validate_replay_action(
    expected_action: dict[str, Any],
    replay_action: Any,
) -> list[str]:
    expected_id = _action_id(expected_action)
    label = expected_id or "<unnamed-action>"

    if not isinstance(replay_action, dict):
        return [f"{label}: replay action must be an object"]

    errors: list[str] = []
    replay_id = str(replay_action.get("action_id", ""))
    if replay_id != expected_id:
        errors.append(
            f"{label}: replay action_id mismatch: {replay_id!r}"
        )

    replay_kind = str(replay_action.get("kind", ""))
    expected_kind = str(expected_action.get("kind", ""))
    if replay_kind != expected_kind:
        errors.append(
            f"{label}: replay kind mismatch: "
            f"{replay_kind!r} != {expected_kind!r}"
        )

    command = replay_action.get("command")
    if not isinstance(command, dict):
        errors.append(f"{label}: replay command must be an object")
    elif command != expected_action:
        errors.append(f"{label}: replay command does not match scenario action")

    before = replay_action.get("before")
    after = replay_action.get("after")
    errors.extend(_snapshot_errors(before, label=f"{label}.before"))
    errors.extend(_snapshot_errors(after, label=f"{label}.after"))

    before_frame = (
        before.get("physics_frame")
        if isinstance(before, dict)
        and isinstance(before.get("physics_frame"), int)
        else None
    )
    after_frame = (
        after.get("physics_frame")
        if isinstance(after, dict)
        and isinstance(after.get("physics_frame"), int)
        else None
    )
    if (
        before_frame is not None
        and after_frame is not None
        and after_frame < before_frame
    ):
        errors.append(
            f"{label}: after physics_frame regressed: "
            f"{after_frame} < {before_frame}"
        )

    trajectory = replay_action.get("trajectory")
    errors.extend(
        _trajectory_errors(
            trajectory,
            action_id=label,
            before_frame=before_frame,
            after_frame=after_frame,
        )
    )

    result = replay_action.get("result")
    if not isinstance(result, dict):
        errors.append(f"{label}: replay result must be an object")
    elif result.get("success") is not True:
        errors.append(f"{label}: replay result is not successful")

    if not isinstance(before, dict) or not isinstance(after, dict):
        return errors

    before_room = str(before.get("room", ""))
    after_room = str(after.get("room", ""))
    trajectory_rooms: list[str] = []
    if isinstance(trajectory, list):
        trajectory_rooms = [
            str(sample.get("room", ""))
            for sample in trajectory
            if isinstance(sample, dict) and sample.get("room")
        ]

    if _is_transition_action(expected_action):
        params = _parameters(expected_action)
        source_room = str(params.get("source_room", before_room))
        destination_room = str(params.get("destination_room", ""))

        if before_room != source_room:
            errors.append(
                f"{label}: transition source room mismatch: "
                f"{before_room!r} != {source_room!r}"
            )
        if after_room != destination_room:
            errors.append(
                f"{label}: transition destination room mismatch: "
                f"{after_room!r} != {destination_room!r}"
            )

        observed_rooms = [before_room, *trajectory_rooms, after_room]
        if source_room not in observed_rooms or destination_room not in observed_rooms:
            errors.append(
                f"{label}: replay does not observe both transition rooms"
            )
        first_destination = next(
            (
                index
                for index, room in enumerate(observed_rooms)
                if room == destination_room
            ),
            None,
        )
        if first_destination is None:
            errors.append(f"{label}: destination room never observed")
        elif any(
            room == source_room
            for room in observed_rooms[first_destination + 1 :]
        ):
            errors.append(
                f"{label}: replay returned to source room after transition"
            )
    else:
        expected_room = before_room
        if after_room != expected_room:
            errors.append(
                f"{label}: unexpected room change: "
                f"{before_room!r} -> {after_room!r}"
            )
        unexpected = sorted(
            {
                room
                for room in trajectory_rooms
                if room and room != expected_room
            }
        )
        if unexpected:
            errors.append(
                f"{label}: unexpected trajectory room(s): {unexpected!r}"
            )

    return errors



def _rounded_vector(value: Any, places: int = 3) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    result: list[float] = []
    for raw in value:
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return None
        number = float(raw)
        if not math.isfinite(number):
            return None
        rounded = round(number, places)
        result.append(0.0 if rounded == -0.0 else rounded)
    return result


def _compressed_room_sequence(
    before: Any,
    trajectory: Any,
    after: Any,
) -> list[str]:
    values: list[str] = []
    if isinstance(before, dict) and before.get("room"):
        values.append(str(before["room"]))
    if isinstance(trajectory, list):
        values.extend(
            str(sample.get("room"))
            for sample in trajectory
            if isinstance(sample, dict) and sample.get("room")
        )
    if isinstance(after, dict) and after.get("room"):
        values.append(str(after["room"]))

    compressed: list[str] = []
    for room in values:
        if not compressed or compressed[-1] != room:
            compressed.append(room)
    return compressed


def semantic_replay_payload(replay: Any) -> dict[str, Any]:
    if not isinstance(replay, dict):
        return {
            "schema": "remaster.semantic_replay",
            "version": 1,
            "actions": [],
        }

    semantic_actions: list[dict[str, Any]] = []
    actions = replay.get("actions", [])
    if not isinstance(actions, list):
        actions = []

    for row in actions:
        if not isinstance(row, dict):
            continue
        before = row.get("before", {})
        after = row.get("after", {})
        result = row.get("result", {})
        trajectory = row.get("trajectory", [])
        semantic_actions.append({
            "action_id": str(row.get("action_id", "")),
            "kind": str(row.get("kind", "")),
            "command": row.get("command", {}),
            "before": {
                "room": (
                    str(before.get("room", ""))
                    if isinstance(before, dict)
                    else ""
                ),
                "state_sha256": (
                    str(before.get("state_sha256", ""))
                    if isinstance(before, dict)
                    else ""
                ),
                "position": (
                    _rounded_vector(before.get("position"))
                    if isinstance(before, dict)
                    else None
                ),
            },
            "after": {
                "room": (
                    str(after.get("room", ""))
                    if isinstance(after, dict)
                    else ""
                ),
                "state_sha256": (
                    str(after.get("state_sha256", ""))
                    if isinstance(after, dict)
                    else ""
                ),
                "position": (
                    _rounded_vector(after.get("position"))
                    if isinstance(after, dict)
                    else None
                ),
            },
            "room_sequence": _compressed_room_sequence(
                before,
                trajectory,
                after,
            ),
            "result": {
                "success": (
                    result.get("success")
                    if isinstance(result, dict)
                    else None
                ),
                "failures": (
                    list(result.get("failures", []))
                    if isinstance(result, dict)
                    and isinstance(result.get("failures", []), list)
                    else []
                ),
            },
        })

    return {
        "schema": "remaster.semantic_replay",
        "version": 1,
        "actions": semantic_actions,
    }


def semantic_replay_sha256(replay: Any) -> str:
    payload = semantic_replay_payload(replay)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def validate_replay(
    expected_actions: Iterable[dict[str, Any]],
    replay: Any,
) -> list[str]:
    expected = list(expected_actions)
    if not isinstance(replay, dict):
        return ["replay must be an object"]

    errors: list[str] = []
    if replay.get("schema") != "remaster.synthetic_player_replay":
        errors.append("synthetic-player replay schema missing or invalid")
    if replay.get("version") != 1:
        errors.append("synthetic-player replay version must be 1")
    if replay.get("frame_level_avatar_trajectory") is not True:
        errors.append("frame-level avatar trajectory is not enabled")

    actions = replay.get("actions")
    if not isinstance(actions, list):
        errors.append("replay actions must be a list")
        return errors

    if len(actions) != len(expected):
        errors.append(
            f"replay action count mismatch: {len(actions)} != {len(expected)}"
        )

    for index, expected_action in enumerate(expected):
        if index >= len(actions):
            errors.append(
                f"{_action_id(expected_action)}: missing replay action"
            )
            continue
        errors.extend(validate_replay_action(expected_action, actions[index]))

    if len(actions) > len(expected):
        errors.append(
            f"replay contains {len(actions) - len(expected)} unexpected action(s)"
        )

    return errors
