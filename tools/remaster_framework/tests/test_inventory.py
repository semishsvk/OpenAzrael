from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.remaster_framework.inventory import build_inventory, write_inventory


class InventoryTests(unittest.TestCase):
    def test_inventory_is_sorted_and_content_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.txt").write_text("beta", encoding="utf-8")
            (root / "a.txt").write_text("alpha", encoding="utf-8")

            first = build_inventory(root)
            second = build_inventory(root)

            self.assertEqual(first, second)
            self.assertEqual(
                [entry["path"] for entry in first["files"]],
                ["a.txt", "b.txt"],
            )

    def test_output_manifest_excludes_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "asset.bin").write_bytes(b"azrael")
            output = root / "inventory.json"

            first = write_inventory(root, output)
            second = write_inventory(root, output)

            self.assertEqual(first, second)
            self.assertEqual(first["file_count"], 1)
            self.assertEqual(first["files"][0]["path"], "asset.bin")
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                second,
            )


if __name__ == "__main__":
    unittest.main()
