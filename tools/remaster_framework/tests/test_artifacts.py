from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.remaster_framework.artifacts import (
    build_artifact_manifest,
    verify_artifact_manifest,
    write_artifact_manifest,
)


class ArtifactManifestTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "z.json").write_text('{"version": 2}\n', encoding="utf-8")
            (root / "a.json").write_text(
                '{"schema":"example.world","version":1}\n',
                encoding="utf-8",
            )

            first = build_artifact_manifest(root, project="Test")
            second = build_artifact_manifest(root, project="Test")

            self.assertEqual(first, second)
            self.assertEqual(
                [item["path"] for item in first["artifacts"]],
                ["a.json", "z.json"],
            )

    def test_output_manifest_excludes_itself_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.json").write_text(
                '{"schema":"example.audit","version":1}\n',
                encoding="utf-8",
            )
            manifest = root / "catalog.json"

            first = write_artifact_manifest(root, manifest, project="Test")
            second = write_artifact_manifest(root, manifest, project="Test")

            self.assertEqual(first, second)
            self.assertEqual(first["artifact_count"], 1)
            self.assertEqual(verify_artifact_manifest(root, manifest), [])

    def test_verifier_detects_content_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_text('{"version":1}\n', encoding="utf-8")
            manifest = root / "catalog.json"
            write_artifact_manifest(root, manifest, project="Test")

            source.write_text('{"version":2}\n', encoding="utf-8")
            errors = verify_artifact_manifest(root, manifest)

            self.assertTrue(any("hash drift" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
