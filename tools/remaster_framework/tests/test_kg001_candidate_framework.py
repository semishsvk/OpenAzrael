from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.openazrael_adapters.kg001_candidate_framework import (
    _default_scenario_bundle,
    build_candidate_framework_bundle,
)


class KG001CandidateFrameworkTests(unittest.TestCase):
    def test_current_repo_auto_builds_v117_v118_scenarios(self) -> None:
        root = Path(__file__).resolve().parents[3]
        bundle = _default_scenario_bundle(root)
        ids = {row["scenario_id"] for row in bundle["scenarios"]}
        self.assertEqual(bundle["scenario_count"], 19)
        self.assertIn("openazrael.r1.pickup_tongs", ids)
        self.assertIn("openazrael.r1.open_door1", ids)
        self.assertIn("openazrael.r1.open_door2", ids)
        self.assertIn("openazrael.r1.open_door2.negative_without_key", ids)
        self.assertIn("openazrael.r7.water_switchboard", ids)
        self.assertIn(
            "openazrael.r7.water_switchboard.negative_wrong_sequence",
            ids,
        )
        self.assertIn("openazrael.r8.take_lens", ids)
        self.assertIn("openazrael.r8.place_lens", ids)
        self.assertIn("openazrael.r8.optical_sequence", ids)
        self.assertIn("openazrael.r8.take_shield", ids)
        self.assertIn("openazrael.transition.r1_to_r7", ids)
        self.assertIn("openazrael.transition.r7_to_r1", ids)
        self.assertIn("openazrael.transition.r1_to_r8", ids)
        self.assertIn("openazrael.r1.floor_traversal", ids)
        self.assertIn("openazrael.r7.well_tongs.positive", ids)
        self.assertIn(
            "openazrael.r7.well_tongs.negative_without_tongs",
            ids,
        )

    def _write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _repo(self, root: Path) -> None:
        (root / "project.godot").write_text(
            '[application]\nconfig/version="0.1.0-rc.1"\n',
            encoding="utf-8",
        )
        self._write(
            root / "data/kg001_acceptance_contract.json",
            {
                "schema": "openazrael.kg001_acceptance_contract",
                "version": 1,
                "target_tag": "demo-known-good-001",
                "gates": [
                    {
                        "id": f"G{i:02d}",
                        "name": f"gate_{i}",
                        "required": True,
                    }
                    for i in range(11)
                ],
                "forensic_boundary": {
                    "known_good_does_not_promote_holds": True,
                },
            },
        )
        self._write(
            root / "data/tests/kg001_state_space_v108.json",
            {"status": "PASS"},
        )
        self._write(
            root / "data/xaf_trigger_evidence.json",
            {
                "schema": 1,
                "rooms": {},
                "demo_transitions": [],
            },
        )
        self._write(
            root / "data/gameplay_event_graph_v87.json",
            {
                "version": 87,
                "graphs": {},
            },
        )
        self._write(
            root / "tools/remaster_framework/tool_manifest.json",
            {"schema_version": 1, "tools": []},
        )

    def _evidence(self, root: Path, manual: bool) -> Path:
        evidence = root / ".tmp/kg001"
        evidence.mkdir(parents=True)
        self._write(
            evidence / "kg001_source_validation_v112.json",
            {"status": "PASS"},
        )
        for version in (109, 110, 111, 117, 118):
            self._write(
                evidence / f"kg001_v{version}_runtime.json",
                {"status": "PASS"},
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
                },
            },
        )
        self._write(
            evidence / "kg001_candidate_v112.json",
            {"status": "PASS"},
        )
        if manual:
            self._write(
                evidence / "kg001_manual_sanity.json",
                {
                    "status": "PASS",
                    "critical_bugs": [],
                    "reproducible_softlocks": [],
                },
            )
        return evidence

    def test_bundle_is_blocked_without_manual_sanity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=False)

            bundle = build_candidate_framework_bundle(
                root,
                evidence,
                commit_sha="a" * 40,
                godot_version="4.x",
            )
            self.assertEqual(bundle["release_status"], "BLOCKED")
            self.assertFalse(bundle["known_good_eligible"])
            self.assertTrue((evidence / "build_provenance.json").is_file())
            self.assertTrue((evidence / "pppv_coverage.json").is_file())
            self.assertTrue(
                (evidence / "pppv_playthrough_plan.json").is_file()
            )
            self.assertEqual(
                bundle["pppv_playthrough_runtime_status"],
                "NOT_AVAILABLE",
            )
            self.assertEqual(
                bundle["pppv_playthrough_evaluation_status"],
                "NOT_AVAILABLE",
            )
            self.assertEqual(
                bundle["artifacts"]["pppv_playthrough_plan"],
                "pppv_playthrough_plan.json",
            )
            provenance = json.loads(
                (evidence / "build_provenance.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIn(
                "pppv_playthrough_plan",
                provenance["inputs"],
            )
            self.assertEqual(
                bundle["well_tongs_real_input_pppv_status"],
                "NOT_AVAILABLE",
            )

    def test_real_input_well_pppv_is_bound_into_provenance_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=False)
            self._write(
                evidence / "kg001_well_tongs_pppv.json",
                {
                    "schema": "openazrael.kg001.well_tongs_pppv",
                    "version": 1,
                    "status": "PASS",
                    "final_pppv_oracle": True,
                },
            )

            bundle = build_candidate_framework_bundle(
                root,
                evidence,
                commit_sha="a" * 40,
                godot_version="4.x",
            )
            self.assertEqual(
                bundle["well_tongs_real_input_pppv_status"],
                "PASS",
            )
            self.assertEqual(
                bundle["artifacts"]["well_tongs_real_input_pppv"],
                "kg001_well_tongs_pppv.json",
            )
            provenance = json.loads(
                (evidence / "build_provenance.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIn(
                "well_tongs_real_input_pppv",
                provenance["inputs"],
            )

    def test_complete_evidence_can_be_known_good_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=True)

            bundle = build_candidate_framework_bundle(
                root,
                evidence,
                commit_sha="a" * 40,
                godot_version="4.x",
                manual_path=evidence / "kg001_manual_sanity.json",
            )
            self.assertEqual(
                bundle["release_status"],
                "ELIGIBLE_FOR_KNOWN_GOOD",
            )
            self.assertTrue(bundle["known_good_eligible"])
            self.assertEqual(
                bundle["pppv_playthrough_runtime_status"],
                "NOT_AVAILABLE",
            )
            self.assertEqual(
                bundle["pppv_playthrough_evaluation_status"],
                "NOT_AVAILABLE",
            )


if __name__ == "__main__":
    unittest.main()
