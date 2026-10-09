import unittest
from tools.validate_r7_multistate_evidence_v305 import audit,NAMES,STAGES
class EvidenceTests(unittest.TestCase):
    def test_counts_grounded(self):
        r=audit(); self.assertEqual(r["observed_occurrences"],NAMES)
    def test_no_fidelity_promotion(self):
        r=audit(); self.assertFalse(r["promotion_allowed"]); self.assertEqual(r["fidelity_status"],"HOLD")
    def test_all_stages_explicit(self):
        r=audit(); self.assertEqual(set(r["stages"]),set(STAGES))
    def test_unproven_semantics_held(self):
        r=audit(); self.assertEqual(r["stages"]["animation_transform"]["state"],"HOLD")
