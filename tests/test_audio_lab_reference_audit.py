from __future__ import annotations

import unittest

from tools.audio_lab.oa_audio_reference_audit import build_audit

def asset(name: str, expected: bool = True, refs: list[str] | None = None) -> dict:
    return {
        "path": name,
        "filename": name,
        "sha256": "a" * 64,
        "references": refs or [],
        "expected": {"known": expected},
    }

class AudioLabReferenceAuditTests(unittest.TestCase):
    def test_classifies_ambient_event_and_expected_unmapped(self):
        manifest = {"assets": [asset("A.wav"), asset("B.wav"), asset("C.wav")]}
        ir = {
            "audio": {
                "sounds": [
                    {"filename":"A.wav"},
                    {"filename":"B.wav"},
                    {"filename":"C.wav"},
                ],
                "ambient_emitters": [
                    {"emitter_id":"OA_AMB_B","sample":"B.wav","room_id":1,"source":{"file":"AMB1.SND"}}
                ]
            }
        }
        graph = {"graphs": {"G": {"actions":[{"op":"play_sound","asset":"A.wav"}]}}}
        report = build_audit(manifest, ir, graph)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["summary"]["mapped_assets"], 2)
        self.assertEqual(report["summary"]["unmapped_assets"], 1)
        self.assertEqual(report["summary"]["expected_unmapped_assets"], 1)
        self.assertEqual(report["summary"]["unexpected_orphan_assets"], 0)
        rows = {r["filename"]:r for r in report["assets"]}
        self.assertEqual(rows["A.wav"]["mapping_types"], ["EVENT_GRAPH"])
        self.assertEqual(rows["B.wav"]["mapping_types"], ["POSITIONAL_AMBIENT"])
        self.assertEqual(rows["C.wav"]["mapping_status"], "EXPECTED_UNMAPPED")
        self.assertEqual(rows["C.wav"]["review_priority"], "REVIEW")

    def test_unexpected_unmapped_is_review_orphan_not_hard_failure(self):
        manifest = {"assets": [asset("EXTRA.wav", expected=False)]}
        ir = {"audio":{"sounds":[],"ambient_emitters":[]}}
        graph = {"graphs":{}}
        report = build_audit(manifest, ir, graph)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["summary"]["unexpected_orphan_assets"], 1)
        self.assertEqual(report["assets"][0]["mapping_status"], "UNEXPECTED_ORPHAN")
        self.assertEqual(report["assets"][0]["review_priority"], "HIGH_REVIEW")

    def test_missing_event_asset_is_hard_failure(self):
        manifest = {"assets":[asset("A.wav")]}
        ir = {"audio":{"sounds":[{"filename":"A.wav"}],"ambient_emitters":[]}}
        graph = {"graphs":{"G":{"actions":[{"op":"play_sound","asset":"MISSING.wav"}]}}}
        report = build_audit(manifest, ir, graph)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["summary"]["broken_reference_count"], 1)
        self.assertEqual(report["broken_references"][0]["code"], "AUDREF004_MISSING_EVENT_ASSET")

    def test_diagnostic_runner_literal_is_not_production_mapping(self):
        manifest = {"assets":[asset("A.wav", refs=["scripts/kg001_audio_runtime_runner_v116.gd"])]}
        ir = {"audio":{"sounds":[{"filename":"A.wav"}],"ambient_emitters":[]}}
        graph = {"graphs":{}}
        report = build_audit(manifest, ir, graph)
        self.assertEqual(report["summary"]["mapped_assets"], 0)
        self.assertEqual(
            report["assets"][0]["diagnostic_references"],
            ["scripts/kg001_audio_runtime_runner_v116.gd"],
        )

    def test_tool_reference_is_diagnostic_not_runtime(self):
        manifest = {"assets":[asset("A.wav", refs=["tools/prepare_candidate_audio.py"])]}
        ir = {"audio":{"sounds":[{"filename":"A.wav"}],"ambient_emitters":[]}}
        graph = {"graphs":{}}
        report = build_audit(manifest, ir, graph)
        self.assertEqual(report["summary"]["mapped_assets"], 0)
        self.assertEqual(report["assets"][0]["diagnostic_references"], ["tools/prepare_candidate_audio.py"])

    def test_production_script_literal_counts_as_direct_mapping(self):
        manifest = {"assets":[asset("A.wav", refs=["scripts/player.gd"])]}
        ir = {"audio":{"sounds":[{"filename":"A.wav"}],"ambient_emitters":[]}}
        graph = {"graphs":{}}
        report = build_audit(manifest, ir, graph)
        self.assertEqual(report["summary"]["mapped_assets"], 1)
        self.assertEqual(report["assets"][0]["mapping_types"], ["DIRECT_RUNTIME_LITERAL"])
        self.assertEqual(report["assets"][0]["mapping_status"], "MAPPED")

if __name__ == "__main__":
    unittest.main()
