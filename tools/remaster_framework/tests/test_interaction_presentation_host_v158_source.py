from __future__ import annotations
import unittest
from pathlib import Path

class InteractionPresentationHostV158SourceTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[3]
        self.src=(root/"scripts"/"interaction_presentation_host_v158.gd").read_text(encoding="utf-8")

    def test_host_is_source_gated(self):
        self.assertIn("texture == null", self.src)
        self.assertNotIn("Label.new()", self.src)
        self.assertNotIn("RichTextLabel", self.src)

    def test_host_exposes_observable_open_close_state(self):
        self.assertIn("signal presentation_opened", self.src)
        self.assertIn("signal presentation_closed", self.src)
        self.assertIn("func active_id()", self.src)
        self.assertIn("func close()", self.src)

    def test_candidate_contract_forbids_state_only_parchment_pass(self):
        import json
        root=Path(__file__).resolve().parents[3]
        contract=json.loads((root/"data/tests/kg001_candidate3_pppv_integration_contract.json").read_text(encoding="utf-8"))
        gate=contract["interaction_presentation_gate"]
        self.assertTrue(gate["state_only_pass_forbidden"])
        self.assertEqual(gate["status"], "BLOCKED_SOURCE_PAYLOAD")

    def test_readable_binding_requires_two_independent_links(self):
        import json
        root=Path(__file__).resolve().parents[3]
        policy=json.loads((root/"data/tests/kg001_readable_evidence_policy_v159.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(policy["binding_threshold"]["minimum_independent_links"], 2)
        self.assertEqual(policy["current_r1p1"]["payload_identity"], "HOLD")

    def test_source_texture_uses_nearest_filtering(self):
        self.assertIn("TEXTURE_FILTER_NEAREST", self.src)

if __name__=="__main__":
    unittest.main()
