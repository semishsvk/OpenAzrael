from __future__ import annotations

import unittest
from pathlib import Path


class GodotPPPVTransitionNavigationSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.navigator = (
            root / "scripts" / "validation" / "pppv_navigator.gd"
        ).read_text(encoding="utf-8")
        self.executor = (
            root / "scripts" / "validation" / "pppv_action_executor.gd"
        ).read_text(encoding="utf-8")
        self.runner = (
            root / "scripts" / "validation" / "pppv_scenario_runner.gd"
        ).read_text(encoding="utf-8")
        self.manager = (root / "scripts" / "room_manager.gd").read_text(
            encoding="utf-8"
        )

    def test_world_point_navigation_uses_input_not_teleport(self) -> None:
        section = self.navigator.split("func approach_world_point", 1)[1]
        self.assertIn('Input.action_press(&"move_forward"', section)
        self.assertIn("InputEventMouseMotion.new()", self.navigator)
        self.assertNotIn("player.global_position =", section)
        self.assertNotIn("player.position =", section)
        self.assertNotIn("player.velocity =", section)
        self.assertNotIn("player.move_and_slide()", section)

    def test_shared_executor_uses_trigger_centroid_only_as_navigation_goal(self) -> None:
        execute = self.executor.split("func _execute_impl", 1)[1]
        execute = execute.split("func failure_list", 1)[0]
        self.assertIn('params.get("goal_trigger"', execute)
        self.assertIn('manager.call("_trigger_record"', self.executor)
        self.assertIn("navigator.approach_world_point", execute)
        self.assertIn('manager.set("transition_cooldown", 0.0)', execute)
        self.assertNotIn("player.global_position =", execute)
        self.assertNotIn("_spawn_at_portal", execute)

    def test_shared_executor_supports_audited_world_waypoints(self) -> None:
        execute = self.executor.split("func _execute_impl", 1)[1]
        execute = execute.split("func failure_list", 1)[0]
        self.assertIn('params.get("goal_world_point"', execute)
        self.assertIn("navigator.approach_world_point", execute)
        self.assertIn("world_point_not_reached", execute)
        self.assertNotIn("player.global_position =", execute)

    def test_transition_success_requires_room_and_spawn_validation(self) -> None:
        execute = self.executor.split("func _execute_impl", 1)[1]
        execute = execute.split("func failure_list", 1)[0]
        self.assertIn("stopped_by_condition", execute)
        self.assertIn('manager.get("current_room_id")', execute)
        self.assertIn("transition_not_observed", execute)
        self.assertIn("verify_transition_spawn", execute)
        self.assertIn("transition_spawn_validation_failed", execute)

    def test_production_transition_preserves_portal_relative_pose(self) -> None:
        process = self.manager.split("func _process", 1)[1]
        process = process.split("func _debug_jump", 1)[0]
        self.assertIn("_transition_room_through_portal(tr)", process)
        self.assertNotIn("load_room_at_portal(dest, dest_view)", process)
        self.assertIn('transition.get("source_view"', self.manager)
        self.assertIn('transition.get("destination_view"', self.manager)
        self.assertIn("source_depth", self.manager)
        self.assertIn("desired_lateral", self.manager)
        self.assertIn("-source_lateral", self.manager)
        self.assertIn('"continuity_depth_delta"', self.manager)
        self.assertIn('"continuity_lateral_delta"', self.manager)
        self.assertIn('"continuity_logical_jump"', self.manager)
        self.assertIn('"continuity_fallback"', self.manager)

    def test_scenario_runner_has_only_shared_action_executor_path(self) -> None:
        self.assertIn("ActionExecutorScript.new", self.runner)
        self.assertIn("action_executor.execute(raw_action)", self.runner)
        self.assertNotIn("func _execute_action(", self.runner)

    def test_scenario_setup_uses_one_portal_entry_helper_and_support_gate(self) -> None:
        self.assertIn('manager.has_method("load_room_at_portal")', self.runner)
        self.assertIn('manager.call("load_room_at_portal"', self.runner)
        self.assertNotIn('manager.call("_spawn_at_portal"', self.runner)
        self.assertIn("for frame in range(30)", self.runner)
        self.assertIn("portal_support_failed", self.runner)


if __name__ == "__main__":
    unittest.main()
