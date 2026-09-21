from __future__ import annotations

import unittest

from tools.remaster_framework.evaluate_playthrough import (
    evaluate_playthrough_bundle,
)


HASH = "a" * 64


def scenario_payload() -> dict:
    return {
        "schema": "remaster.validation_scenario",
        "version": 1,
        "scenario_id": "scenario",
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
    }


def runtime_step() -> dict:
    return {
        "step_id": "S01",
        "kind": "scenario",
        "schema": "remaster.runtime_validation_bundle",
        "version": 1,
        "scenario_id": "scenario",
        "status": "EXECUTION_PASS",
        "failures": [],
        "scenario": scenario_payload(),
        "evidence": {
            "schema": "remaster.runtime_evidence",
            "version": 1,
            "events": [
                {
                    "event_id": "e1",
                    "frame": 1,
                    "kind": "player_action",
                    "payload": {
                        "action_id": "forward",
                        "execution_mode": "input",
                    },
                },
                {
                    "event_id": "e2",
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
    }


def bundle() -> dict:
    return {
        "schema": "remaster.runtime_playthrough_bundle",
        "version": 1,
        "status": "EXECUTION_PASS",
        "failures": [],
        "plan": {
            "schema": "remaster.playthrough_plan",
            "version": 1,
            "plan_id": "test",
            "plan_sha256": "d" * 64,
            "success_state_sha256": HASH,
            "steps": [
                {
                    "step_id": "S01",
                    "kind": "scenario",
                    "status": "READY",
                    "scenario_id": "scenario",
                },
                {
                    "step_id": "C02",
                    "kind": "checkpoint",
                    "status": "READY",
                    "checkpoint_id": "saved",
                },
            ],
        },
        "steps": [
            runtime_step(),
            {
                "step_id": "C02",
                "kind": "checkpoint",
                "checkpoint_id": "saved",
                "status": "PASS",
                "restore_ok": True,
                "before_state_sha256": HASH,
                "after_restore_sha256": HASH,
                "expected_state_sha256": HASH,
            },
        ],
        "final_state_sha256": HASH,
        "expected_final_state_sha256": HASH,
        "runtime_guard_failures": [],
        "replay": {
            "schema": "remaster.synthetic_player_replay",
            "version": 1,
            "frame_level_avatar_trajectory": True,
            "actions": [
                {
                    "action_id": "forward",
                    "kind": "move",
                    "command": scenario_payload()["actions"][0],
                    "before": {"physics_frame": 0, "room": "R1"},
                    "trajectory": [
                        {"physics_frame": 1, "position": [0.0, 0.0, 0.0]}
                    ],
                    "after": {"physics_frame": 2, "room": "R1"},
                    "result": {"success": True, "failures": []},
                }
            ],
        },
        "runtime_boundary": {
            "single_scene_instance": True,
            "state_reset_between_scenarios": False,
            "direct_interact_calls": False,
            "gameplay_teleport_during_actions": False,
            "checkpoint_persistence": "canonical_state_roundtrip",
            "frame_level_avatar_trajectory": True,
            "world_state_snapshots": True,
            "softlock_watchdog": True,
            "transition_spawn_validation": True,
        },
    }


class PlaythroughEvaluationTests(unittest.TestCase):
    def test_complete_chained_bundle_passes(self) -> None:
        report = evaluate_playthrough_bundle(bundle())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["step_count"], 2)
        self.assertEqual(report["plan_sha256"], "d" * 64)

    def test_failed_embedded_scenario_blocks_playthrough(self) -> None:
        payload = bundle()
        payload["steps"][0]["evidence"]["events"] = []
        report = evaluate_playthrough_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("S01:" in item for item in report["errors"]))

    def test_checkpoint_hash_mismatch_blocks_playthrough(self) -> None:
        payload = bundle()
        payload["steps"][1]["after_restore_sha256"] = "b" * 64
        report = evaluate_playthrough_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("roundtrip hash mismatch" in item for item in report["errors"])
        )


    def test_runtime_guard_failure_blocks_playthrough(self) -> None:
        payload = bundle()
        payload["runtime_guard_failures"] = ["walk:unsupported_fall"]
        report = evaluate_playthrough_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("runtime guard failure" in item for item in report["errors"])
        )

    def test_missing_replay_action_blocks_playthrough(self) -> None:
        payload = bundle()
        payload["replay"]["actions"] = []
        report = evaluate_playthrough_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("replay action count mismatch" in item for item in report["errors"])
        )

    def test_runtime_boundary_shortcut_blocks_playthrough(self) -> None:
        payload = bundle()
        payload["runtime_boundary"]["gameplay_teleport_during_actions"] = True
        report = evaluate_playthrough_bundle(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any(
                "gameplay_teleport_during_actions" in item
                for item in report["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
