from __future__ import annotations

import unittest
from pathlib import Path

from tools.openazrael_adapters.demo_playthrough_plan import (
    build_openazrael_demo_playthrough_plan,
)
from tools.openazrael_adapters.kg001_candidate_framework import (
    _default_scenario_bundle,
)


class OpenAzraelDemoPlaythroughPlanTests(unittest.TestCase):
    def test_current_scenario_bundle_does_not_fake_full_demo_readiness(self) -> None:
        root = Path(__file__).resolve().parents[3]
        scenarios = _default_scenario_bundle(root)
        plan = build_openazrael_demo_playthrough_plan(scenarios)

        self.assertEqual(plan["status"], "AUTHORING_REQUIRED")
        self.assertNotIn("S01_PICKUP_TONGS", plan["blocked_steps"])
        self.assertNotIn("S02_OPEN_DOOR1", plan["blocked_steps"])
        self.assertNotIn("S08_OPEN_DOOR2", plan["blocked_steps"])
        self.assertIn("T03_R1_TO_R7", plan["blocked_steps"])
        self.assertIn("S05_SWITCHBOARD", plan["blocked_steps"])
        self.assertIn("S10_TAKE_LENS", plan["blocked_steps"])
        self.assertIn("S11_OPTICAL_SEQUENCE", plan["blocked_steps"])
        self.assertIn("S13_TAKE_SHIELD", plan["blocked_steps"])

    def test_r1_interactions_are_reused_as_ready_segments(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(rows["S01_PICKUP_TONGS"]["status"], "READY")
        self.assertEqual(rows["S02_OPEN_DOOR1"]["status"], "READY")
        self.assertEqual(rows["S08_OPEN_DOOR2"]["status"], "READY")

    def test_v118_well_positive_is_reused_as_ready_segment(self) -> None:
        root = Path(__file__).resolve().parents[3]
        scenarios = _default_scenario_bundle(root)
        plan = build_openazrael_demo_playthrough_plan(scenarios)
        rows = {row["step_id"]: row for row in plan["steps"]}

        self.assertEqual(rows["S04_WELL_TONGS"]["status"], "READY")
        self.assertEqual(
            rows["S04_WELL_TONGS"]["scenario_id"],
            "openazrael.r7.well_tongs.positive",
        )

    def test_save_load_checkpoints_preserve_v109_oracle(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertTrue(
            rows["C06_POST_R7_SAVELOAD"]["metadata"][
                "require_save_restore_hash_identity"
            ]
        )
        self.assertTrue(
            rows["C12_POST_DOOR_R8_SAVELOAD"]["metadata"][
                "require_save_restore_hash_identity"
            ]
        )
        self.assertEqual(
            rows["C14_FINAL_STATE"]["metadata"]["expected_state_sha256"],
            plan["success_state_sha256"],
        )

    def test_transition_steps_explicitly_forbid_centroid_teleport(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        transitions = [
            row for row in plan["steps"] if row["kind"] == "transition"
        ]
        self.assertTrue(transitions)
        self.assertTrue(
            all(
                row["metadata"]["forbid_trigger_centroid_teleport"]
                for row in transitions
            )
        )


if __name__ == "__main__":
    unittest.main()
