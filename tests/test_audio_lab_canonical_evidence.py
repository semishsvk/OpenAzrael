from __future__ import annotations

from pathlib import Path
import json
import unittest

class CanonicalSourceEvidenceTests(unittest.TestCase):
    def test_committed_evidence_matches_current_ir_contract(self):
        root=Path(__file__).resolve().parents[1]
        evidence=json.loads((root/"data/audio_lab/al_poc_01_canonical_source_evidence.json").read_text(encoding="utf-8"))
        ir=json.loads((root/"data/audio/legacy_world_ir.json").read_text(encoding="utf-8"))
        sounds=ir.get("audio",{}).get("sounds",[])
        self.assertEqual(evidence["status"],"PASS")
        self.assertEqual(evidence["source_file_count"],len(sounds))
        self.assertEqual(evidence["expected_file_count"],30)
        self.assertEqual(evidence["errors"],0)
        self.assertEqual(evidence["missing_expected_assets"],[])
        self.assertEqual(evidence["unexpected_assets"],[])
        self.assertTrue(evidence["source_unchanged"])
        self.assertEqual(len(evidence["source_tree_sha256"]),64)
        self.assertEqual(
            {(x["filename"],x["code"]) for x in evidence["warning_assets"]},
            {
                ("981PULL.WAV","CANON_TERMINAL_PAD_MISSING"),
                ("S137.WAV","CANON_TERMINAL_PAD_MISSING"),
            },
        )
        names={s["filename"] for s in sounds}
        self.assertTrue(all(x["filename"] in names for x in evidence["warning_assets"]))
        self.assertEqual(evidence["signal_qa_observations"]["assets_over_clipping_threshold"],[])

if __name__=="__main__":
    unittest.main()
