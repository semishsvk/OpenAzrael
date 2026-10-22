from __future__ import annotations

import unittest
from pathlib import Path


class OpenAzraelPPPVObserverSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (
            root
            / "scripts"
            / "validation"
            / "openazrael_pppv_observer.gd"
        ).read_text(encoding="utf-8")

    def test_observer_uses_existing_runtime_signals_dynamically(self) -> None:
        self.assertIn('_connect_once(state, "inventory_changed"', self.source)
        self.assertIn('_connect_once(state, "flag_changed"', self.source)
        self.assertIn('"puzzle_node_changed"', self.source)
        self.assertIn(
            '_connect_once(\n        legacy_events,\n        "logical_audio_event"',
            self.source,
        )
        self.assertIn('"demo_action_step"', self.source)
        self.assertIn('source.has_signal(signal_name)', self.source)
        self.assertIn('source.connect(signal_name, callback)', self.source)
        self.assertIn('evidence.record("state_change"', self.source)
        self.assertIn("evidence.record_audio(filename)", self.source)
        self.assertIn("evidence.record_demo_action_step(step)", self.source)
        self.assertIn('"character_animation_request"', self.source)
        self.assertIn('"conversation_request"', self.source)

    def test_observer_reads_dynamic_state_without_mutating_it(self) -> None:
        self.assertIn('state.get(property_name)', self.source)
        self.assertIn('state.call("has", key)', self.source)
        self.assertIn('state.call("flag", key)', self.source)
        self.assertIn('state.call("puzzle_node", key)', self.source)

        self.assertNotIn("state.acquire(", self.source)
        self.assertNotIn("state.remove(", self.source)
        self.assertNotIn("state.set_flag(", self.source)
        self.assertNotIn("state.set_puzzle_node(", self.source)


if __name__ == "__main__":
    unittest.main()
