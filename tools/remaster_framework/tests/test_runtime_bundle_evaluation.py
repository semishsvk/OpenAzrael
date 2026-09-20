from __future__ import annotations

import unittest

from tools.remaster_framework.evaluate_validation import evaluate_runtime_bundle


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
        }

    def test_execution_pass_and_evidence_pass_yields_pass(self) -> None:
        report = evaluate_runtime_bundle(self._bundle())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["runtime_execution_status"], "EXECUTION_PASS")

    def test_execution_failure_forces_evaluation_failure(self) -> None:
        report = evaluate_runtime_bundle(self._bundle("EXECUTION_FAIL"))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("runtime execution status" in item for item in report["errors"])
        )
        self.assertIn("blocked", report["runtime_execution_failures"])


if __name__ == "__main__":
    unittest.main()
