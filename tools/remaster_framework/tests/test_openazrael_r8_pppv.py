from __future__ import annotations

import unittest

from tools.openazrael_adapters.r8_pppv import (
    build_r8_interaction_scenarios,
)
from tools.remaster_framework.validation import ExecutionMode


class OpenAzraelR8PPPVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = {
            row.scenario_id: row
            for row in build_r8_interaction_scenarios()
        }

    def test_r8_lens_place_and_shield_scenarios_exist(self) -> None:
        self.assertEqual(len(self.scenarios), 5)
        self.assertIn("openazrael.r8.take_lens", self.scenarios)
        self.assertIn(
            "openazrael.r8.take_lens.negative_water_not_drained",
            self.scenarios,
        )
        self.assertIn("openazrael.r8.place_lens", self.scenarios)
        self.assertIn("openazrael.r8.optical_sequence", self.scenarios)
        self.assertIn("openazrael.r8.take_shield", self.scenarios)

    def test_all_scenarios_validate_and_never_use_direct_gameplay_calls(self) -> None:
        for scenario in self.scenarios.values():
            self.assertEqual(scenario.validate(), [])
            self.assertTrue(
                all(
                    row.execution_mode
                    in {
                        ExecutionMode.INPUT,
                        ExecutionMode.INTERACTION_PROBE,
                        ExecutionMode.PHYSICS_WAIT,
                    }
                    for row in scenario.actions
                )
            )

    def test_optical_sequence_requires_trigger_aim_audio_and_visual_effects(self) -> None:
        scenario = self.scenarios["openazrael.r8.optical_sequence"]
        self.assertEqual(
            [row.execution_mode for row in scenario.actions],
            [
                ExecutionMode.INPUT,
                ExecutionMode.INPUT,
                ExecutionMode.INTERACTION_PROBE,
                ExecutionMode.PHYSICS_WAIT,
            ],
        )
        self.assertEqual(
            set(scenario.metadata["coverage_targets"]),
            {
                "gameplay:R8_OPTICAL_START",
                "gameplay:R8_SECRET_DOOR_OPEN",
            },
        )
        requirement_ids = {row.requirement_id for row in scenario.requirements}
        self.assertTrue(
            {
                "zxplate_enter",
                "bible_probe_from_plate",
                "optical_start_audio",
                "secret_door_audio",
                "lens_visual_moved",
                "secret_door_visual_rotated",
                "shield_became_visible",
            }
            <= requirement_ids
        )
        self.assertEqual(
            scenario.metadata["non_gating_reconstruction"]["puzzle.R8Counter"],
            "UNKNOWN opcode semantics",
        )

    def test_lens_place_requires_source_backed_audio_and_state(self) -> None:
        scenario = self.scenarios["openazrael.r8.place_lens"]
        self.assertEqual(
            scenario.metadata["coverage_targets"],
            ["gameplay:R8_LENS_PLACE"],
        )
        self.assertTrue(
            any(
                row.kind == "audio" and row.match.get("asset") == "S137.WAV"
                for row in scenario.requirements
            )
        )
        paths = {row.path for row in scenario.state_expectations}
        self.assertIn("inventory.r8_lens", paths)
        self.assertIn("puzzle.R8LensPlace", paths)

    def test_submerged_lens_negative_cannot_acquire_lens(self) -> None:
        scenario = self.scenarios[
            "openazrael.r8.take_lens.negative_water_not_drained"
        ]
        self.assertTrue(
            any(
                row.match.get("path") == "inventory.r8_lens"
                for row in scenario.forbidden
            )
        )

    def test_shield_completion_is_bound_to_gameplay_graph(self) -> None:
        scenario = self.scenarios["openazrael.r8.take_shield"]
        self.assertEqual(
            scenario.metadata["coverage_targets"],
            ["gameplay:R8_TAKE_SHIELD"],
        )
        expected = {row.path for row in scenario.state_expectations}
        self.assertTrue(
            {"inventory.shield", "puzzle.R8TakeShield", "flags.demo_complete"}
            <= expected
        )


if __name__ == "__main__":
    unittest.main()
