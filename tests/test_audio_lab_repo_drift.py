from __future__ import annotations

from pathlib import Path
import json
import unittest

from tools.audio_lab.oa_audio_repo_drift import compare_baseline
from tools.audio_lab.oa_audio_repo_evidence import build_repo_evidence

class AudioLabRepoDriftTests(unittest.TestCase):
    def test_compare_detects_mapping_count_drift(self):
        baseline = {
            "asset_count": 2,
            "mapped_assets": 1,
            "expected_unmapped_assets": 1,
            "unexpected_orphan_assets": 0,
            "broken_reference_count": 0,
            "mapped_asset_names": ["A.wav"],
            "mapped_asset_names_by_type": {"EVENT_GRAPH":["A.wav"]},
        }
        report = {"summary": dict(baseline)}
        self.assertEqual(compare_baseline(baseline, report), [])
        report["summary"]["mapped_assets"] = 2
        diffs = compare_baseline(baseline, report)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["field"], "mapped_assets")

    def test_committed_baseline_matches_current_repository_evidence(self):
        root = Path(__file__).resolve().parents[1]
        baseline = json.loads((root / "data/audio_lab/al_poc_01_repo_mapping_baseline.json").read_text(encoding="utf-8"))
        ir = json.loads((root / "data/audio/legacy_world_ir.json").read_text(encoding="utf-8"))
        graph = json.loads((root / "data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
        report = build_repo_evidence(root, ir, graph)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(compare_baseline(baseline, report), [])

if __name__ == "__main__":
    unittest.main()
