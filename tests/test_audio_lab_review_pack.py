from __future__ import annotations

import unittest

from tools.audio_lab.oa_audio_review_pack import build_review_pack

def source_asset(name: str, issues=None) -> dict:
    return {
        "path": name,
        "filename": name,
        "sha256": "a"*64,
        "detected_format": "WAVE",
        "analysis": {"channels":1,"sample_rate":22050,"sample_width_bits":8,"duration_seconds":1.0,"waveform_bins":[]},
        "issues": issues or [],
    }

def mapping(name: str, status: str, types=None) -> dict:
    return {
        "filename": name,
        "mapping_status": status,
        "mapping_types": types or [],
        "mappings": [],
        "diagnostic_references": [],
        "documentation_references": [],
        "other_references": [],
    }

class AudioLabReviewPackTests(unittest.TestCase):
    def test_priority_order_and_classes(self):
        manifest = {"assets":[
            source_asset("clean.wav"),
            source_asset("expected.wav"),
            source_asset("orphan.wav"),
            source_asset("warn.wav", [{"code":"AUD006_CLIPPING","severity":"warning","message":"x"}]),
            source_asset("error.wav", [{"code":"AUD007_FINGERPRINT_MISMATCH","severity":"error","message":"x"}]),
        ]}
        refs = {"assets":[
            mapping("clean.wav","MAPPED",["EVENT_GRAPH"]),
            mapping("expected.wav","EXPECTED_UNMAPPED"),
            mapping("orphan.wav","UNEXPECTED_ORPHAN"),
            mapping("warn.wav","MAPPED",["EVENT_GRAPH"]),
            mapping("error.wav","MAPPED",["EVENT_GRAPH"]),
        ],"broken_references":[]}
        pack = build_review_pack(manifest, refs)
        rows = {r["filename"]:r for r in pack["assets"]}
        self.assertEqual(rows["error.wav"]["priority"], "P0")
        self.assertEqual(rows["orphan.wav"]["priority"], "P1")
        self.assertEqual(rows["warn.wav"]["priority"], "P1")
        self.assertEqual(rows["expected.wav"]["priority"], "P2")
        self.assertEqual(rows["clean.wav"]["priority"], "P4")
        self.assertEqual(pack["status"], "BLOCKED")
        self.assertEqual(pack["assets"][0]["filename"], "error.wav")

    def test_broken_reference_promotes_asset_to_p0(self):
        manifest = {"assets":[source_asset("A.wav")]}
        refs = {
            "assets":[mapping("A.wav","MAPPED",["EVENT_GRAPH"])],
            "broken_references":[{"code":"AUDREF999","asset":"A.wav"}],
        }
        pack = build_review_pack(manifest, refs)
        self.assertEqual(pack["assets"][0]["priority"], "P0")
        self.assertIn("BROKEN_RUNTIME_REFERENCE", pack["assets"][0]["reasons"])

    def test_mapped_asset_suppresses_stale_no_runtime_info(self):
        manifest = {"assets":[source_asset("A.wav", [
            {"code":"AUD010_NO_RUNTIME_REFERENCE","severity":"info","message":"scanner did not recover mapping"}
        ])]}
        refs = {"assets":[mapping("A.wav","MAPPED",["EVENT_GRAPH"])],"broken_references":[]}
        pack = build_review_pack(manifest, refs)
        self.assertEqual(pack["assets"][0]["priority"], "P4")
        self.assertEqual(pack["assets"][0]["reasons"], [])

    def test_expected_unmapped_is_review_not_blocker(self):
        manifest = {"assets":[source_asset("A.wav")]}
        refs = {"assets":[mapping("A.wav","EXPECTED_UNMAPPED")],"broken_references":[]}
        pack = build_review_pack(manifest, refs)
        self.assertEqual(pack["status"], "READY_FOR_REVIEW")
        self.assertEqual(pack["summary"]["priority_counts"]["P2"], 1)

if __name__ == "__main__":
    unittest.main()
