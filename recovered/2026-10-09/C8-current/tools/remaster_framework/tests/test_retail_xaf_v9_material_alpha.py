from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.texture_pipeline import export_xaf_glb_v9


class RetailXafV9MaterialAlphaTests(unittest.TestCase):
    def test_explicit_zero_alpha_untextured_material_exports_blend(self) -> None:
        xaf = r'''
material "TRANSPARANT" {
 colour { 0, 0, 0, 0 }
 specular { 0, 15 }
}
object "tri" {
 matrix { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 }
 mesh {
  vertices { 0,0,0, 1,0,0, 0,1,0 }
  normals { 0,0,1 }
  texture_coordinates { 0,0, 1,0, 0,1 }
  faces {
   3 0 0 1 0 2 0
  }
  material "TRANSPARANT"
 }
}
'''
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "alpha0.xaf"
            tex = root / "textures"
            tex.mkdir()
            src.write_text(xaf, encoding="latin1")
            scene, objects, primitives, _mats, _resolved, missing = export_xaf_glb_v9.parse(src, tex)
            self.assertEqual(len(objects), 1)
            self.assertEqual(sum(p["triangles"] for p in primitives), 1)
            self.assertEqual(missing, [])
            blob = scene.export(file_type="glb")

        magic, version, total = struct.unpack_from("<4sII", blob, 0)
        self.assertEqual(magic, b"glTF")
        self.assertEqual(version, 2)
        offset = 12
        payload = None
        while offset < total:
            length, chunk_type = struct.unpack_from("<II", blob, offset)
            chunk = blob[offset + 8 : offset + 8 + length]
            if chunk_type == 0x4E4F534A:
                payload = json.loads(chunk.rstrip(b" \x00").decode("utf8"))
                break
            offset += 8 + length
        self.assertIsNotNone(payload)
        materials = payload["materials"]
        self.assertEqual(len(materials), 1)
        self.assertEqual(materials[0]["name"], "TRANSPARANT")
        self.assertEqual(materials[0]["alphaMode"], "BLEND")
        self.assertEqual(materials[0]["pbrMetallicRoughness"]["baseColorFactor"][3], 0.0)


if __name__ == "__main__":
    unittest.main()
