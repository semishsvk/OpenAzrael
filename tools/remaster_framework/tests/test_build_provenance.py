from __future__ import annotations

import unittest

from tools.remaster_framework.build_provenance import build_provenance


class BuildProvenanceTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_order_independent(self) -> None:
        common = {
            "project": "OpenAzrael",
            "commit_sha": "a" * 40,
            "project_version": "0.1.0-rc.1",
            "engine": {"name": "Godot", "version": "4.x"},
        }
        first = build_provenance(
            **common,
            inputs={"source": "b" * 64, "tools": "c" * 64},
        )
        second = build_provenance(
            **common,
            inputs={"tools": "c" * 64, "source": "b" * 64},
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["provenance_sha256"]), 64)

    def test_invalid_commit_sha_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_provenance(
                project="OpenAzrael",
                commit_sha="not-a-sha",
                project_version="0.1.0",
                engine={"name": "Godot", "version": "4.x"},
                inputs={},
            )

    def test_invalid_input_hash_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_provenance(
                project="OpenAzrael",
                commit_sha="a" * 40,
                project_version="0.1.0",
                engine={"name": "Godot", "version": "4.x"},
                inputs={"source": "bad"},
            )


if __name__ == "__main__":
    unittest.main()
