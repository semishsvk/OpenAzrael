from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.remaster_framework.release import aggregate_release


class ReleaseGateTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.contract = json.loads(
            (root / "data" / "kg001_acceptance_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.gates = [
            {
                "id": row["id"],
                "status": "PASS",
                "evidence": [
                    {
                        "path": f"evidence/{row['id']}.json",
                        "sha256": "a" * 64,
                    }
                ],
            }
            for row in self.contract["gates"]
        ]

    def _results(self) -> dict:
        return {
            "schema": "remaster.release_gate_results",
            "version": 1,
            "candidate": {
                "commit_sha": "b" * 40,
                "build_id": "0.1.0-rc.1",
            },
            "defects": {
                "inventory_complete": True,
                "known_critical_bugs": 0,
                "reproducible_softlocks": 0,
            },
            "gates": [dict(row) for row in self.gates],
            "holds": [
                {
                    "id": "HOLD_ORIGINAL_AUDIO_PARITY",
                    "status": "HOLD",
                }
            ],
        }

    def test_all_existing_kg001_gates_can_be_aggregated(self) -> None:
        summary = aggregate_release(self.contract, self._results())
        self.assertEqual(summary["status"], "ELIGIBLE_FOR_KNOWN_GOOD")
        self.assertEqual(len(summary["gates"]), 11)
        self.assertFalse(summary["automatic_tag_creation"])
        self.assertEqual(len(summary["summary_sha256"]), 64)

    def test_required_gate_failure_blocks_release(self) -> None:
        results = self._results()
        for row in results["gates"]:
            if row["id"] == "G05":
                row["status"] = "FAIL"
        summary = aggregate_release(self.contract, results)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertTrue(any("G05" in item for item in summary["blockers"]))

    def test_critical_bug_or_softlock_blocks_release(self) -> None:
        results = self._results()
        results["defects"]["known_critical_bugs"] = 1
        results["defects"]["reproducible_softlocks"] = 1
        summary = aggregate_release(self.contract, results)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertTrue(any("critical" in item for item in summary["blockers"]))
        self.assertTrue(any("softlocks" in item for item in summary["blockers"]))

    def test_incomplete_defect_inventory_blocks_release(self) -> None:
        results = self._results()
        results["defects"]["inventory_complete"] = False
        summary = aggregate_release(self.contract, results)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertTrue(
            any("defect inventory" in item for item in summary["blockers"])
        )

    def test_missing_manual_gate_blocks_release(self) -> None:
        results = self._results()
        results["gates"] = [
            row for row in results["gates"] if row["id"] != "G10"
        ]
        summary = aggregate_release(self.contract, results)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertTrue(any("G10" in item for item in summary["blockers"]))

    def test_holds_remain_holds_and_do_not_become_verified(self) -> None:
        summary = aggregate_release(self.contract, self._results())
        self.assertEqual(summary["holds"][0]["status"], "HOLD")
        self.assertTrue(
            summary["forensic_boundary"]["known_good_does_not_promote_holds"]
        )


if __name__ == "__main__":
    unittest.main()
