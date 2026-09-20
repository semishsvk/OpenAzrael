from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from tools.audio_lab.oa_audio_repo_evidence import build_repo_evidence, build_virtual_manifest

class AudioLabRepoEvidenceTests(unittest.TestCase):
    def test_virtual_manifest_is_explicitly_byte_free(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "scripts").mkdir()
            (root / "scripts/runtime.gd").write_text('const X = "A.wav"', encoding="utf-8")
            ir = {"audio":{"sounds":[{
                "filename":"A.wav","sha256":"a"*64,"channels":1,
                "sample_rate":22050,"sample_width_bits":8,"duration_seconds":1.0
            }]}}
            manifest = build_virtual_manifest(ir, root)
            self.assertEqual(manifest["evidence_mode"], "REPOSITORY_ONLY_NO_SOURCE_BYTES")
            self.assertEqual(len(manifest["assets"]), 1)
            self.assertIn("scripts/runtime.gd", manifest["assets"][0]["references"])

    def test_repo_evidence_detects_missing_event_reference(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            ir = {"audio":{"sounds":[{
                "filename":"A.wav","sha256":"a"*64,"channels":1,
                "sample_rate":22050,"sample_width_bits":8,"duration_seconds":1.0
            }],"ambient_emitters":[]}}
            graph = {"graphs":{"G":{"actions":[{"op":"play_sound","asset":"MISSING.wav"}]}}}
            report = build_repo_evidence(root, ir, graph)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["summary"]["broken_reference_count"], 1)

    def test_current_repo_evidence_has_complete_known_corpus_and_no_orphans(self):
        root = Path(__file__).resolve().parents[1]
        ir = json.loads((root / "data/audio/legacy_world_ir.json").read_text(encoding="utf-8"))
        graph = json.loads((root / "data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
        report = build_repo_evidence(root, ir, graph)
        self.assertEqual(report["evidence_mode"], "REPOSITORY_ONLY_NO_SOURCE_BYTES")
        self.assertEqual(report["summary"]["asset_count"], 30)
        self.assertEqual(report["summary"]["unexpected_orphan_assets"], 0)
        self.assertEqual(report["summary"]["broken_reference_count"], 0)
        self.assertEqual(
            report["summary"]["mapped_assets"] + report["summary"]["expected_unmapped_assets"],
            30,
        )
        self.assertGreaterEqual(report["summary"]["mapped_assets"], 7)

if __name__ == "__main__":
    unittest.main()
