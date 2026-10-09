from __future__ import annotations

import unittest

from tools.remaster_framework.coverage import audit_validation_coverage


class ValidationCoverageTests(unittest.TestCase):
    def test_reports_uncovered_gameplay_targets(self) -> None:
        graph = {
            "nodes": [
                {"node_id": "room:R1", "kind": "room"},
                {"node_id": "gameplay:A", "kind": "gameplay_graph"},
                {"node_id": "gameplay:B", "kind": "gameplay_graph"},
            ]
        }
        bundle = {
            "schema": "openazrael.pppv_scenario_bundle",
            "scenarios": [
                {
                    "scenario_id": "scenario_a",
                    "metadata": {"coverage_targets": ["gameplay:A"]},
                }
            ],
        }
        report = audit_validation_coverage(graph, bundle)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["covered_target_count"], 1)
        self.assertEqual(report["uncovered_targets"], ["gameplay:B"])

    def test_complete_coverage_is_detected(self) -> None:
        graph = {
            "nodes": [
                {"node_id": "gameplay:A", "kind": "gameplay_graph"},
                {"node_id": "gameplay:B", "kind": "gameplay_graph"},
            ]
        }
        bundle = {
            "scenarios": [
                {
                    "scenario_id": "one",
                    "metadata": {
                        "coverage_targets": ["gameplay:A", "gameplay:B"]
                    },
                }
            ]
        }
        report = audit_validation_coverage(graph, bundle)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["coverage_ratio"], 1.0)

    def test_orphan_declared_target_is_visible(self) -> None:
        graph = {
            "nodes": [
                {"node_id": "gameplay:A", "kind": "gameplay_graph"},
            ]
        }
        bundle = {
            "scenarios": [
                {
                    "scenario_id": "newer_scenario",
                    "metadata": {
                        "coverage_targets": [
                            "gameplay:A",
                            "gameplay:NEWER_THAN_GRAPH",
                        ]
                    },
                }
            ]
        }
        report = audit_validation_coverage(graph, bundle)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(
            report["declared_targets_not_in_reference_graph"],
            ["gameplay:NEWER_THAN_GRAPH"],
        )


if __name__ == "__main__":
    unittest.main()
