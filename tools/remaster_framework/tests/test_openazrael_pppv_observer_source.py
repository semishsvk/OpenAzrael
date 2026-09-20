from __future__ import annotations

import unittest
from pathlib import Path


class OpenAzraelPPPVObserverSourceTests(unittest.TestCase):
    def test_observer_uses_existing_runtime_signals(self) -> None:
        root = Path(__file__).resolve().parents[3]
        source = (
            root
            / "scripts"
            / "validation"
            / "openazrael_pppv_observer.gd"
        ).read_text(encoding="utf-8")

        self.assertIn("state.inventory_changed.connect", source)
        self.assertIn("state.flag_changed.connect", source)
        self.assertIn("state.puzzle_node_changed.connect", source)
        self.assertIn("legacy_events.logical_audio_event.connect", source)
        self.assertIn('interaction.has_signal("demo_action_step")', source)
        self.assertIn('evidence.record("state_change"', source)
        self.assertIn("evidence.record_audio(filename)", source)
        self.assertIn("evidence.record_demo_action_step(step)", source)

    def test_observer_does_not_mutate_game_state(self) -> None:
        root = Path(__file__).resolve().parents[3]
        source = (
            root
            / "scripts"
            / "validation"
            / "openazrael_pppv_observer.gd"
        ).read_text(encoding="utf-8")

        self.assertNotIn("state.acquire(", source)
        self.assertNotIn("state.remove(", source)
        self.assertNotIn("state.set_flag(", source)
        self.assertNotIn("state.set_puzzle_node(", source)


if __name__ == "__main__":
    unittest.main()
