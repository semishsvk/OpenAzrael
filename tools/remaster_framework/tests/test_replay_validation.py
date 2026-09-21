from __future__ import annotations

import math
import unittest

from tools.remaster_framework.replay_validation import validate_replay


def snapshot(frame: int, room: str, *, x: float = 0.0) -> dict:
    return {
        "physics_frame": frame,
        "room": room,
        "position": [x, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "velocity": [0.0, 0.0, 0.0],
        "is_on_floor": True,
        "floor_normal": [0.0, 1.0, 0.0],
        "state_sha256": "a" * 64,
        "state_payload": [],
    }


def move_action() -> dict:
    return {
        "action_id": "walk",
        "kind": "move",
        "execution_mode": "input",
        "input_action": "move_forward",
        "frames": 2,
    }


def transition_action() -> dict:
    return {
        "action_id": "cross",
        "kind": "move",
        "execution_mode": "input",
        "parameters": {
            "goal_trigger": "door",
            "source_room": "R1",
            "destination_room": "R7",
        },
    }


def replay_for(action: dict, before_room: str, after_room: str) -> dict:
    trajectory = [
        {
            "index": 0,
            "physics_frame": 11,
            "room": before_room,
            "position": [1.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "velocity": [1.0, 0.0, 0.0],
            "is_on_floor": True,
            "room_changed": False,
            "delta_y": 0.0,
            "drop_from_action_start": 0.0,
        },
        {
            "index": 1,
            "physics_frame": 12,
            "room": after_room,
            "position": [2.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "velocity": [1.0, 0.0, 0.0],
            "is_on_floor": True,
            "room_changed": before_room != after_room,
            "delta_y": 0.0,
            "drop_from_action_start": 0.0,
        },
    ]
    return {
        "schema": "remaster.synthetic_player_replay",
        "version": 1,
        "frame_level_avatar_trajectory": True,
        "actions": [
            {
                "action_id": action["action_id"],
                "kind": action["kind"],
                "command": action,
                "before": snapshot(10, before_room),
                "trajectory": trajectory,
                "after": snapshot(13, after_room, x=2.0),
                "result": {
                    "success": True,
                    "details": {},
                    "failures": [],
                },
            }
        ],
    }


class ReplayValidationTests(unittest.TestCase):
    def test_valid_non_transition_replay_passes(self) -> None:
        action = move_action()
        self.assertEqual(
            validate_replay([action], replay_for(action, "R1", "R1")),
            [],
        )

    def test_valid_transition_replay_passes(self) -> None:
        action = transition_action()
        self.assertEqual(
            validate_replay([action], replay_for(action, "R1", "R7")),
            [],
        )

    def test_wrong_action_order_fails(self) -> None:
        first = move_action()
        second = {
            **move_action(),
            "action_id": "walk_2",
        }
        replay = replay_for(second, "R1", "R1")
        errors = validate_replay([first], replay)
        self.assertTrue(any("action_id mismatch" in item for item in errors))

    def test_unexpected_room_change_fails_non_transition(self) -> None:
        action = move_action()
        errors = validate_replay([action], replay_for(action, "R1", "R7"))
        self.assertTrue(any("unexpected room change" in item for item in errors))

    def test_wrong_transition_destination_fails(self) -> None:
        action = transition_action()
        errors = validate_replay([action], replay_for(action, "R1", "R8"))
        self.assertTrue(
            any("transition destination room mismatch" in item for item in errors)
        )

    def test_transition_return_to_source_fails(self) -> None:
        action = transition_action()
        replay = replay_for(action, "R1", "R7")
        replay["actions"][0]["trajectory"].append(
            {
                "index": 2,
                "physics_frame": 13,
                "room": "R1",
                "position": [3.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "velocity": [0.0, 0.0, 0.0],
                "is_on_floor": True,
                "room_changed": True,
                "delta_y": 0.0,
                "drop_from_action_start": 0.0,
            }
        )
        replay["actions"][0]["after"]["physics_frame"] = 14
        errors = validate_replay([action], replay)
        self.assertTrue(
            any("returned to source room" in item for item in errors)
        )

    def test_regressing_physics_frame_fails(self) -> None:
        action = move_action()
        replay = replay_for(action, "R1", "R1")
        replay["actions"][0]["trajectory"][1]["physics_frame"] = 9
        errors = validate_replay([action], replay)
        self.assertTrue(any("physics_frame regressed" in item for item in errors))

    def test_nan_avatar_coordinate_fails(self) -> None:
        action = move_action()
        replay = replay_for(action, "R1", "R1")
        replay["actions"][0]["trajectory"][0]["position"][0] = math.nan
        errors = validate_replay([action], replay)
        self.assertTrue(any("must be finite" in item for item in errors))

    def test_state_hash_is_required_on_snapshots(self) -> None:
        action = move_action()
        replay = replay_for(action, "R1", "R1")
        replay["actions"][0]["before"]["state_sha256"] = ""
        errors = validate_replay([action], replay)
        self.assertTrue(any("state_sha256" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
