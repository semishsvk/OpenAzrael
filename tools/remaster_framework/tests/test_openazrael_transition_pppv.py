from __future__ import annotations

import unittest

from tools.openazrael_adapters.transition_pppv import (
    build_transition_scenarios,
)
from tools.remaster_framework.validation import ExecutionMode


class OpenAzraelTransitionPPPVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = {
            row.scenario_id: row for row in build_transition_scenarios()
        }

    def test_builds_three_demo_route_transitions(self) -> None:
        self.assertEqual(len(self.scenarios), 3)
        self.assertIn("openazrael.transition.r1_to_r7", self.scenarios)
        self.assertIn("openazrael.transition.r7_to_r1", self.scenarios)
        self.assertIn("openazrael.transition.r1_to_r8", self.scenarios)

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
