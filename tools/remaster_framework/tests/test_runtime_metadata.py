from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.remaster_framework.runtime_metadata import (
    clean_runtime_metadata,
    stage_runtime_metadata,
)


class RuntimeMetadataTests(unittest.TestCase):
    def _write(self, path: Path, schema: str, **extra) -> Path:
        payload = {"schema": schema, **extra}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_stage_and_clean_source_safe_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            inputs.mkdir()
            provenance = self._write(
                inputs / "provenance.json",
                "remaster.build_provenance",
                provenance_sha256="a" * 64,
            )
            release = self._write(
                inputs / "release.json",
                "remaster.release_gate_summary",
                status="BLOCKED",
            )
            coverage = self._write(
                inputs / "coverage.json",
                "remaster.validation_coverage",
                status="INCOMPLETE",
            )

            result = stage_runtime_metadata(
                root,
                build_provenance=provenance,
                release_gate_summary=release,
                pppv_coverage=coverage,
            )
            self.assertEqual(result["staged_count"], 3)

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
            source = root / "wrong.json"
            self._write(source, "wrong.schema")
            with self.assertRaises(ValueError):
                stage_runtime_metadata(root, build_provenance=source)


if __name__ == "__main__":
    unittest.main()
