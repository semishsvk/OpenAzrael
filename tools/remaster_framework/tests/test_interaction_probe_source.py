from __future__ import annotations

import unittest
from pathlib import Path


class InteractionProbeSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (root / "scripts" / "interaction_probe.gd").read_text(
            encoding="utf-8"
        )

    def test_probe_is_ray_first_then_checks_containing_interactive_area(self) -> None:
        ray_index = self.source.index("intersect_ray(q)")
        point_index = self.source.index("intersect_point(point_q, 16)")
        self.assertLess(ray_index, point_index)
        self.assertIn("PhysicsPointQueryParameters3D.new()", self.source)
        self.assertIn("point_q.position = from", self.source)
        self.assertIn("point_q.collision_mask = 2", self.source)
        self.assertIn("point_q.collide_with_areas = true", self.source)
        self.assertIn("point_q.collide_with_bodies = false", self.source)
        self.assertIn('collider.has_method("interact")', self.source)

    def test_probe_keeps_production_interact_input_path(self) -> None:
        self.assertIn('event.is_action_pressed("interact")', self.source)
        self.assertIn("n.interact()", self.source)
        self.assertIn('get_node_or_null("CandidateDiagnostics")', self.source)
        self.assertIn('has_method("record_interaction")', self.source)
        self.assertIn('call("record_interaction"', self.source)


if __name__ == "__main__":
    unittest.main()
