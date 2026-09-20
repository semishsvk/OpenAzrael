from __future__ import annotations

import unittest

from tools.openazrael_adapters.lab_compatibility import (
    audit_audio_contract,
    audit_texture_policy,
    build_compatibility_report,
)


class OpenAzraelLabCompatibilityTests(unittest.TestCase):
    def test_audio_contract_preserves_source_safe_analysis_boundary(self) -> None:
        contract = {
            "schema": "openazrael.audio_lab.al_poc_02_contract",
            "version": 3,
            "milestone": "AL-POC-02",
            "scope": {
                "source_mutation_allowed": False,
                "runtime_mutation_allowed": False,
                "output_inside_source_allowed": False,
            },
            "acceptance_gates": ["source_digest_unchanged"],
            "required_outputs": ["spectral_manifest.json"],
            "review_policy": {
                "spectral_outliers": "review-only; never fail the milestone"
            },
        }
        report = audit_audio_contract(contract)
        self.assertEqual(report["status"], "PASS")

    def test_texture_policy_requires_manual_hash_bound_approval(self) -> None:
        source_status = {
            "schema": "openazrael.texture_lab.rt_poc_01_source_status.v1",
            "branch": "texture-lab-rt-poc-01",
            "source_status": "SOURCE_SAFE_READY_FOR_LOCAL_RUNTIME",
            "review_evidence": {
                "structured_manual_review": {
                    "required_before_stage_approval": True,
                    "binds_complete_stage_evidence_sha256": True,
                    "stage_approval_requires_nonempty_note": True,
                }
            },
        }
        selection = {
            "schema": "openazrael.texture_lab.production_selection.v2",
            "automatic_selection": False,
            "profiles": {"remastered": {}},
        }
        report = audit_texture_policy(source_status, selection)
        self.assertEqual(report["status"], "PASS")

    def test_automatic_texture_selection_breaks_compatibility(self) -> None:
        source_status = {
            "schema": "openazrael.texture_lab.rt_poc_01_source_status.v1",
            "source_status": "SOURCE_SAFE_READY",
            "review_evidence": {
                "structured_manual_review": {
                    "required_before_stage_approval": True,
                    "binds_complete_stage_evidence_sha256": True,
                    "stage_approval_requires_nonempty_note": True,
                }
            },
        }
        selection = {
            "schema": "openazrael.texture_lab.production_selection.v2",
            "automatic_selection": True,
        }
        report = audit_texture_policy(source_status, selection)
        self.assertEqual(report["status"], "FAIL")

    def test_combined_report_never_outputs_quality_ranking(self) -> None:
        report = build_compatibility_report(
            audio_contracts=[
                {
                    "schema": "openazrael.audio_lab.al_poc_01_contract",
                    "milestone": "AL-POC-01",
                    "scope": {
                        "source_mutation_allowed": False,
                        "runtime_mutation_allowed": False,
                        "output_inside_source_allowed": False,
                    },
                    "acceptance_gates": ["scanner_pass"],
                    "required_outputs": ["audio_manifest.json"],
                }
            ]
        )
        self.assertEqual(report["status"], "PASS")
        self.assertNotIn("ranking", str(report).casefold())
        self.assertNotIn("winner", str(report).casefold())


if __name__ == "__main__":
    unittest.main()
