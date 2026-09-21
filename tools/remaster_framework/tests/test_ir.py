from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.remaster_framework.ir import IRKind, describe_json_ir


class IRAdapterTests(unittest.TestCase):
    def test_declared_schema_is_preserved(self) -> None:
        payload = {
            "schema": "openazrael.legacy_world_ir",
            "version": 1,
        }
        descriptor = describe_json_ir(Path("legacy_world_ir.json"), payload)
        self.assertEqual(descriptor.schema_id, "openazrael.legacy_world_ir")
        self.assertEqual(descriptor.schema_version, 1)
        self.assertFalse(descriptor.legacy)
        self.assertEqual(descriptor.kind, IRKind.WORLD)

    def test_existing_gameplay_graph_gets_legacy_adapter(self) -> None:
        root = Path(__file__).resolve().parents[3]
        path = root / "data" / "gameplay_event_graph_v87.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        descriptor = describe_json_ir(path, payload)
        self.assertEqual(descriptor.schema_id, "openazrael.gameplay_event_graph")
        self.assertEqual(descriptor.schema_version, 87)
        self.assertEqual(descriptor.kind, IRKind.GAMEPLAY_GRAPH)
        self.assertTrue(descriptor.legacy)

    def test_existing_numeric_xaf_schema_gets_named_adapter(self) -> None:
        root = Path(__file__).resolve().parents[3]
        path = root / "data" / "xaf_trigger_evidence.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        descriptor = describe_json_ir(path, payload)
        self.assertEqual(descriptor.schema_id, "openazrael.xaf_trigger_evidence")
        self.assertEqual(descriptor.schema_version, 1)
        self.assertEqual(descriptor.kind, IRKind.TRIGGER_GRAPH)
        self.assertTrue(descriptor.legacy)


if __name__ == "__main__":
    unittest.main()
