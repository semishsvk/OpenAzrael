#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/texture_lab"))

from common import image_mae, seam_mae, sha256_file
from oa_tex_enhance import upscale_one
from oa_tex_scan import scan
from oa_tex_tile import tile_preview
from oa_tex_validate import validate_pair


class TextureLabRTPOC01Tests(unittest.TestCase):
    def _fixture(self, path: Path) -> None:
        im = Image.new("RGBA", (8, 8), (20, 40, 60, 255))
        px = im.load()
        for y in range(8):
            for x in range(8):
                px[x, y] = (
                    (x * 31 + y * 7) % 256,
                    (y * 29 + x * 3) % 256,
                    (x * 11 + y * 17) % 256,
                    255 if (x + y) % 3 else 128,
                )
        im.save(path)

    def test_scan_and_deterministic_upscale(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "classic"
            source_dir.mkdir()
            src = source_dir / "TEX_TEST.png"
            self._fixture(src)

            manifest = scan(source_dir)
            self.assertEqual(manifest["texture_count"], 1)
            self.assertTrue(manifest["textures"][0]["has_alpha"])

            out_a = root / "run_a"
            out_b = root / "run_b"
            variants_a = upscale_one(src, out_a, 4, ["nearest", "bicubic", "lanczos"])
            variants_b = upscale_one(src, out_b, 4, ["nearest", "bicubic", "lanczos"])
            self.assertEqual(len(variants_a), 3)
            self.assertEqual(
                [sha256_file(out_a / v["file"]) for v in variants_a],
                [sha256_file(out_b / v["file"]) for v in variants_b],
            )

            nearest = out_a / "nearest_x4.png"
            result = validate_pair(src, nearest, 4)
            self.assertEqual(result["technical_status"], "PASS")
            self.assertEqual(result["actual_size"], [32, 32])

    def test_metrics_are_stable(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.png"
            self._fixture(src)
            with Image.open(src) as im:
                copy = im.copy()
                self.assertEqual(image_mae(im, copy), 0.0)
                seams = seam_mae(im)
                self.assertIn("x", seams)
                self.assertIn("y", seams)

    def test_tile_preview_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "tile.png"
            dest = root / "tile_preview.png"
            self._fixture(src)
            tile_preview(src, dest, 3, 4)
            with Image.open(dest) as im:
                self.assertEqual(im.size, (24, 32))


if __name__ == "__main__":
    unittest.main()
