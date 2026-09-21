from __future__ import annotations

import unittest
from pathlib import Path


class GodotPPPVPlaythroughRunnerSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (
            root / "scripts" / "validation" / "pppv_playthrough_runner.gd"
        ).read_text(encoding="utf-8")
        self.executor = (
            root / "scripts" / "validation" / "pppv_action_executor.gd"
        ).read_text(encoding="utf-8")

    def test_runner_uses_single_scene_and_shared_action_executor(self) -> None:
        self.assertEqual(self.source.count('load("res://main.tscn")'), 1)
        self.assertIn("ActionExecutorScript.new", self.source)
        self.assertIn("executor.execute(raw_action)", self.source)
        self.assertIn('"single_scene_instance": true', self.source)
        self.assertIn('"state_reset_between_scenarios": false', self.source)

    def test_scenario_setup_is_checked_not_applied_between_steps(self) -> None:
        check_section = self.source.split(
            "func _check_setup_preconditions", 1
        )[1].split("func _slice_events", 1)[0]
        self.assertNotIn('state.call("acquire"', check_section)
        self.assertNotIn('state.call("set_flag"', check_section)
        self.assertNotIn('state.call("set_puzzle_node"', check_section)
        self.assertIn("_precondition_value", check_section)

    def test_only_explicit_checkpoint_resets_state(self) -> None:
        occurrences = self.source.count('state.call("reset_all")')
        self.assertEqual(occurrences, 2)
        self.assertIn("func _run_checkpoint", self.source)
        self.assertIn("restore_canonical_state_payload", self.source)

    def test_action_executor_has_no_gameplay_teleport_or_direct_interact(self) -> None:
        self.assertNotIn("player.global_position =", self.executor)
        self.assertNotIn("player.position =", self.executor)
        self.assertNotIn("player.rotation.y =", self.executor)
        self.assertNotIn("player.velocity =", self.executor)
        self.assertNotIn("move_and_slide()", self.executor)
        self.assertNotIn(".interact()", self.executor)
        self.assertNotIn('call("interact")', self.executor)
        self.assertIn("driver.interact_via_probe", self.executor)


if __name__ == "__main__":
    unittest.main()
