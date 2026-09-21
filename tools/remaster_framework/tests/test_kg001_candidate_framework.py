from __future__ import annotations

import hashlib
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
        self.assertEqual(bundle["scenario_count"], 20)
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
        self.assertIn("openazrael.transition.r8_to_r1", ids)
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

    def _materialize_passing_pppv_evidence(
        self,
        root: Path,
        evidence: Path,
    ) -> None:
        build_candidate_framework_bundle(
            root,
            evidence,
            commit_sha="a" * 40,
            godot_version="4.x",
        )
        scenario_path = evidence / "pppv_scenarios.json"
        scenario_bundle = json.loads(
            scenario_path.read_text(encoding="utf-8")
        )
        scenario_ids = sorted(
            row["scenario_id"]
            for row in scenario_bundle["scenarios"]
        )
        transition_ids = sorted(
            value
            for value in scenario_ids
            if value.startswith("openazrael.transition.")
        )
        profiles = {}
        for row in scenario_bundle["scenarios"]:
            metadata = row.get("metadata", {})
            profile = (
                metadata.get("execution_profile")
                if isinstance(metadata, dict)
                else None
            )
            profiles[row["scenario_id"]] = (
                profile or "guarded_generic_runtime"
            )
        bridge_ids = sorted(
            scenario_id
            for scenario_id, profile in profiles.items()
            if profile == "v117_real_geometry_input"
        )
        guarded_ids = sorted(
            scenario_id
            for scenario_id, profile in profiles.items()
            if profile == "guarded_generic_runtime"
        )
        bundle_sha = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
        self._write(
            evidence / "kg001_pppv_scenario_suite.json",
            {
                "schema": "openazrael.kg001.pppv_scenario_suite",
                "version": 1,
                "status": "PASS",
                "scenario_bundle": ".tmp/kg001/pppv_scenarios.json",
                "scenario_bundle_sha256": bundle_sha,
                "scenario_count": len(scenario_ids),
                "passed": len(scenario_ids),
                "failed": 0,
                "transition_scenario_count": len(transition_ids),
                "transition_scenario_ids": transition_ids,
                "guarded_scenario_count": len(guarded_ids),
                "v117_bridge_scenario_count": len(bridge_ids),
                "all_authored_scenarios_executed": True,
                "all_transition_scenarios_guarded": True,
                "scenarios": {
                    scenario_id: {
                        "status": "PASS",
                        "execution_profile": profiles[scenario_id],
                        "guarded_replay": (
                            profiles[scenario_id]
                            == "guarded_generic_runtime"
                        ),
                    }
                    for scenario_id in scenario_ids
                },
            },
        )
        plan_path = evidence / "pppv_playthrough_plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_sha = str(plan.get("plan_sha256", ""))
        final_hash = str(plan.get("success_state_sha256", ""))
        semantic_hash = "d" * 64
        evaluation = {
            "schema": "remaster.playthrough_evaluation",
            "version": 1,
            "status": "PASS",
            "plan_sha256": plan_sha,
            "semantic_replay_sha256": semantic_hash,
            "final_state_sha256": final_hash,
        }
        self._write(
            evidence / "kg001_pppv_playthrough_evaluation.json",
            evaluation,
        )
        self._write(
            evidence / "kg001_pppv_playthrough_repeat2_evaluation.json",
            evaluation,
        )
        self._write(
            evidence / "kg001_pppv_determinism.json",
            {
                "schema": "openazrael.kg001.pppv_determinism",
                "version": 1,
                "status": "PASS",
                "plan_sha256": plan_sha,
                "plan_document_sha256": hashlib.sha256(
                    plan_path.read_bytes()
                ).hexdigest(),
                "scenario_bundle_sha256": bundle_sha,
                "repeat_count": 2,
                "all_runs_pass": True,
                "semantic_replay_sha256": [
                    semantic_hash,
                    semantic_hash,
                ],
                "final_state_sha256": [
                    final_hash,
                    final_hash,
                ],
                "semantic_replay_match": True,
                "final_state_match": True,
            },
        )
        fresh_path = evidence / "kg001_fresh_checkout.json"
        fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
        fresh["runtime_status"]["pppv_scenario_suite"] = "PASS"
        fresh["runtime_status"]["pppv_playthrough"] = "PASS"
        self._write(fresh_path, fresh)

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

    def test_stale_playthrough_runtime_plan_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=False)
            self._write(
                evidence / "kg001_pppv_playthrough.json",
                {
                    "schema": "remaster.runtime_playthrough_bundle",
                    "version": 1,
                    "status": "EXECUTION_PASS",
                    "plan": {
                        "schema": "remaster.playthrough_plan",
                        "version": 1,
                        "plan_id": "stale",
                        "plan_sha256": "f" * 64,
                        "steps": [],
                    },
                    "steps": [],
                    "failures": [],
                    "runtime_boundary": {},
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "runtime plan hash does not match",
            ):
                build_candidate_framework_bundle(
                    root,
                    evidence,
                    commit_sha="a" * 40,
                    godot_version="4.x",
                )


    def test_stale_pppv_suite_hash_is_blocked_by_integrity_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=True)
            self._materialize_passing_pppv_evidence(root, evidence)

            suite_path = evidence / "kg001_pppv_scenario_suite.json"
            suite = json.loads(suite_path.read_text(encoding="utf-8"))
            suite["scenario_bundle_sha256"] = "f" * 64
            self._write(suite_path, suite)

            bundle = build_candidate_framework_bundle(
                root,
                evidence,
                commit_sha="a" * 40,
                godot_version="4.x",
                manual_path=evidence / "kg001_manual_sanity.json",
            )
            self.assertEqual(
                bundle["pppv_scenario_suite_integrity_status"],
                "FAIL",
            )
            self.assertEqual(bundle["release_status"], "BLOCKED")
            self.assertFalse(bundle["known_good_eligible"])

            integrity = json.loads(
                (evidence / "pppv_scenario_suite_integrity.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(integrity["status"], "FAIL")
            self.assertTrue(
                any("SHA-256 mismatch" in item for item in integrity["errors"])
            )


    def test_stale_determinism_scenario_hash_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=True)
            self._materialize_passing_pppv_evidence(root, evidence)

            determinism_path = evidence / "kg001_pppv_determinism.json"
            determinism = json.loads(
                determinism_path.read_text(encoding="utf-8")
            )
            determinism["scenario_bundle_sha256"] = "f" * 64
            self._write(determinism_path, determinism)

            bundle = build_candidate_framework_bundle(
                root,
                evidence,
                commit_sha="a" * 40,
                godot_version="4.x",
                manual_path=evidence / "kg001_manual_sanity.json",
            )
            self.assertEqual(
                bundle["pppv_determinism_integrity_status"],
                "FAIL",
            )
            self.assertEqual(bundle["release_status"], "BLOCKED")
            self.assertFalse(bundle["known_good_eligible"])

    def test_mismatched_repeat_evaluation_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=True)
            self._materialize_passing_pppv_evidence(root, evidence)

            repeat_path = (
                evidence / "kg001_pppv_playthrough_repeat2_evaluation.json"
            )
            repeat = json.loads(repeat_path.read_text(encoding="utf-8"))
            repeat["semantic_replay_sha256"] = "e" * 64
            self._write(repeat_path, repeat)

            bundle = build_candidate_framework_bundle(
                root,
                evidence,
                commit_sha="a" * 40,
                godot_version="4.x",
                manual_path=evidence / "kg001_manual_sanity.json",
            )
            self.assertEqual(
                bundle["pppv_determinism_integrity_status"],
                "FAIL",
            )
            integrity = json.loads(
                (evidence / "pppv_determinism_integrity.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(
                any(
                    "semantic replay hashes differ" in item
                    for item in integrity["errors"]
                )
            )

    def test_complete_evidence_can_be_known_good_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            evidence = self._evidence(root, manual=True)
            self._materialize_passing_pppv_evidence(root, evidence)

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
