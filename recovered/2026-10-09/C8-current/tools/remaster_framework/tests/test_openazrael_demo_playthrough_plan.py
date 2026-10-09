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
    def test_current_scenario_bundle_is_authoring_complete_not_runtime_validated(self) -> None:
        root = Path(__file__).resolve().parents[3]
        scenarios = _default_scenario_bundle(root)
        plan = build_openazrael_demo_playthrough_plan(scenarios)

        self.assertEqual(plan["status"], "READY")
        self.assertEqual(plan["blocked_steps"], [])
        self.assertEqual(
            plan["metadata"]["runtime_validation_status"],
            "NOT_EXECUTED",
        )
        self.assertTrue(
            plan["metadata"]["chained_execution_implemented"]
        )
        self.assertNotIn("S02_PICKUP_TONGS", plan["blocked_steps"])
        self.assertNotIn("S01_OPEN_DOOR1", plan["blocked_steps"])
        self.assertNotIn("S08_OPEN_DOOR2", plan["blocked_steps"])
        self.assertNotIn("T03_R1_TO_R7", plan["blocked_steps"])
        self.assertNotIn("T07_R7_TO_R1", plan["blocked_steps"])
        self.assertNotIn("T09_R1_TO_R8", plan["blocked_steps"])
        self.assertNotIn("S05_SWITCHBOARD", plan["blocked_steps"])
        self.assertNotIn("S10_TAKE_LENS", plan["blocked_steps"])
        self.assertNotIn("S11_PLACE_LENS", plan["blocked_steps"])
        self.assertNotIn("S11_OPTICAL_SEQUENCE", plan["blocked_steps"])
        self.assertNotIn("S13_TAKE_SHIELD", plan["blocked_steps"])

    def test_r1_interactions_are_reused_as_ready_segments(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(rows["S02_PICKUP_TONGS"]["status"], "READY")
        self.assertEqual(rows["S01_OPEN_DOOR1"]["status"], "READY")
        self.assertEqual(rows["S08_OPEN_DOOR2"]["status"], "READY")

    def test_r1_order_matches_physical_corridor_dependency(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        step_ids = [row["step_id"] for row in plan["steps"]]
        self.assertLess(
            step_ids.index("S01_OPEN_DOOR1"),
            step_ids.index("S02_PICKUP_TONGS"),
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(
            rows["S01_OPEN_DOOR1"]["scenario_id"],
            "openazrael.r1.open_door1",
        )
        self.assertEqual(
            rows["S02_PICKUP_TONGS"]["scenario_id"],
            "openazrael.r1.pickup_tongs",
        )
        self.assertIn(
            "flags.R1Door1Open",
            rows["S02_PICKUP_TONGS"]["required_state_paths"],
        )

    def test_transition_scenarios_are_reused_as_ready_segments(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(rows["T03_R1_TO_R7"]["status"], "READY")
        self.assertEqual(rows["T07_R7_TO_R1"]["status"], "READY")
        self.assertEqual(rows["T09_R1_TO_R8"]["status"], "READY")
        self.assertEqual(
            rows["T03_R1_TO_R7"]["scenario_id"],
            "openazrael.transition.r1_to_r7",
        )

    def test_r7_switchboard_is_reused_as_ready_segment(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(rows["S05_SWITCHBOARD"]["status"], "READY")
        self.assertEqual(
            rows["S05_SWITCHBOARD"]["scenario_id"],
            "openazrael.r7.water_switchboard",
        )

    def test_chained_r7_steps_carry_physical_context_routes(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(
            len(rows["S05_SWITCHBOARD"]["metadata"]["playthrough_entry_actions"]),
            5,
        )
        self.assertEqual(
            len(rows["T07_R7_TO_R1"]["metadata"]["playthrough_entry_actions"]),
            6,
        )
        self.assertEqual(
            rows["S13_TAKE_SHIELD"]["metadata"]["skip_action_prefixes"],
            ["route_to_shield_"],
        )

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

    def test_all_r8_segments_are_authored_ready(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plan = build_openazrael_demo_playthrough_plan(
            _default_scenario_bundle(root)
        )
        rows = {row["step_id"]: row for row in plan["steps"]}
        self.assertEqual(rows["S10_TAKE_LENS"]["status"], "READY")
        self.assertEqual(rows["S11_PLACE_LENS"]["status"], "READY")
        self.assertEqual(rows["S13_TAKE_SHIELD"]["status"], "READY")
        self.assertEqual(rows["S11_OPTICAL_SEQUENCE"]["status"], "READY")
        self.assertEqual(
            rows["S11_OPTICAL_SEQUENCE"]["scenario_id"],
            "openazrael.r8.optical_sequence",
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
