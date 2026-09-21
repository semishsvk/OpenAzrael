from __future__ import annotations

import unittest
from pathlib import Path


class GodotPPPVHelperSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[3]
        self.bus = (
            self.root / "scripts" / "validation" / "pppv_evidence_bus.gd"
        ).read_text(encoding="utf-8")
        self.driver = (
            self.root / "scripts" / "validation" / "pppv_player_driver.gd"
        ).read_text(encoding="utf-8")

    def test_driver_uses_real_input_paths(self) -> None:
        self.assertIn("Input.action_press", self.driver)
        self.assertIn("Input.action_release", self.driver)
        self.assertIn("Input.parse_input_event", self.driver)
        self.assertIn('pressed.action = &"interact"', self.driver)
        self.assertIn('execution_mode', self.bus)

    def test_driver_never_calls_interaction_target_directly(self) -> None:
        self.assertNotIn('candidate.call("interact")', self.driver)
        self.assertNotIn("candidate.interact()", self.driver)
        self.assertNotIn("player.move_and_slide()", self.driver)

    def test_evidence_bus_has_generic_schema_and_no_timestamp(self) -> None:
        self.assertIn('const SCHEMA := "remaster.runtime_evidence"', self.bus)
        self.assertIn("Engine.get_physics_frames()", self.bus)
        self.assertNotIn("Time.get_", self.bus)
        self.assertIn('"event_id"', self.bus)
        self.assertIn('"kind"', self.bus)
        self.assertIn('"payload"', self.bus)


if __name__ == "__main__":
    unittest.main()
