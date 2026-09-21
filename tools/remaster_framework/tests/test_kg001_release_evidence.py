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
            evidence / "kg001_fresh_checkout.json",
            {"status": "PASS", "commit_sha": "a" * 40},
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
