from __future__ import annotations

import unittest
from pathlib import Path

from tools.openazrael_adapters.reference_graph import (
    build_openazrael_reference_graph,
)
from tools.remaster_framework.planning import build_validation_plan


class ValidationPlanningTests(unittest.TestCase):
    def test_plan_derives_room_state_audio_and_coverage(self) -> None:
        graph = {
            "nodes": [
                {"node_id": "room:R7", "kind": "room", "label": "R7"},
                {
                    "node_id": "gameplay:PUZZLE",
                    "kind": "gameplay_graph",
                    "label": "PUZZLE",
                },
                {"node_id": "state:flag", "kind": "state", "label": "flag"},
                {
                    "node_id": "asset:S.WAV",
                    "kind": "audio_asset",
                    "label": "S.WAV",
                },
                {
                    "node_id": "source:PUZZLES.DAT",
                    "kind": "evidence_source",
                    "label": "PUZZLES.DAT",
                },
            ],
            "edges": [
                {
                    "source": "room:R7",
                    "target": "gameplay:PUZZLE",
                    "relation": "owns_gameplay",
                },
                {
                    "source": "gameplay:PUZZLE",
                    "target": "state:flag",
                    "relation": "mutates_state",
                    "metadata": {"value": True},
                },
                {
                    "source": "gameplay:PUZZLE",
                    "target": "asset:S.WAV",
                    "relation": "plays_audio",
                    "metadata": {"semantic": "puzzle sound"},
                },
                {
                    "source": "gameplay:PUZZLE",
                    "target": "source:PUZZLES.DAT",
                    "relation": "evidence_source",
                },
            ],
        }
        scenarios = {
            "scenarios": [
                {
                    "scenario_id": "scenario",
                    "metadata": {
                        "coverage_targets": ["gameplay:PUZZLE"]
                    },
                }
            ]
        }
        plan = build_validation_plan(graph, scenarios)
        target = plan["targets"][0]
        self.assertEqual(plan["status"], "COMPLETE")
        self.assertEqual(target["rooms"], ["room:R7"])
        self.assertEqual(target["coverage_status"], "COVERED")
        self.assertEqual(
            target["expected_effects"]["audio"][0]["target"],
            "asset:S.WAV",
        )
        self.assertEqual(
            target["expected_effects"]["state"][0]["target"],
            "state:flag",
        )

    def test_current_openazrael_reference_graph_yields_all_gameplay_targets(self) -> None:
        root = Path(__file__).resolve().parents[3]
        graph = build_openazrael_reference_graph(
            root / "data" / "xaf_trigger_evidence.json",
            root / "data" / "gameplay_event_graph_v87.json",
        ).to_dict()
        plan = build_validation_plan(graph)
        target_ids = {row["target_id"] for row in plan["targets"]}

        self.assertEqual(plan["target_count"], 6)
        self.assertEqual(plan["unmapped_count"], 6)
        self.assertEqual(plan["status"], "AUTHORING_REQUIRED")
        self.assertIn("gameplay:R7_WELL_TONGS_USE", target_ids)
        self.assertIn("gameplay:R7_WATER_SWITCHBOARD_SOLVED", target_ids)
        self.assertIn("gameplay:R8_LENS_PLACE", target_ids)
        self.assertIn("gameplay:R8_OPTICAL_START", target_ids)
        self.assertIn("gameplay:R8_SECRET_DOOR_OPEN", target_ids)
        self.assertIn("gameplay:R8_TAKE_SHIELD", target_ids)


if __name__ == "__main__":
    unittest.main()
