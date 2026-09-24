from __future__ import annotations

import unittest
from pathlib import Path


class GodotPPPVScenarioRunnerSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (
            root / "scripts" / "validation" / "pppv_scenario_runner.gd"
        ).read_text(encoding="utf-8")
        self.executor = (
            root / "scripts" / "validation" / "pppv_action_executor.gd"
        ).read_text(encoding="utf-8")

    def test_runner_composes_reusable_validation_helpers(self) -> None:
        self.assertIn("PPPV", self.source)
        self.assertIn("pppv_evidence_bus.gd", self.source)
        self.assertIn("pppv_player_driver.gd", self.source)
        self.assertIn("pppv_navigator.gd", self.source)
        self.assertIn("openazrael_pppv_observer.gd", self.source)
        self.assertIn("observer.snapshot_state", self.source)
        self.assertIn("evidence.bundle()", self.source)

    def test_gameplay_actions_do_not_teleport_or_call_interact_directly(self) -> None:
        execute_section = self.executor.split("func _execute_impl", 1)[1]
        execute_section = execute_section.split("func failure_list", 1)[0]
        self.assertNotIn("global_position =", execute_section)
        self.assertNotIn("player.position =", execute_section)
        self.assertNotIn(".interact()", execute_section)
        self.assertNotIn('call("interact")', execute_section)
        self.assertNotIn("move_and_slide()", execute_section)
        self.assertNotIn("_spawn_at_portal", execute_section)
        self.assertIn("navigator.approach_interactable", execute_section)
        self.assertIn("driver.interact_via_probe", execute_section)

    def test_portal_setup_uses_production_faithful_room_entry(self) -> None:
        setup_section = self.source.split("func _apply_setup", 1)[1]
        setup_section = setup_section.split("func _write_bundle", 1)[0]
        self.assertIn('manager.has_method("load_room_at_portal")', setup_section)
        self.assertIn('manager.call("load_room_at_portal", room, spawn_view, false)', setup_section)
        self.assertIn("await _verify_setup_support(manager, room, spawn_view)", setup_section)
        self.assertNotIn("_spawn_at_portal", setup_section)
        execute_section = self.executor.split("func _execute_impl", 1)[1]
        execute_section = execute_section.split("func failure_list", 1)[0]
        self.assertNotIn("_spawn_at_portal", execute_section)
        self.assertNotIn("load_room_at_portal", execute_section)

    def test_runtime_bundle_contains_evidence_and_before_after_state(self) -> None:
        self.assertIn('"remaster.runtime_validation_bundle"', self.source)
        self.assertIn('"before_state"', self.source)
        self.assertIn('"after_state"', self.source)
        self.assertIn('"evidence"', self.source)
        self.assertIn('"scenario"', self.source)


if __name__ == "__main__":
    unittest.main()
