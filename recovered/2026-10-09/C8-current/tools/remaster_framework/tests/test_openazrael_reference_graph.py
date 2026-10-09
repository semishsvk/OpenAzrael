from __future__ import annotations

import unittest
from pathlib import Path

from tools.openazrael_adapters.reference_graph import (
    build_openazrael_reference_graph,
)


class OpenAzraelReferenceGraphTests(unittest.TestCase):
    def test_current_demo_ir_builds_valid_reference_graph(self) -> None:
        root = Path(__file__).resolve().parents[3]
        graph = build_openazrael_reference_graph(
            root / "data" / "xaf_trigger_evidence.json",
            root / "data" / "gameplay_event_graph_v87.json",
        )
        payload = graph.to_dict()
        node_ids = {item["node_id"] for item in payload["nodes"]}

        self.assertIn("room:R7", node_ids)
        self.assertIn("trigger:R1:zxcoriR2", node_ids)
        self.assertIn("gameplay:R8_LENS_PLACE", node_ids)
        self.assertIn("asset:S137.WAV", node_ids)
        self.assertEqual(graph.validate(), [])

        self.assertTrue(
            any(
                edge["source"] == "gameplay:R8_LENS_PLACE"
                and edge["relation"] == "plays_audio"
                and edge["target"] == "asset:S137.WAV"
                for edge in payload["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["source"] == "room:R1"
                and edge["relation"] == "room_transition"
                and edge["target"] == "room:R8"
                and edge["metadata"].get("trigger") == "zxcoriR2"
                for edge in payload["edges"]
            )
        )

    def test_build_is_deterministic(self) -> None:
        root = Path(__file__).resolve().parents[3]
        args = (
            root / "data" / "xaf_trigger_evidence.json",
            root / "data" / "gameplay_event_graph_v87.json",
        )
        first = build_openazrael_reference_graph(*args).to_dict()
        second = build_openazrael_reference_graph(*args).to_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
