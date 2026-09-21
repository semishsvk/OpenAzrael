from __future__ import annotations

import unittest

from tools.remaster_framework.graph import ReferenceGraph


class ReferenceGraphTests(unittest.TestCase):
    def test_graph_is_deterministic(self) -> None:
        first = ReferenceGraph(project="Test")
        first.add_node("b", "room", "B")
        first.add_node("a", "room", "A")
        first.add_edge("a", "links", "b")

        second = ReferenceGraph(project="Test")
        second.add_node("a", "room", "A")
        second.add_node("b", "room", "B")
        second.add_edge("a", "links", "b")

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.validate(), [])

    def test_missing_endpoint_is_reported(self) -> None:
        graph = ReferenceGraph(project="Test")
        graph.add_node("a", "room", "A")
        graph.add_edge("a", "links", "missing")
        self.assertTrue(any("missing target" in item for item in graph.validate()))


if __name__ == "__main__":
    unittest.main()
