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

    def test_transition_success_requires_room_and_spawn_validation(self) -> None:
        execute = self.executor.split("func _execute_impl", 1)[1]
        execute = execute.split("func failure_list", 1)[0]
        self.assertIn("stopped_by_condition", execute)
        self.assertIn('manager.get("current_room_id")', execute)
        self.assertIn("transition_not_observed", execute)
        self.assertIn("verify_transition_spawn", execute)
        self.assertIn("transition_spawn_validation_failed", execute)

    def test_scenario_runner_has_only_shared_action_executor_path(self) -> None:
        self.assertIn("ActionExecutorScript.new", self.runner)
        self.assertIn("action_executor.execute(raw_action)", self.runner)
        self.assertNotIn("func _execute_action(", self.runner)


if __name__ == "__main__":
    unittest.main()
