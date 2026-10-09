from __future__ import annotations

import unittest

from tools.remaster_framework.evaluate_validation import evaluate_runtime_bundle


def replay_snapshot(frame: int, room: str) -> dict:
    return {
        "physics_frame": frame,
        "room": room,
        "position": [0.0, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "velocity": [0.0, 0.0, 0.0],
        "is_on_floor": True,
        "floor_normal": [0.0, 1.0, 0.0],
        "state_sha256": "a" * 64,
        "state_payload": [],
    }


class RuntimeBundleEvaluationTests(unittest.TestCase):
    def _bundle(self, execution_status: str = "EXECUTION_PASS") -> dict:
        return {
            "schema": "remaster.runtime_validation_bundle",
            "version": 1,
            "status": execution_status,
            "failures": [] if execution_status == "EXECUTION_PASS" else ["blocked"],
            "scenario": {
                "schema": "remaster.validation_scenario",
                "version": 1,
                "scenario_id": "simple",
                "room": "R1",
                "setup": {},
                "actions": [
                    {
                        "action_id": "forward",
                        "kind": "move",
                        "execution_mode": "input",
                        "input_action": "move_forward",
                        "frames": 1,
                    }
                ],
                "requirements": [
                    {
                        "requirement_id": "progress",
                        "kind": "movement",
                        "match": {
                            "action_id": "forward",
                            "progress_ok": True,
                        },
                    }
                ],
                "forbidden": [],
                "sequences": [],
                "state_expectations": [],
                "metadata": {},
            },
            "evidence": {
                "schema": "remaster.runtime_evidence",
                "version": 1,
                "events": [
                    {
                        "event_id": "ev_000001",
                        "frame": 1,
                        "kind": "player_action",
                        "payload": {
                            "action_id": "forward",
                            "execution_mode": "input",
                        },
                    },
                    {
                        "event_id": "ev_000002",
                        "frame": 2,
                        "kind": "movement",
                        "payload": {
                            "action_id": "forward",
                            "progress_ok": True,
                        },
                    },
                ],
            },
            "before_state": {},
            "after_state": {},
            "runtime_guard_failures": [],
            "replay": {
                "schema": "remaster.synthetic_player_replay",
                "version": 1,
                "frame_level_avatar_trajectory": True,
                "actions": [
                    {
                        "action_id": "forward",
                        "kind": "move",
                        "command": {
                            "action_id": "forward",
                            "kind": "move",
                            "execution_mode": "input",
                            "input_action": "move_forward",
                            "frames": 1,
                        },
                        "before": replay_snapshot(0, "R1"),
                        "trajectory": [
                            {
                                "physics_frame": 1,
                                "room": "R1",
                                "position": [0.0, 0.0, 0.0],
                                "rotation": [0.0, 0.0, 0.0],
                                "velocity": [0.0, 0.0, 0.0],
                                "is_on_floor": True,
                                "room_changed": False,
                                "delta_y": 0.0,
                                "drop_from_action_start": 0.0,
                            }
                        ],
                        "after": replay_snapshot(2, "R1"),
                        "result": {"success": True, "failures": []},
                    }
                ],
            },
            "runtime_boundary": {
                "direct_interact_calls": False,
                "gameplay_teleport_during_actions": False,
                "frame_level_avatar_trajectory": True,
                "world_state_snapshots": True,
                "softlock_watchdog": True,
                "transition_spawn_validation": True,
            },
        }

    def test_execution_pass_and_evidence_pass_yields_pass(self) -> None:
        report = evaluate_runtime_bundle(self._bundle())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["runtime_execution_status"], "EXECUTION_PASS")


    def test_runtime_guard_failure_forces_evaluation_failure(self) -> None:
        payload = self._bundle()
        payload["runtime_guard_failures"] = ["forward:unsupported_fall"]
        report = evaluate_runtime_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("runtime guard failure" in item for item in report["errors"])
        )

    def test_replay_action_count_mismatch_forces_failure(self) -> None:
        payload = self._bundle()
        payload["replay"]["actions"] = []
        report = evaluate_runtime_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("replay action count mismatch" in item for item in report["errors"])
        )

    def test_execution_failure_forces_evaluation_failure(self) -> None:
        report = evaluate_runtime_bundle(self._bundle("EXECUTION_FAIL"))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("runtime execution status" in item for item in report["errors"])
        )
        self.assertIn("blocked", report["runtime_execution_failures"])


if __name__ == "__main__":
    unittest.main()
