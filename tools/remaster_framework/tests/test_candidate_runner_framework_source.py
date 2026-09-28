from __future__ import annotations

import unittest
from pathlib import Path


class CandidateRunnerFrameworkSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        supplemental = root / "tools" / "run_candidate3_pppv_v2.py"
        canonical = root / "tools" / "run_kg001_candidate_v112.py"
        self.runner_path = supplemental if supplemental.is_file() else canonical
        self.source = self.runner_path.read_text(encoding="utf-8")

    def test_framework_generation_occurs_after_g09_clean_observation(self) -> None:
        clean_after = self.source.index("clean_after=git_clean()")
        fresh_write = self.source.index(
            'write_json(TMP/"kg001_fresh_checkout.json",fresh)'
        )
        framework_cmd = self.source.index("framework_cmd=[")
        self.assertLess(clean_after, fresh_write)
        self.assertLess(fresh_write, framework_cmd)

    def test_runtime_metadata_staging_occurs_after_framework_bundle(self) -> None:
        framework_cmd = self.source.index("framework_cmd=[")
        stage = self.source.index("metadata_cmd=[")
        self.assertLess(framework_cmd, stage)
        self.assertIn("--stage-framework-metadata", self.source)

    def test_source_phase_includes_framework_and_diagnostics_gates(self) -> None:
        self.assertIn("tools.remaster_framework.cli", self.source)
        self.assertIn("tools/remaster_framework/tests", self.source)
        self.assertIn("runtime_capabilities", self.source)
        self.assertIn("validate_candidate_diagnostics_v116.py", self.source)
        self.assertIn("validate_kg001_contract.py", self.source)
        self.assertIn("validate_kg001_physical_traversal_v117.py", self.source)
        self.assertIn("validate_kg001_well_tongs_animation_v118.py", self.source)
        self.assertIn("kg001_physical_traversal_runner_v117.gd", self.source)
        self.assertIn("kg001_well_tongs_animation_runner_v118.gd", self.source)

    def test_real_input_well_pppv_is_supplemental_not_silent_g09_gate(self) -> None:
        self.assertIn("def run_well_pppv(godot):", self.source)
        self.assertIn("pppv_scenario_runner.gd", self.source)
        self.assertIn("tools.remaster_framework.evaluate_validation", self.source)
        self.assertIn("kg001_well_tongs_pppv.json", self.source)
        self.assertIn('"final_pppv_oracle":True', self.source)

        fresh_expression = self.source.split("fresh_pass=(", 1)[1].split(
            ")\n\n    fresh=", 1
        )[0]
        self.assertNotIn("well_pppv", fresh_expression)
        self.assertIn(
            '"well_tongs_real_input_pppv":well_pppv.get("status","")',
            self.source,
        )

    def test_framework_failure_affects_process_exit_but_not_recorded_g09(self) -> None:
        self.assertIn('framework_ok = framework_status == "PASS"', self.source)
        self.assertIn("fresh_pass and framework_ok and metadata_ok", self.source)
        self.assertIn(
            '"status":"PASS" if fresh_pass else',
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
