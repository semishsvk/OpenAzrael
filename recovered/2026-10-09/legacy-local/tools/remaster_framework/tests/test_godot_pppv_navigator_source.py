from __future__ import annotations

import unittest
from pathlib import Path


class GodotPPPVNavigatorSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (
            root / "scripts" / "validation" / "pppv_navigator.gd"
        ).read_text(encoding="utf-8")

    def test_navigation_uses_only_gameplay_input_for_motion_and_turning(self) -> None:
        self.assertIn('Input.action_press(&"move_forward"', self.source)
        self.assertIn('Input.action_release(&"move_forward")', self.source)
        self.assertIn("InputEventMouseMotion.new()", self.source)
        self.assertIn("Input.parse_input_event(event)", self.source)
        self.assertIn("await player.get_tree().physics_frame", self.source)

    def test_navigation_does_not_teleport_or_drive_character_solver(self) -> None:
        self.assertNotIn("player.global_position =", self.source)
        self.assertNotIn("player.position =", self.source)
        self.assertNotIn("player.rotation.y =", self.source)
        self.assertNotIn("player.velocity =", self.source)
        self.assertNotIn("player.move_and_slide()", self.source)

    def test_interaction_approach_stops_before_exact_probe_aim(self) -> None:
        self.assertIn("standoff_distance := 64.0", self.source)
        self.assertIn("distance <= standoff_distance", self.source)
        self.assertIn("func aim_at_interactable", self.source)
        self.assertIn("_probe_target_name() == target_name", self.source)

    def test_navigation_emits_tongs_grade_diagnostics(self) -> None:
        for token in (
            '"player_position"',
            '"player_velocity"',
            '"heading_yaw"',
            '"pitch"',
            '"navigation_target"',
            '"distance_to_target"',
            '"interaction_probe_target"',
            '"support"',
            '"direction_corrections"',
            '"yaw_sign_flips"',
            '"watchdog_progress_metric_frames_since_progress"',
            '"last_successful_route_waypoint"',
        ):
            self.assertIn(token, self.source)

    def test_navigation_fails_when_target_missing_or_stuck(self) -> None:
        self.assertIn('"target_not_found"', self.source)
        self.assertIn('"stuck"', self.source)
        self.assertIn('"navigation_failure"', self.source)
        self.assertIn("record_interaction_probe", self.source)


if __name__ == "__main__":
    unittest.main()
