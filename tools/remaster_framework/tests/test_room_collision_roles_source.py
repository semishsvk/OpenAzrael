from __future__ import annotations

import json
import unittest
from pathlib import Path


class RoomCollisionRoleSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.source = (
            root / "scripts" / "room_manager.gd"
        ).read_text(encoding="utf-8")
        self.contract = json.loads(
            (
                root
                / "data"
                / "tests"
                / "kg001_collision_role_contract_v120.json"
            ).read_text(encoding="utf-8")
        )

    def _role(self, room: str, object_name: str) -> dict:
        return next(
            row
            for row in self.contract["roles"]
            if row["room"] == room and row["object"] == object_name
        )

    def test_contract_records_r1_object02_as_required_tunnel_support(self) -> None:
        row = self._role("R1", "Object02")
        self.assertEqual(row["xaf_material"], "TUNNEL")
        self.assertEqual(row["triangle_count"], 8)
        self.assertEqual(row["upward_floor_triangles"], 2)
        self.assertTrue(row["route_intersects_xz_bounds"])
        self.assertTrue(row["collision_required"])
        self.assertEqual(row["severity_if_missing"], "CRITICAL")

    def test_deep_r7_drown_planes_are_room_specific_exclusions(self) -> None:
        for object_name in ("Object02", "Object03"):
            row = self._role("R7", object_name)
            self.assertEqual(row["xaf_material"], "1DROWN")
            self.assertFalse(row["collision_required"])

        self.assertIn("NON_COLLIDING_OBJECTS_BY_ROOM", self.source)
        self.assertIn('"R7": {', self.source)
        self.assertIn('"Object02": true', self.source)
        self.assertIn('"Object03": true', self.source)

    def test_r1_object02_is_not_globally_blacklisted(self) -> None:
        self.assertNotIn(
            'obj_name in ["Object02", "Object03"',
            self.source,
        )
        self.assertIn(
            "_collision_excluded(room_id, obj_name)",
            self.source,
        )

    def test_portal_views_are_derived_per_room(self) -> None:
        self.assertIn("func _portal_view_names(room_id: String)", self.source)
        self.assertIn(
            'evidence["rooms"][room_id].get("portal_views", [])',
            self.source,
        )
        self.assertIn("portal_views.has(obj_name)", self.source)

    def test_legacy_trimeshes_keep_two_sided_collision(self) -> None:
        self.assertIn(
            "ConcavePolygonShape3D",
            self.source,
        )
        self.assertIn("backface_collision = true", self.source)


if __name__ == "__main__":
    unittest.main()
