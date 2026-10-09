from __future__ import annotations

import unittest
from pathlib import Path

from tools.remaster_framework.registry import ToolRegistry


class RegistryTests(unittest.TestCase):
    def test_manifest_has_unique_valid_entrypoints(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        registry = ToolRegistry.load()
        self.assertGreater(len(registry.all()), 0)
        self.assertEqual(registry.validate(repo_root), [])

    def test_source_safe_inventory_is_registered(self) -> None:
        item = ToolRegistry.load().get("source_safe_inventory")
        self.assertTrue(item.source_safe)
        self.assertTrue(item.deterministic)
        self.assertFalse(item.mutates_runtime)


if __name__ == "__main__":
    unittest.main()
