from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.openazrael_adapters.transition_pppv import (
    build_transition_scenarios,
)
from tools.remaster_framework.validation import ExecutionMode


class OpenAzraelTransitionPPPVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = {
            row.scenario_id: row for row in build_transition_scenarios()
        }

    def test_builds_all_four_authored_demo_transitions(self) -> None:
        self.assertEqual(len(self.scenarios), 4)
        self.assertIn("openazrael.transition.r1_to_r7", self.scenarios)
        self.assertIn("openazrael.transition.r7_to_r1", self.scenarios)
        self.assertIn("openazrael.transition.r1_to_r8", self.scenarios)
        self.assertIn("openazrael.transition.r8_to_r1", self.scenarios)

    def test_transition_actions_use_input_and_trigger_goal(self) -> None:
        for scenario in self.scenarios.values():
            action = scenario.actions[0]
            self.assertEqual(action.execution_mode, ExecutionMode.INPUT)
            self.assertIn("goal_trigger", action.parameters)
            self.assertFalse(
                scenario.metadata["teleport_allowed_during_action"]
            )
            self.assertEqual(
                scenario.metadata["trigger_centroid_role"],
                "steering_target_only",
            )
            self.assertTrue(
                action.parameters["verify_destination_spawn"]
            )
            self.assertTrue(
                scenario.metadata["destination_spawn_validation_required"]
            )
            self.assertTrue(
                scenario.metadata["critical_if_transition_broken"]
            )


    def test_transition_matrix_matches_source_evidence(self) -> None:
        root = Path(__file__).resolve().parents[3]
        payload = json.loads(
            (root / "data" / "xaf_trigger_evidence.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            (
                row["source_room"],
                row["trigger"],
                row["destination_room"],
            )
            for row in payload["demo_transitions"]
        }
        actual = {
            (
                scenario.room,
                scenario.actions[0].parameters["goal_trigger"],
                scenario.actions[0].parameters["destination_room"],
            )
            for scenario in self.scenarios.values()
        }
        self.assertEqual(actual, expected)

    def test_transition_requires_enter_then_room_transition_evidence(self) -> None:
        scenario = self.scenarios["openazrael.transition.r1_to_r7"]
        self.assertEqual(scenario.requirements[0].kind, "trigger")
        self.assertEqual(scenario.requirements[1].kind, "room_transition")
        self.assertEqual(
            scenario.requirements[1].after_requirement,
            scenario.requirements[0].requirement_id,
        )

    def test_r1_gates_are_setup_preconditions_not_runtime_injection(self) -> None:
        r7 = self.scenarios["openazrael.transition.r1_to_r7"]
        r8 = self.scenarios["openazrael.transition.r1_to_r8"]
        self.assertTrue(r7.setup["flags"]["R1Door1Open"])
        self.assertTrue(r8.setup["flags"]["R1Door2Open"])
        self.assertTrue(r8.setup["flags"]["FR1DoorUnlocked"])


if __name__ == "__main__":
    unittest.main()
