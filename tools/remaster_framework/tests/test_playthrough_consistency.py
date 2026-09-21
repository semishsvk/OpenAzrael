from __future__ import annotations

import unittest
from pathlib import Path

from tools.openazrael_adapters.demo_playthrough_plan import (
    build_openazrael_demo_playthrough_plan,
)
from tools.openazrael_adapters.kg001_candidate_framework import (
    _default_scenario_bundle,
)
from tools.remaster_framework.playthrough_consistency import (
    audit_playthrough_consistency,
)


class PlaythroughConsistencyTests(unittest.TestCase):
    def test_current_kg001_authored_chain_is_statically_consistent(self) -> None:
        root = Path(__file__).resolve().parents[3]
        scenarios = _default_scenario_bundle(root)
        plan = build_openazrael_demo_playthrough_plan(scenarios)
        report = audit_playthrough_consistency(plan, scenarios)

        self.assertEqual(report["status"], "CONSISTENT")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["step_count"], len(plan["steps"]))
        self.assertEqual(
            report["known_state"]["flags.demo_complete"],
            True,
        )
        self.assertEqual(
            report["known_state"]["inventory.shield"],
            True,
        )

    def test_unproven_true_precondition_is_rejected(self) -> None:
        scenarios = {
            "schema": "openazrael.pppv_scenario_bundle",
            "version": 1,
            "scenarios": [
                {
                    "schema": "remaster.validation_scenario",
                    "version": 1,
                    "scenario_id": "needs_key",
                    "room": "R1",
                    "setup": {
                        "inventory": {"well_key": True},
                    },
                    "actions": [
                        {
                            "action_id": "move",
                            "kind": "move",
                            "execution_mode": "input",
                            "input_action": "move_forward",
                            "frames": 1,
                        }
                    ],
                    "requirements": [],
                    "forbidden": [],
                    "sequences": [],
                    "state_expectations": [],
                    "metadata": {},
                }
            ],
        }
        plan = {
            "schema": "remaster.playthrough_plan",
            "version": 1,
            "plan_id": "bad",
            "status": "READY",
            "steps": [
                {
                    "step_id": "S1",
                    "kind": "scenario",
                    "status": "READY",
                    "scenario_id": "needs_key",
                }
            ],
            "metadata": {},
        }
        report = audit_playthrough_consistency(plan, scenarios)
        self.assertEqual(report["status"], "INCONSISTENT")
        self.assertTrue(
            any(
                "inventory.well_key=True" in item
                for item in report["errors"]
            )
        )

    def test_transition_room_mismatch_is_rejected(self) -> None:
        scenarios = {
            "schema": "openazrael.pppv_scenario_bundle",
            "version": 1,
            "scenarios": [
                {
                    "schema": "remaster.validation_scenario",
                    "version": 1,
                    "scenario_id": "transition",
                    "room": "R1",
                    "setup": {},
                    "actions": [
                        {
                            "action_id": "cross",
                            "kind": "move",
                            "execution_mode": "input",
                            "input_action": "move_forward",
                            "parameters": {
                                "destination_room": "R7",
                            },
                        }
                    ],
                    "requirements": [],
                    "forbidden": [],
                    "sequences": [],
                    "state_expectations": [],
                    "metadata": {},
                }
            ],
        }
        plan = {
            "schema": "remaster.playthrough_plan",
            "version": 1,
            "plan_id": "bad_transition",
            "status": "READY",
            "steps": [
                {
                    "step_id": "T1",
                    "kind": "transition",
                    "status": "READY",
                    "scenario_id": "transition",
                    "source_room": "R1",
                    "destination_room": "R8",
                }
            ],
            "metadata": {},
        }
        report = audit_playthrough_consistency(plan, scenarios)
        self.assertEqual(report["status"], "INCONSISTENT")
        self.assertTrue(
            any("does not match planned R8" in item for item in report["errors"])
        )


if __name__ == "__main__":
    unittest.main()
