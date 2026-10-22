from __future__ import annotations

import unittest

from tools.openazrael_adapters.r1_pppv import (
    build_r1_interaction_scenarios,
)
from tools.remaster_framework.validation import ExecutionMode


class OpenAzraelR1PPPVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = {
            row.scenario_id: row
            for row in build_r1_interaction_scenarios()
        }

    def test_builds_pickup_and_door_positive_negative_scenarios(self) -> None:
        self.assertEqual(len(self.scenarios), 4)
        self.assertIn("openazrael.r1.pickup_tongs", self.scenarios)
        self.assertIn("openazrael.r1.open_door1", self.scenarios)
        self.assertIn("openazrael.r1.open_door2", self.scenarios)
        self.assertIn(
            "openazrael.r1.open_door2.negative_without_key",
            self.scenarios,
        )

    def test_every_r1_scenario_uses_real_approach_and_probe(self) -> None:
        for scenario in self.scenarios.values():
            self.assertEqual(scenario.validate(), [])
            modes = [action.execution_mode for action in scenario.actions]
            self.assertEqual(
                modes.count(ExecutionMode.INTERACTION_PROBE),
                1,
            )
            self.assertTrue(
                all(
                    mode in (
                        ExecutionMode.INPUT,
                        ExecutionMode.INTERACTION_PROBE,
                    )
                    for mode in modes
                )
            )
            self.assertFalse(
                scenario.metadata["direct_interact_call_allowed"]
            )

    def test_tongs_uses_audited_physical_corridor_route(self) -> None:
        scenario = self.scenarios["openazrael.r1.pickup_tongs"]
        self.assertTrue(scenario.setup["flags"]["R1Door1Open"])
        waypoint_actions = [
            action
            for action in scenario.actions
            if "goal_world_point" in action.parameters
        ]
        self.assertGreaterEqual(len(waypoint_actions), 40)
        self.assertTrue(
            all(
                action.execution_mode == ExecutionMode.INPUT
                for action in waypoint_actions
            )
        )
        self.assertEqual(
            scenario.metadata["route_policy"],
            "production input only; no teleport",
        )

    def test_door2_uses_same_audited_route_before_real_interaction(self) -> None:
        scenario = self.scenarios["openazrael.r1.open_door2"]
        self.assertTrue(scenario.setup["flags"]["R1Door1Open"])
        self.assertTrue(scenario.setup["inventory"]["well_key"])
        self.assertTrue(
            any("goal_world_point" in action.parameters for action in scenario.actions)
        )
        self.assertEqual(
            scenario.actions[-1].parameters["goal_world_point"],
            [529.295811, -84.2055, -513.041569],
        )

    def test_tongs_pickup_requires_inventory_state_change(self) -> None:
        scenario = self.scenarios["openazrael.r1.pickup_tongs"]
        self.assertEqual(
            scenario.state_expectations[0].path,
            "inventory.rusty_tongs",
        )
        self.assertFalse(scenario.state_expectations[0].before)
        self.assertTrue(scenario.state_expectations[0].after)

    def test_door2_negative_forbids_unlock_and_open_flags(self) -> None:
        scenario = self.scenarios[
            "openazrael.r1.open_door2.negative_without_key"
        ]
        forbidden_paths = {
            row.match.get("path") for row in scenario.forbidden
        }
        self.assertEqual(
            forbidden_paths,
            {"flags.FR1DoorUnlocked", "flags.R1Door2Open"},
        )


if __name__ == "__main__":
    unittest.main()
