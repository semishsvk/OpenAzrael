#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/texture_lab"))

from common import (
    alpha_is_binary,
    image_mae,
    prepare_backend_colorkey_input,
    prepare_conditioning_image,
    reapply_source_colorkey_mask,
    seam_mae,
    sha256_file,
    visible_legacy_magenta_pixels,
)
from oa_tex_ai_bakeoff import build_recreate_plan, eligible_entries
from oa_tex_comfy_doctor import EXPECTED_INPUTS, evaluate_object_info
from oa_tex_enhance import upscale_one
from oa_tex_prompt import build_prompt_pair
from oa_tex_qwen_preflight import (
    exact_loader_check,
    inspect_workflow,
    node_binding_check,
    sampling_check,
)
from oa_tex_realesrgan_bootstrap import verify_checkpoint
from oa_tex_scan import scan
from oa_tex_structural_drift import analyze_pair
from oa_tex_tile import tile_preview
from oa_tex_validate import validate_pair


class TextureLabRTPOC01Tests(unittest.TestCase):
    def _fixture(self, path: Path) -> None:
        im = Image.new("RGBA", (16, 16), (20, 40, 60, 255))
        px = im.load()
        for y in range(16):
            for x in range(16):
                px[x, y] = (
                    (x * 31 + y * 7) % 256,
                    (y * 29 + x * 3) % 256,
                    (x * 11 + y * 17) % 256,
                    255 if (x + y) % 3 else 128,
                )
        for y in range(4, 9):
            for x in range(3, 7):
                px[x, y] = (245, 232, 40, 255)
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
            self.assertEqual(result["actual_size"], [64, 64])

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
                self.assertEqual(im.getpixel((0, 0)), (0, 0, 0, 0))
                self.assertEqual(alpha.getpixel((16, 16)), 255)

    def test_enhanced_conditioning_canvas_locks_classic_silhouette(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classic = root / "SPRITE#.png"
            enhanced = root / "enhanced.png"
            prepared = root / "prepared.png"
            self._legacy_key_fixture(classic)

            # Deliberately opaque/high-resolution conditioning image: the helper
            # must impose the Classic silhouette without changing target size.
            Image.new("RGB", (32, 32), (110, 90, 70)).save(enhanced)
            prepared_path, changed = prepare_conditioning_image(classic, enhanced, prepared)
            self.assertTrue(changed)
            self.assertEqual(prepared_path, prepared)

            with Image.open(prepared) as im:
                self.assertEqual(im.size, (32, 32))
                self.assertEqual(im.mode, "RGBA")
                self.assertTrue(alpha_is_binary(im))
                alpha = im.getchannel("A")
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertEqual(alpha.getpixel((16, 16)), 255)
                self.assertEqual(im.getpixel((0, 0)), (0, 0, 0, 0))

    def test_structural_drift_detects_displacement(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source.png"
            good = root / "good.png"
            shifted = root / "shifted.png"
            self._fixture(src)

            with Image.open(src) as im:
                im.resize((64, 64), Image.Resampling.NEAREST).save(good)
                moved = Image.new("RGBA", im.size, (0, 0, 0, 255))
                moved.alpha_composite(im, (3, 0))
                moved.resize((64, 64), Image.Resampling.NEAREST).save(shifted)

            good_metrics = analyze_pair(src, good)
            bad_metrics = analyze_pair(src, shifted)

            self.assertLess(
                good_metrics["low_frequency_luma_mae_0_255"],
                bad_metrics["low_frequency_luma_mae_0_255"],
            )
            self.assertLess(
                good_metrics["edge_map_mae_0_255"],
                bad_metrics["edge_map_mae_0_255"],
            )

    def test_ai_policy_excludes_mask_and_text_recreation(self):
        selection = {
            "textures": [
                {"id": "KEYHOLE#", "content_class": "binary_mask_hard_edge"},
                {"id": "SHIELD1", "content_class": "text_decorative_shield"},
                {"id": "BAPFLOR#", "content_class": "stone_floor"},
            ]
        }
        policy = {
            "defaults": {"ai_restored": True, "ai_recreated": True},
            "classes": {
                "binary_mask_hard_edge": {
                    "ai_restored": False,
                    "ai_recreated": False,
                    "preferred_tier": "enhanced_nearest",
                },
                "text_decorative_shield": {"ai_restored": True, "ai_recreated": False},
                "stone_floor": {"ai_restored": True, "ai_recreated": True},
            },
        }

        restored, restored_skipped = eligible_entries(selection, policy, "restored")
        recreated, recreated_skipped = eligible_entries(selection, policy, "recreated")

        self.assertEqual([row["id"] for row in restored], ["SHIELD1", "BAPFLOR#"])
        self.assertEqual([row["id"] for row in recreated], ["BAPFLOR#"])
        self.assertEqual([row["id"] for row in restored_skipped], ["KEYHOLE#"])
        self.assertEqual(
            [row["id"] for row in recreated_skipped],
            ["KEYHOLE#", "SHIELD1"],
        )

    def test_prompt_pair_keeps_negative_constraints_separate(self):
        profiles = {
            "base": "Preserve composition.",
            "classes": {"stone_floor": "Restore stone microdetail."},
            "negative": "No new objects. No moved edges.",
        }
        pair = build_prompt_pair(profiles, "stone_floor")
        self.assertIn("Preserve composition.", pair["positive"])
        self.assertIn("Restore stone microdetail.", pair["positive"])
        self.assertNotIn("No new objects", pair["positive"])
        self.assertEqual(pair["negative"], "No new objects. No moved edges.")

    def test_canonical_qwen_api_workflow_contract(self):
        workflow_path = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
        contract_path = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        contract = json.loads(contract_path.read_text(encoding="utf-8"))

        inspection = inspect_workflow(workflow, contract)
        loaders = exact_loader_check(inspection, contract)
        sampler = sampling_check(inspection, contract)
        bindings = contract["canonical_openazrael_workflow"]["bindings"]
        binding_checks = node_binding_check(
            workflow,
            str(bindings["load_image_node"]),
            str(bindings["prompt_node"]),
            str(bindings["negative_prompt_node"]),
            str(bindings["seed_node"]),
        )

        self.assertEqual(inspection["missing_required_classes"], [])
        self.assertEqual(len(inspection["load_image_nodes"]), 1)
        self.assertEqual(len(inspection["prompt_nodes"]), 2)
        self.assertEqual(len(inspection["samplers"]), 1)
        self.assertEqual(len(inspection["lora_nodes"]), 0)
        self.assertTrue(all(loaders.values()))
        self.assertEqual(sampler["status"], "PASS")
        self.assertTrue(
            all(row["status"] == "PASS" for row in binding_checks.values())
        )

        positive = workflow[str(bindings["prompt_node"])]["inputs"]
        negative = workflow[str(bindings["negative_prompt_node"])]["inputs"]
        for inputs in [positive, negative]:
            self.assertIn("image1", inputs)
            self.assertNotIn("image2", inputs)
            self.assertNotIn("image3", inputs)

    def test_comfy_doctor_requires_qwen_runtime_nodes_and_inputs(self):
        required = [
            "LoadImage",
            "UNETLoader",
            "CLIPLoader",
            "VAELoader",
            "ModelSamplingAuraFlow",
            "CFGNorm",
            "TextEncodeQwenImageEditPlus",
            "VAEEncode",
            "KSampler",
            "VAEDecode",
            "SaveImage",
        ]
        object_info = {
            cls: {
                "input": {
                    "required": {
                        name: ["TEST"]
                        for name in EXPECTED_INPUTS.get(cls, set())
                    }
                }
            }
            for cls in required
        }

        good = evaluate_object_info(object_info, required)
        self.assertTrue(good["all_required_classes_present"])
        self.assertTrue(good["all_expected_inputs_present"])

        del object_info["CFGNorm"]
        missing_class = evaluate_object_info(object_info, required)
        self.assertFalse(missing_class["all_required_classes_present"])
        self.assertEqual(missing_class["classes"]["CFGNorm"]["status"], "MISSING")

        object_info["CFGNorm"] = {
            "input": {"required": {"model": ["MODEL"]}}
        }
        missing_input = evaluate_object_info(object_info, required)
        self.assertFalse(missing_input["all_expected_inputs_present"])
        self.assertIn("strength", missing_input["classes"]["CFGNorm"]["missing_inputs"])

    def test_recreated_plan_gates_runtime_and_uses_enhanced_conditioning(self):
        contract = json.loads(
            (ROOT / "tools/texture_lab/config/qwen_2511_contract.json").read_text(encoding="utf-8")
        )
        profiles = json.loads(
            (ROOT / "tools/texture_lab/profiles/recreate_profiles.json").read_text(encoding="utf-8")
        )
        entry = {
            "id": "CORIROCK",
            "content_class": "rock_organic_surface",
            "policy": {"ai_recreated": True},
        }
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            args = SimpleNamespace(
                workflow=ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json",
                server="http://127.0.0.1:8188",
                run_dir=temp / "run",
                comfy_root=None,
                model_file=[],
                source_dir=temp / "classic",
                recreated_dir=temp / "recreated",
                recreate_input_dir=temp / "enhanced",
                recreate_input_variant="lanczos_x4.png",
                load_image_node="1",
                prompt_node="7",
                prompt_key="prompt",
                negative_prompt_node="8",
                negative_prompt_key="prompt",
                seed_node="10",
                seed_key="seed",
                seed=734234,
                model_label="Qwen-Image-Edit-2511",
                selection=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
            )
            jobs = build_recreate_plan(args, [entry], profiles, contract)

        self.assertEqual(
            [job["stage"] for job in jobs],
            ["comfy_doctor", "qwen_preflight", "generate", "structural_qa"],
        )
        generate = jobs[2]
        self.assertTrue(generate["conditioning_image"].endswith("CORIROCK/lanczos_x4.png"))
        self.assertIn("--negative-prompt-node", generate["argv"])
        self.assertIn("8", generate["argv"])
        self.assertIn("--conditioning-image", generate["argv"])

    def test_checkpoint_identity_verification(self):
        with tempfile.TemporaryDirectory() as td:
            checkpoint = Path(td) / "model.pth"
            payload = b"openazrael-test-checkpoint"
            checkpoint.write_bytes(payload)
            spec = {
                "checkpoint_size_bytes": len(payload),
                "checkpoint_sha256": hashlib.sha256(payload).hexdigest(),
            }

            good = verify_checkpoint(checkpoint, spec)
            self.assertEqual(good["status"], "PASS")
            self.assertTrue(good["size_ok"])
            self.assertTrue(good["sha256_ok"])

            checkpoint.write_bytes(payload + b"-corrupted")
            bad = verify_checkpoint(checkpoint, spec)
            self.assertEqual(bad["status"], "FAIL")
            self.assertFalse(bad["size_ok"])
            self.assertFalse(bad["sha256_ok"])

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
                self.assertEqual(im.size, (48, 64))


if __name__ == "__main__":
    unittest.main()
