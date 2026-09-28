from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.openazrael_adapters.kg001_release_evidence import (
    build_gate_results,
)


class KG001ReleaseEvidenceTests(unittest.TestCase):
    def _write(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _prepare(self, root: Path, *, manual_status: str = "PASS") -> Path:
        evidence = root / "evidence"
        evidence.mkdir()
        data = root / "data" / "tests"
        data.mkdir(parents=True)

        self._write(
            data / "kg001_state_space_v108.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_source_validation_v112.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_v109_runtime.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_v110_runtime.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_v111_runtime.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_v117_runtime.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_v118_runtime.json",
            {"status": "PASS"},
        )
        self._write(
            evidence / "kg001_pppv_scenario_suite.json",
            {
                "schema": "openazrael.kg001.pppv_scenario_suite",
                "version": 1,
                "status": "PASS",
                "scenario_count": 20,
                "passed": 20,
            },
        )
        self._write(
            evidence / "pppv_scenario_suite_integrity.json",
            {
                "schema": "openazrael.kg001.pppv_scenario_suite_integrity",
                "version": 1,
                "status": "PASS",
            },
        )
        self._write(
            evidence / "kg001_pppv_playthrough_evaluation.json",
            {
                "schema": "remaster.playthrough_evaluation",
                "version": 1,
                "status": "PASS",
            },
        )
        self._write(
            evidence / "kg001_pppv_determinism.json",
            {
                "schema": "openazrael.kg001.pppv_determinism",
                "version": 1,
                "status": "PASS",
                "repeat_count": 2,
                "all_runs_pass": True,
                "semantic_replay_match": True,
                "final_state_match": True,
            },
        )
        self._write(
            evidence / "pppv_determinism_integrity.json",
            {
                "schema": "openazrael.kg001.pppv_determinism_integrity",
                "version": 1,
                "status": "PASS",
            },
        )
        self._write(
            evidence / "kg001_fresh_checkout.json",
            {
                "status": "PASS",
                "commit_sha": "a" * 40,
                "runtime_status": {
                    "v109": "PASS",
                    "v110": "PASS",
                    "v111": "PASS",
                    "v117": "PASS",
                    "v118": "PASS",
                    "pppv_scenario_suite": "PASS",
                    "pppv_playthrough": "PASS",
                },
            },
        )
        self._write(
            evidence / "kg001_manual_sanity.json",
            {
                "status": manual_status,
                "critical_bugs": [],
                "reproducible_softlocks": [],
            },
        )
        return evidence

    def test_complete_existing_evidence_maps_to_g00_g10(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            result = build_gate_results(root, evidence)

            self.assertEqual(
                [row["id"] for row in result["gates"]],
                [f"G{i:02d}" for i in range(11)],
            )
            self.assertTrue(
                all(row["status"] == "PASS" for row in result["gates"])
            )
            self.assertTrue(result["defects"]["inventory_complete"])
            self.assertEqual(result["candidate"]["commit_sha"], "a" * 40)
            self.assertTrue(
                all(
                    len(item["sha256"]) == 64
                    for row in result["gates"]
                    for item in row["evidence"]
                )
            )


    def test_guarded_scenario_suite_is_required_for_g04_and_g05(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            (evidence / "kg001_pppv_scenario_suite.json").unlink()

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G04"], "PENDING")
            self.assertEqual(statuses["G05"], "PENDING")
            self.assertEqual(statuses["G08"], "PASS")

    def test_failed_guarded_scenario_suite_blocks_g04_and_g05(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "kg001_pppv_scenario_suite.json",
                {"status": "FAIL"},
            )

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G04"], "FAIL")
            self.assertEqual(statuses["G05"], "FAIL")


    def test_missing_suite_integrity_blocks_transition_and_fresh_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            (evidence / "pppv_scenario_suite_integrity.json").unlink()

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G04"], "PENDING")
            self.assertEqual(statuses["G05"], "PENDING")
            self.assertEqual(statuses["G09"], "PENDING")

    def test_failed_suite_integrity_blocks_transition_and_fresh_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "pppv_scenario_suite_integrity.json",
                {"status": "FAIL"},
            )

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G04"], "FAIL")
            self.assertEqual(statuses["G05"], "FAIL")
            self.assertEqual(statuses["G09"], "FAIL")

    def test_guarded_chained_playthrough_is_required_for_g08(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            (evidence / "kg001_pppv_playthrough_evaluation.json").unlink()

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G04"], "PASS")
            self.assertEqual(statuses["G05"], "PASS")
            self.assertEqual(statuses["G08"], "PENDING")

    def test_failed_guarded_chained_playthrough_blocks_g08(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "kg001_pppv_playthrough_evaluation.json",
                {"status": "FAIL"},
            )

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G08"], "FAIL")


    def test_missing_determinism_blocks_g08_and_g09(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            (evidence / "kg001_pppv_determinism.json").unlink()

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G08"], "PENDING")
            self.assertEqual(statuses["G09"], "PENDING")

    def test_failed_determinism_blocks_g08_and_g09(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "kg001_pppv_determinism.json",
                {"status": "FAIL"},
            )

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G08"], "FAIL")
            self.assertEqual(statuses["G09"], "FAIL")

    def test_missing_determinism_integrity_blocks_g08_and_g09(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            (evidence / "pppv_determinism_integrity.json").unlink()

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G08"], "PENDING")
            self.assertEqual(statuses["G09"], "PENDING")

    def test_failed_determinism_integrity_blocks_g08_and_g09(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "pppv_determinism_integrity.json",
                {"status": "FAIL"},
            )

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G08"], "FAIL")
            self.assertEqual(statuses["G09"], "FAIL")

    def test_supplemental_v117_v118_checks_are_evidence_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            result = build_gate_results(root, evidence)

            checks = {row["id"]: row for row in result["supplemental_checks"]}
            self.assertEqual(checks["V117_PHYSICAL_TRAVERSAL"]["status"], "PASS")
            self.assertEqual(checks["V118_WELL_TONGS"]["status"], "PASS")
            self.assertEqual(
                len(checks["V117_PHYSICAL_TRAVERSAL"]["evidence"][0]["sha256"]),
                64,
            )

    def test_stale_fresh_checkout_without_v117_v118_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "kg001_fresh_checkout.json",
                {
                    "status": "PASS",
                    "commit_sha": "a" * 40,
                    "runtime_status": {
                        "v109": "PASS",
                        "v110": "PASS",
                        "v111": "PASS",
                    },
                },
            )

            result = build_gate_results(root, evidence)
            g09 = next(row for row in result["gates"] if row["id"] == "G09")
            self.assertEqual(g09["status"], "PENDING")

    def test_real_input_well_pppv_is_supplemental_and_evidence_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "kg001_well_tongs_pppv.json",
                {
                    "schema": "openazrael.kg001.well_tongs_pppv",
                    "version": 1,
                    "status": "PASS",
                    "final_pppv_oracle": True,
                },
            )

            result = build_gate_results(root, evidence)
            checks = {row["id"]: row for row in result["supplemental_checks"]}
            row = checks["PPPV_WELL_REAL_INPUT"]
            self.assertEqual(row["status"], "PASS")
            self.assertFalse(row["required_for_g09"])
            self.assertEqual(len(row["evidence"][0]["sha256"]), 64)

    def test_missing_manual_keeps_g10_pending_and_defects_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            (evidence / "kg001_manual_sanity.json").unlink()

            result = build_gate_results(root, evidence)

            g10 = next(row for row in result["gates"] if row["id"] == "G10")
            self.assertEqual(g10["status"], "PENDING")
            self.assertFalse(result["defects"]["inventory_complete"])

    def test_failed_runtime_propagates_to_dependent_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self._prepare(root)
            self._write(
                evidence / "kg001_v110_runtime.json",
                {"status": "FAIL"},
            )

            result = build_gate_results(root, evidence)
            statuses = {row["id"]: row["status"] for row in result["gates"]}
            self.assertEqual(statuses["G04"], "FAIL")
            self.assertEqual(statuses["G05"], "FAIL")


if __name__ == "__main__":
    unittest.main()
