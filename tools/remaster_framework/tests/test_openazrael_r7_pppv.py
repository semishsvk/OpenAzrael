from __future__ import annotations

import unittest

from tools.openazrael_adapters.r7_pppv import (
    build_r7_switchboard_scenarios,
)
from tools.remaster_framework.validation import ExecutionMode


class OpenAzraelR7PPPVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = {
            row.scenario_id: row
            for row in build_r7_switchboard_scenarios()
        }

    def test_positive_and_wrong_sequence_negative_exist(self) -> None:
        self.assertEqual(len(self.scenarios), 2)
        self.assertIn("openazrael.r7.water_switchboard", self.scenarios)
        self.assertIn(
            "openazrael.r7.water_switchboard.negative_wrong_sequence",
            self.scenarios,
        )

    def test_positive_uses_real_player_actions_in_exact_authored_order(self) -> None:
        scenario = self.scenarios["openazrael.r7.water_switchboard"]
        self.assertEqual(scenario.validate(), [])
        self.assertEqual(
            [row.execution_mode for row in scenario.actions],
            [
                ExecutionMode.INPUT,
                ExecutionMode.INPUT,
                ExecutionMode.INTERACTION_PROBE,
                ExecutionMode.INPUT,
                ExecutionMode.INPUT,
                ExecutionMode.INTERACTION_PROBE,
                ExecutionMode.INPUT,
                ExecutionMode.INPUT,
                ExecutionMode.INPUT,
                ExecutionMode.INTERACTION_PROBE,
            ],
        )
        self.assertEqual(
            list(scenario.sequences[0].expected),
            [
                "Interact_well_lev02",
                "Interact_well_weel3",
                "Interact_well_lev02",
            ],
        )

    def test_positive_explicitly_aims_and_physically_disambiguates_final_lever(self) -> None:
        scenario = self.scenarios["openazrael.r7.water_switchboard"]
        ids = [row.action_id for row in scenario.actions]
        self.assertEqual(
            [row for row in ids if row.startswith("aim_switch_")],
            ["aim_switch_1", "aim_switch_2", "aim_switch_3"],
        )
        side_step = next(
            row for row in scenario.actions
            if row.action_id == "separate_switch_targets"
        )
        self.assertEqual(side_step.execution_mode, ExecutionMode.INPUT)
        self.assertEqual(side_step.parameters["goal_world_point"], [65.0, -41.45, 85.0])

    def test_positive_requires_source_backed_flags_audio_and_water_state(self) -> None:
        scenario = self.scenarios["openazrael.r7.water_switchboard"]
        paths = {row.path for row in scenario.state_expectations}
        self.assertEqual(
            paths,
            {
                "flags.R7waterswitchboard",
                "flags.R8BathDrain",
                "puzzle.R8Water",
            },
        )
        self.assertTrue(
            any(
                row.kind == "audio"
                and row.match.get("asset") == "S152V2.WAV"
                for row in scenario.requirements
            )
        )
        self.assertEqual(
            scenario.metadata["coverage_targets"],
            ["gameplay:R7_WATER_SWITCHBOARD_SOLVED"],
        )

    def test_wrong_sequence_cannot_solve_or_emit_drain_audio(self) -> None:
        scenario = self.scenarios[
            "openazrael.r7.water_switchboard.negative_wrong_sequence"
        ]
        forbidden = {
            (row.kind, row.match.get("path"), row.match.get("asset"))
            for row in scenario.forbidden
        }
        self.assertIn(
            ("state_change", "flags.R8BathDrain", None),
            forbidden,
        )
        self.assertIn(("audio", None, "S152V2.WAV"), forbidden)


if __name__ == "__main__":
    unittest.main()
