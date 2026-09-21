from __future__ import annotations

import unittest
from pathlib import Path


class BugReportFrameworkContextSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.helper = (
            root
            / "scripts"
            / "validation"
            / "bug_report_framework_context.gd"
        ).read_text(encoding="utf-8")
        self.diagnostics = (
            root / "scripts" / "candidate_diagnostics_v116.gd"
        ).read_text(encoding="utf-8")

    def test_helper_reads_only_framework_metadata(self) -> None:
        self.assertIn(
            "res://data/runtime/build_provenance.json",
            self.helper,
        )
        self.assertIn(
            "res://data/runtime/release_gate_summary.json",
            self.helper,
        )
        self.assertIn(
            "res://data/runtime/pppv_coverage.json",
            self.helper,
        )
        self.assertIn(
            "res://data/runtime/pppv_playthrough_evaluation.json",
            self.helper,
        )
        for forbidden in (
            "res://assets/rooms/",
            "res://assets/audio/",
            "res://assets/textures/classic/",
        ):
            self.assertNotIn(forbidden, self.helper)

    def test_helper_enforces_schema_and_size_limit(self) -> None:
        self.assertIn("MAX_CONTEXT_BYTES", self.helper)
        self.assertIn('"remaster.build_provenance"', self.helper)
        self.assertIn('"remaster.release_gate_summary"', self.helper)
        self.assertIn('"remaster.validation_coverage"', self.helper)
        self.assertIn('"remaster.playthrough_evaluation"', self.helper)
        self.assertIn("schema_mismatch", self.helper)
        self.assertIn("too_large", self.helper)
        self.assertIn("HashingContext.HASH_SHA256", self.helper)

    def test_f11_manifest_binds_included_framework_artifacts(self) -> None:
        self.assertIn("BugReportFrameworkContextScript", self.diagnostics)
        self.assertIn('"framework_context.json"', self.diagnostics)
        self.assertIn('"framework_artifacts"', self.diagnostics)
        self.assertIn('"sha256"', self.diagnostics)
        self.assertIn("framework_context", self.diagnostics)


if __name__ == "__main__":
    unittest.main()
