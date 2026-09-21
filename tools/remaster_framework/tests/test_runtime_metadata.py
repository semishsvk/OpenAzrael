from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.remaster_framework.runtime_metadata import (
    clean_runtime_metadata,
    stage_runtime_metadata,
)


def canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class RuntimeMetadataTests(unittest.TestCase):
    def _write(self, path: Path, payload: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _provenance(self) -> dict:
        payload = {
            "schema": "remaster.build_provenance",
            "version": 1,
            "project": "OpenAzrael",
            "commit_sha": "a" * 40,
            "project_version": "0.1.0-rc.1",
            "engine": {"name": "Godot", "version": "4.x"},
            "inputs": {"source": "b" * 64},
            "metadata": {},
        }
        payload["provenance_sha256"] = canonical_hash(payload)
        return payload

    def _release(self) -> dict:
        payload = {
            "schema": "remaster.release_gate_summary",
            "version": 1,
            "status": "BLOCKED",
            "target_tag": "demo-known-good-001",
            "blockers": ["manual sanity missing"],
        }
        payload["summary_sha256"] = canonical_hash(payload)
        return payload

    def _coverage(self) -> dict:
        return {
            "schema": "remaster.validation_coverage",
            "version": 1,
            "status": "INCOMPLETE",
            "required_target_count": 5,
            "covered_target_count": 1,
            "coverage_ratio": 0.2,
        }

    def _playthrough_evaluation(self) -> dict:
        return {
            "schema": "remaster.playthrough_evaluation",
            "version": 1,
            "plan_id": "kg001_demo_real_player_v1",
            "status": "PASS",
            "errors": [],
            "step_count": 14,
            "final_state_sha256": "c" * 64,
            "expected_final_state_sha256": "c" * 64,
        }

    def test_stage_and_clean_source_safe_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            provenance = self._write(
                inputs / "provenance.json",
                self._provenance(),
            )
            release = self._write(
                inputs / "release.json",
                self._release(),
            )
            coverage = self._write(
                inputs / "coverage.json",
                self._coverage(),
            )

            result = stage_runtime_metadata(
                root,
                build_provenance=provenance,
                release_gate_summary=release,
                pppv_coverage=coverage,
            )
            self.assertEqual(result["staged_count"], 3)
            self.assertTrue(result["source_safe"])
            self.assertFalse(result["commercial_assets_included"])
            self.assertTrue(
                all(len(row["sha256"]) == 64 for row in result["staged"])
            )

            runtime = root / "data" / "runtime"
            self.assertTrue((runtime / "build_provenance.json").is_file())
            self.assertTrue((runtime / "release_gate_summary.json").is_file())
            self.assertTrue((runtime / "pppv_coverage.json").is_file())

            removed = clean_runtime_metadata(root)
            self.assertEqual(len(removed), 3)
            self.assertFalse((runtime / "build_provenance.json").exists())

    def test_wrong_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._write(root / "wrong.json", {"schema": "wrong.schema"})
            with self.assertRaises(ValueError):
                stage_runtime_metadata(root, build_provenance=source)

    def test_tampered_internal_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self._provenance()
            payload["project_version"] = "tampered"
            source = self._write(root / "provenance.json", payload)
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                stage_runtime_metadata(root, build_provenance=source)

    def test_framework_bundle_stages_three_bound_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            self._write(evidence / "build_provenance.json", self._provenance())
            self._write(evidence / "release_gate_summary.json", self._release())
            self._write(evidence / "pppv_coverage.json", self._coverage())
            bundle = self._write(
                evidence / "kg001_framework_bundle.json",
                {
                    "schema": "openazrael.kg001.framework_bundle",
                    "version": 1,
                    "artifacts": {
                        "build_provenance": "build_provenance.json",
                        "release_gate_summary": "release_gate_summary.json",
                        "pppv_coverage": "pppv_coverage.json",
                    },
                },
            )

            result = stage_runtime_metadata(
                root,
                framework_bundle=bundle,
            )
            self.assertEqual(result["staged_count"], 3)

    def test_framework_bundle_optionally_stages_playthrough_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            self._write(evidence / "build_provenance.json", self._provenance())
            self._write(evidence / "release_gate_summary.json", self._release())
            self._write(evidence / "pppv_coverage.json", self._coverage())
            self._write(
                evidence / "pppv_playthrough_evaluation.json",
                self._playthrough_evaluation(),
            )
            bundle = self._write(
                evidence / "kg001_framework_bundle.json",
                {
                    "schema": "openazrael.kg001.framework_bundle",
                    "version": 1,
                    "artifacts": {
                        "build_provenance": "build_provenance.json",
                        "release_gate_summary": "release_gate_summary.json",
                        "pppv_coverage": "pppv_coverage.json",
                        "pppv_playthrough_evaluation": (
                            "pppv_playthrough_evaluation.json"
                        ),
                    },
                },
            )

            result = stage_runtime_metadata(root, framework_bundle=bundle)
            self.assertEqual(result["staged_count"], 4)
            runtime = root / "data" / "runtime"
            self.assertTrue(
                (runtime / "pppv_playthrough_evaluation.json").is_file()
            )

    def test_framework_bundle_cannot_escape_its_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            evidence.mkdir()
            bundle = self._write(
                evidence / "kg001_framework_bundle.json",
                {
                    "schema": "openazrael.kg001.framework_bundle",
                    "version": 1,
                    "artifacts": {
                        "build_provenance": "../outside.json",
                        "release_gate_summary": "release_gate_summary.json",
                        "pppv_coverage": "pppv_coverage.json",
                    },
                },
            )
            with self.assertRaisesRegex(ValueError, "escapes bundle directory"):
                stage_runtime_metadata(root, framework_bundle=bundle)

    def test_bundle_and_explicit_inputs_cannot_be_mixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            bundle = self._write(
                evidence / "kg001_framework_bundle.json",
                {
                    "schema": "openazrael.kg001.framework_bundle",
                    "version": 1,
                    "artifacts": {},
                },
            )
            provenance = self._write(
                root / "provenance.json",
                self._provenance(),
            )
            with self.assertRaisesRegex(ValueError, "cannot be combined"):
                stage_runtime_metadata(
                    root,
                    framework_bundle=bundle,
                    build_provenance=provenance,
                )


if __name__ == "__main__":
    unittest.main()
