#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/texture_lab"))

from common import (
    alpha_is_binary,
    image_mae,
    prepare_backend_colorkey_input,
    reapply_source_colorkey_mask,
    seam_mae,
    sha256_file,
    visible_legacy_magenta_pixels,
)
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

    def _legacy_key_fixture(self, path: Path) -> None:
        im = Image.new("RGB", (8, 8), (252, 0, 252))
        px = im.load()
        for y in range(2, 6):
            for x in range(2, 6):
                px[x, y] = (48 + x * 10, 32 + y * 8, 20)
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

    def test_legacy_magenta_colorkey_is_alpha_safe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "classic"
            source_dir.mkdir()
            src = source_dir / "SPRITE#.png"
            self._legacy_key_fixture(src)

            manifest = scan(source_dir)
            row = manifest["textures"][0]
            self.assertTrue(row["legacy_colorkey_candidate"])
            self.assertGreater(row["legacy_magenta_pixels"], 0)

            out = root / "enhanced"
            variants = upscale_one(src, out, 4, ["nearest", "bicubic", "lanczos"])
            self.assertEqual(len(variants), 3)
            for variant in variants:
                candidate = out / variant["file"]
                with Image.open(candidate) as im:
                    self.assertEqual(im.mode, "RGBA")
                    self.assertTrue(alpha_is_binary(im))
                    self.assertEqual(visible_legacy_magenta_pixels(im), 0)
                report = validate_pair(src, candidate, 4)
                self.assertEqual(report["technical_status"], "PASS")
                self.assertTrue(report["colorkey_ok"])

    def test_ai_backend_colorkey_input_and_mask_reapply(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "SPRITE#.png"
            prepared = root / "prepared.png"
            output = root / "fake_ai.png"
            self._legacy_key_fixture(src)

            prepared_path, changed = prepare_backend_colorkey_input(src, prepared)
            self.assertTrue(changed)
            self.assertEqual(prepared_path, prepared)
            with Image.open(prepared) as im:
                self.assertEqual(im.mode, "RGBA")
                self.assertTrue(alpha_is_binary(im))
                self.assertEqual(visible_legacy_magenta_pixels(im), 0)

            Image.new("RGB", (32, 32), (80, 120, 160)).save(output)
            reapplied = reapply_source_colorkey_mask(src, output)
            self.assertTrue(reapplied)
            with Image.open(output) as im:
                self.assertEqual(im.mode, "RGBA")
                self.assertTrue(alpha_is_binary(im))
                alpha = im.getchannel("A")
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertEqual(alpha.getpixel((16, 16)), 255)

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
