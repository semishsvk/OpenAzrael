from __future__ import annotations

import unittest
from pathlib import Path

from tools.openazrael_adapters.r8_pppv import (
    R8_LENS_INGRESS_ROUTE,
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
            [row.execution_mode for row in scenario.actions[:len(R8_LENS_INGRESS_ROUTE)]],
            [ExecutionMode.INPUT] * len(R8_LENS_INGRESS_ROUTE),
        )
        self.assertEqual(
            [row.execution_mode for row in scenario.actions[-4:]],
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

    def test_lens_route_uses_source_derived_broken_mirror_ingress(self) -> None:
        self.assertEqual(len(R8_LENS_INGRESS_ROUTE), 11)
        self.assertEqual(R8_LENS_INGRESS_ROUTE[1][0], -254.067350)
        self.assertEqual(R8_LENS_INGRESS_ROUTE[4][0], -222.866992)
        self.assertEqual(R8_LENS_INGRESS_ROUTE[5][0], -208.866992)
        self.assertAlmostEqual(R8_LENS_INGRESS_ROUTE[6][0], -101.798, places=3)
        self.assertGreater(R8_LENS_INGRESS_ROUTE[6][2], 149.087)
        self.assertLess(R8_LENS_INGRESS_ROUTE[7][2], 147.440)

        for routed_scenario in self.scenarios.values():
            world_points = [
                row for row in routed_scenario.actions
                if "goal_world_point" in row.parameters
            ]
            self.assertEqual(
                len(world_points),
                len(R8_LENS_INGRESS_ROUTE),
                routed_scenario.scenario_id,
            )

        scenario = self.scenarios["openazrael.r8.take_lens"]
        self.assertEqual(
            [row.kind.value for row in scenario.actions[-3:]],
            ["move", "look", "interact"],
        )
        self.assertEqual(
            scenario.actions[-2].parameters["goal_target"],
            "Interact_R8Lens",
        )

    def test_broken_right_mirror_is_not_world_collision(self) -> None:
        source = Path("scripts/room_manager.gd").read_text(encoding="utf-8")
        self.assertIn(
            'room_id == "R8" and obj_name in ["mirror01", "broken3"]',
            source,
        )
        self.assertIn("_r8_broken_mirror_wall_collision", source)
        self.assertIn('obj_name in ["mirrors", "mirrors01"]', source)
        self.assertIn("_clip_world_polygon_x", source)
        self.assertIn("source mirror aperture", source)

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
