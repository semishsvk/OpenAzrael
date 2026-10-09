from __future__ import annotations

import unittest

from tools.remaster_framework.asset_lab import (
    EvidenceBinding,
    LabDescriptor,
    LabDomain,
    ProductionSelection,
    ReviewDecision,
    SourceSafetyPolicy,
    sha256_json,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class AssetLabContractTests(unittest.TestCase):
    def test_source_safe_descriptor_accepts_measurement_only_lab(self) -> None:
        descriptor = LabDescriptor(
            lab_id="audio_lab",
            domain=LabDomain.AUDIO,
            milestone="AL-POC-02",
            title="Spectrogram and Perceptual QA",
            source_safety=SourceSafetyPolicy(),
            acceptance_gates=("source_digest_unchanged",),
            automatic_quality_verdict=False,
            automatic_production_selection=False,
        )
        self.assertEqual(descriptor.validate(), [])

    def test_automatic_subjective_verdict_or_selection_is_rejected(self) -> None:
        verdict = LabDescriptor(
            lab_id="texture",
            domain=LabDomain.TEXTURE,
            milestone="RT",
            title="Texture Lab",
            source_safety=SourceSafetyPolicy(),
            automatic_quality_verdict=True,
        )
        selection = LabDescriptor(
            lab_id="texture",
            domain=LabDomain.TEXTURE,
            milestone="RT",
            title="Texture Lab",
            source_safety=SourceSafetyPolicy(),
            automatic_production_selection=True,
        )
        self.assertTrue(verdict.validate())
        self.assertTrue(selection.validate())

    def test_accepted_production_selection_is_manual_and_evidence_bound(self) -> None:
        selected = ProductionSelection(
            selection_id="texture:CORIROCK:remastered",
            asset_id="CORIROCK",
            domain=LabDomain.TEXTURE,
            selected_variant="ai_restored",
            decision=ReviewDecision.ACCEPTED_FOR_STAGE,
            reviewer_note="Reviewed full image, details, alpha and tiling.",
            evidence=(
                EvidenceBinding(
                    evidence_id="review",
                    evidence_sha256=HASH_A,
                    source_sha256=HASH_B,
                    candidate_sha256=HASH_C,
                ),
            ),
            automatic=False,
        )
        self.assertEqual(selected.validate(), [])

    def test_accepted_selection_without_note_or_evidence_fails(self) -> None:
        selected = ProductionSelection(
            selection_id="bad",
            asset_id="asset",
            domain=LabDomain.TEXTURE,
            selected_variant="candidate",
            decision=ReviewDecision.ACCEPTED_FOR_STAGE,
            reviewer_note="",
            evidence=(),
        )
        errors = selected.validate()
        self.assertTrue(any("reviewer_note" in error for error in errors))
        self.assertTrue(any("requires evidence" in error for error in errors))

    def test_canonical_json_hash_is_order_independent(self) -> None:
        self.assertEqual(
            sha256_json({"b": 2, "a": 1}),
            sha256_json({"a": 1, "b": 2}),
        )


if __name__ == "__main__":
    unittest.main()
