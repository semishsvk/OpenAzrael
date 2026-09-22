from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.kg001_state_space_v108 import DemoState, Model
from tools.openazrael_adapters.kg001_state_fuzz import (
    build_state_fuzz_report,
)
from tools.remaster_framework.state_fuzz import StateFuzzConfig


ROOT = Path(__file__).resolve().parents[3]


class OpenAzraelStateFuzzTests(unittest.TestCase):
    def _inputs(self) -> tuple[dict, dict]:
        graph = json.loads(
            (ROOT / "data/gameplay_event_graph_v87.json").read_text(
                encoding="utf-8"
            )
        )
        triggers = json.loads(
            (ROOT / "data/xaf_trigger_evidence.json").read_text(
                encoding="utf-8"
            )
        )
        return graph, triggers

    def test_well_key_model_consumes_tongs_and_emits_source_audio(self) -> None:
        graph, triggers = self._inputs()
        model = Model(graph, triggers)
        state = DemoState()

        for action in (
            "pickup_rusty_tongs",
            "open_r1_door1",
            "transition_R1_R7",
        ):
            state, _ = model.attempt(state, action)

        state, audio = model.attempt(state, "retrieve_well_key")
        self.assertFalse(state.has("rusty_tongs"))
        self.assertTrue(state.puzzle("PickupCollected:rusty_tongs"))
        self.assertTrue(state.has("well_key"))
        self.assertTrue(state.puzzle("R7KeyTake"))
        self.assertTrue(state.flag("R7key"))
        self.assertEqual(audio, ("979TONGS.WAV",))


    def test_consumed_tongs_cannot_respawn_after_return_to_r1(self) -> None:
        graph, triggers = self._inputs()
        model = Model(graph, triggers)
        state = DemoState()

        for action in (
            "pickup_rusty_tongs",
            "open_r1_door1",
            "transition_R1_R7",
            "retrieve_well_key",
            "transition_R7_R1",
        ):
            state, _ = model.attempt(state, action)

        self.assertEqual(state.room, "R1")
        self.assertFalse(state.has("rusty_tongs"))
        self.assertTrue(state.puzzle("PickupCollected:rusty_tongs"))

        before = state
        after, audio = model.attempt(state, "pickup_rusty_tongs")
        self.assertEqual(after, before)
        self.assertEqual(audio, ())

    def test_small_deterministic_fuzz_run_passes(self) -> None:
        graph, triggers = self._inputs()
        report = build_state_fuzz_report(
            graph,
            triggers,
            config=StateFuzzConfig(
                seed_base=1234,
                seed_count=8,
                steps_per_seed=64,
                repeat_previous_probability=0.25,
                restart_probability=0.05,
            ),
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["fuzz"]["failure_count"], 0)
        self.assertEqual(report["fuzz"]["attempts"], 512)
        self.assertTrue(
            report["properties"]["liveness_to_success"]
        )


if __name__ == "__main__":
    unittest.main()
