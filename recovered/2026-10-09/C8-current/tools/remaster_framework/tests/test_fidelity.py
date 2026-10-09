from __future__ import annotations

import unittest

from tools.remaster_framework.fidelity import (
    FidelityLayer,
    build_forensic_report,
    canonical_json_sha256,
    validate_room_fidelity_manifest,
)

class FidelityTests(unittest.TestCase):
    def test_manifest_rejects_incomplete_mesh_metadata(self) -> None:
        payload = {
            "schema": "remaster.room_fidelity_manifest",
            "version": 1,
            "quantization": 1e-5,
            "rooms": {
                "R1": {
                    "asset_sha256": "a" * 64,
                    "mesh_count": 1,
                    "triangle_count": 2,
                    "meshes": [{
                        "node": "floor",
                        "triangles": 2,
                        "uv_sha256": "b" * 64,
                        "transform": [0] * 16,
                        "bounds": [0] * 6,
                    }],
                }
            },
        }
        self.assertEqual(validate_room_fidelity_manifest(payload), [])
        payload["rooms"]["R1"]["meshes"][0]["transform"] = [0] * 15
        self.assertTrue(validate_room_fidelity_manifest(payload))

    def test_report_fails_closed_on_missing_layer(self) -> None:
        report = build_forensic_report(
            "R1",
            [FidelityLayer("source", "PASS", "a" * 64, {})],
            ("source", "runtime", "package"),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["missing_layers"], ["runtime", "package"])

    def test_canonical_hash_is_order_invariant(self) -> None:
        self.assertEqual(
            canonical_json_sha256({"a": 1, "b": 2}),
            canonical_json_sha256({"b": 2, "a": 1}),
        )

if __name__ == "__main__":
    unittest.main()
