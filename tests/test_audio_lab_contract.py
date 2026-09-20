from __future__ import annotations

from pathlib import Path
import json
import unittest

class AudioLabContractTests(unittest.TestCase):
    def test_contract_matches_recovered_demo_ir(self):
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root / "data/audio_lab/al_poc_01_contract.json").read_text(encoding="utf-8"))
        ir = json.loads((root / "data/audio/legacy_world_ir.json").read_text(encoding="utf-8"))
        sounds = ir.get("audio", {}).get("sounds", [])
        expected = contract["canonical_demo_evidence"]
        self.assertEqual(len(sounds), expected["expected_audio_assets"])
        self.assertEqual(sorted({s["channels"] for s in sounds}), expected["channels"])
        self.assertEqual(sorted({s["sample_width_bits"] for s in sounds}), expected["sample_width_bits"])
        self.assertEqual(sorted({s["sample_rate"] for s in sounds}), expected["sample_rates_hz"])

    def test_contract_keeps_mutation_and_enhancement_locked(self):
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root / "data/audio_lab/al_poc_01_contract.json").read_text(encoding="utf-8"))
        scope = contract["scope"]
        self.assertFalse(scope["source_mutation_allowed"])
        self.assertFalse(scope["runtime_mutation_allowed"])
        self.assertFalse(scope["audio_enhancement_allowed"])
        self.assertFalse(scope["ai_restoration_allowed"])
        self.assertIn("review_pack_not_blocked", contract["acceptance_gates"])

if __name__ == "__main__":
    unittest.main()
