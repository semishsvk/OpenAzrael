from __future__ import annotations

import unittest
from pathlib import Path


class PPPVSceneObserverSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (
            root / "scripts" / "validation" / "pppv_scene_observer.gd"
        ).read_text(encoding="utf-8")

    def test_observer_emits_transform_and_visibility_evidence(self) -> None:
        self.assertIn('evidence.record("scene_change"', self.source)
        self.assertIn('"position_changed"', self.source)
        self.assertIn('"rotation_changed"', self.source)
        self.assertIn('"transform_changed"', self.source)
        self.assertIn('"visibility_changed"', self.source)
        self.assertIn('"before_visible"', self.source)
        self.assertIn('"after_visible"', self.source)

    def test_observer_never_mutates_scene_nodes(self) -> None:
        self.assertNotIn(".global_position =", self.source)
        self.assertNotIn(".global_rotation =", self.source)
        self.assertNotIn(".rotation =", self.source)
        self.assertNotIn(".visible =", self.source)
        self.assertNotIn("set_global_", self.source)
        self.assertNotIn("set_visible", self.source)


if __name__ == "__main__":
    unittest.main()
