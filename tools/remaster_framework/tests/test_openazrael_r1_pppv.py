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
            self.assertEqual(
                [action.execution_mode for action in scenario.actions],
                [ExecutionMode.INPUT, ExecutionMode.INTERACTION_PROBE],
            )
            self.assertFalse(
                scenario.metadata["direct_interact_call_allowed"]
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
