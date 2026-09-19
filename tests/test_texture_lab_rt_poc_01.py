#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/texture_lab"))

from common import (
    PILLOW_VERSION,
    PINNED_PILLOW_VERSION,
    alpha_is_binary,
    image_mae,
    named_candidate_root,
    prepare_backend_colorkey_input,
    prepare_conditioning_image,
    reapply_source_colorkey_mask,
    seam_mae,
    sha256_file,
    visible_legacy_magenta_pixels,
)
from oa_tex_ai_bakeoff import (
    DEFAULT_RECREATED_DIR,
    DEFAULT_RESTORED_DIR,
    apply_execution_subset,
    build_recreate_plan,
    build_restore_plan,
    eligible_entries,
    prepare_run_storage,
    resolve_named_candidate_namespace,
    run_instance_id,
    validate_named_preset_contract,
)
from oa_tex_atlas import split_equal, stitch_equal
from oa_tex_comfy_doctor import EXPECTED_INPUTS, evaluate_object_info
from oa_tex_compare import _fit_preview
from oa_tex_contract_validate import validate_contracts
from oa_tex_enhance import upscale_one
from oa_tex_first_run import (
    baseline_plan,
    bootstrap_plan,
    classify_restored_smoke_1_state,
    classify_recreated_smoke_1_state,
    poc_source_status,
    recreated_smoke_check_plan,
    recreated_smoke_plan,
    restored_smoke_check_plan,
    restored_smoke_plan,
    runtime_paths,
)
from oa_tex_manual_review import init_review, record_texture, validate_manual_review
from oa_tex_prompt import build_prompt_pair
from oa_tex_production_selection import (
    CURRENT_RECORD_SCHEMA,
    CURRENT_REGISTRY_SCHEMA,
    LEGACY_REGISTRY_SCHEMA,
    load_registry,
    registry_status,
    select_candidate,
    store_selection_record,
)
from oa_tex_qwen_bootstrap import build_plan as build_qwen_bootstrap_plan, verify_model as verify_qwen_bootstrap_model
from oa_tex_qwen_preflight import (
    exact_loader_check,
    inspect_workflow,
    node_binding_check,
    sampling_check,
)
from oa_tex_realesrgan_bootstrap import dependency_install_commands, verify_checkpoint
from oa_tex_realesrgan_runtime import evaluate_probe, load_contract as load_realesrgan_runtime_contract
from oa_tex_realesrgan_lock import build_lock_candidate, requirements_text
from oa_tex_realesrgan_lock_plan import (
    build_promotion_plan,
    candidate_compatibility,
    write_plan_artifacts,
)
from oa_tex_stage_gate import (
    approve,
    check_prerequisites,
    _qwen_job_checks,
    evidence_snapshot,
    expected_recreated_job_records,
    preset_record,
    restored_generation_provenance,
    valid_run_instance_id,
    validate_receipt,
)
from oa_tex_review_report import build_review_rows
from oa_tex_review_pack import build_review_pack
from oa_tex_review_handoff import build_handoff
from oa_tex_review_profile import build_review_profile
from oa_tex_run_summary import build_summary, restored_performance_summary
from oa_tex_runtime_export import compile_export
from oa_tex_runtime_manifest import build_manifest, input_file_record
from oa_tex_runtime_verify import verify_manifest
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
                factor=4,
            )
            jobs = build_recreate_plan(args, [entry], profiles, contract)

        self.assertEqual(
            [job["stage"] for job in jobs],
            ["comfy_doctor", "qwen_preflight", "generate", "technical_qa", "structural_qa", "review_queue", "review_pack"],
        )
        generate = jobs[2]
        self.assertTrue(generate["conditioning_image"].endswith("CORIROCK/lanczos_x4.png"))
        self.assertIn("--negative-prompt-node", generate["argv"])
        self.assertIn("8", generate["argv"])
        self.assertIn("--conditioning-image", generate["argv"])

    def test_smoke_presets_select_staged_subset(self):
        allowed = [
            {"id": "CORIROCK", "content_class": "rock_organic_surface"},
            {"id": "ECRDOR01", "content_class": "architectural_doorway"},
            {"id": "WEL_PUZ1", "content_class": "mechanical_puzzle"},
            {"id": "BAPFLOR#", "content_class": "stone_floor"},
            {"id": "BAPTAP", "content_class": "high_detail_mural"},
        ]
        selected, deferred, preset = apply_execution_subset(
            "recreated", allowed, "recreated_smoke_4", None
        )
        self.assertEqual(
            [entry["id"] for entry in selected],
            ["CORIROCK", "ECRDOR01", "WEL_PUZ1", "BAPFLOR#"],
        )
        self.assertEqual([entry["id"] for entry in deferred], ["BAPTAP"])
        self.assertEqual(preset["name"], "recreated_smoke_4")

    def test_real_named_runs_get_unique_approval_identity(self):
        self.assertIsNone(run_instance_id(None, False))
        self.assertIsNone(run_instance_id("restored_smoke_1", True))

        first = run_instance_id("restored_smoke_1", False)
        second = run_instance_id("restored_smoke_1", False)
        self.assertTrue(valid_run_instance_id(first))
        self.assertTrue(valid_run_instance_id(second))
        self.assertNotEqual(first, second)

    def test_named_run_storage_refuses_stale_mix_and_replaces_explicitly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            candidate_dir = root / "candidate"

            clean = prepare_run_storage(
                run_dir,
                candidate_dir,
                replace_existing=False,
                dry_run=False,
            )
            self.assertEqual(clean["status"], "CLEAN")
            self.assertFalse(clean["replaced_existing"])

            run_dir.mkdir()
            candidate_dir.mkdir()
            (run_dir / "old_report.json").write_text("{}", encoding="utf-8")
            (candidate_dir / "old.png").write_bytes(b"old")

            with self.assertRaises(SystemExit):
                prepare_run_storage(
                    run_dir,
                    candidate_dir,
                    replace_existing=False,
                    dry_run=False,
                )
            self.assertTrue((run_dir / "old_report.json").is_file())
            self.assertTrue((candidate_dir / "old.png").is_file())

            dry = prepare_run_storage(
                run_dir,
                candidate_dir,
                replace_existing=False,
                dry_run=True,
            )
            self.assertEqual(dry["status"], "DRY_RUN_NO_MUTATION")
            self.assertTrue((run_dir / "old_report.json").is_file())

            with self.assertRaises(SystemExit):
                prepare_run_storage(
                    run_dir,
                    candidate_dir,
                    replace_existing=True,
                    dry_run=True,
                )

            replaced = prepare_run_storage(
                run_dir,
                candidate_dir,
                replace_existing=True,
                dry_run=False,
            )
            self.assertTrue(replaced["replaced_existing"])
            self.assertFalse(run_dir.exists())
            self.assertFalse(candidate_dir.exists())

    def test_named_presets_use_preset_scoped_candidate_namespaces(self):
        restored = SimpleNamespace(
            preset="restored_smoke_1",
            mode="restored",
            restored_dir=DEFAULT_RESTORED_DIR,
            recreated_dir=DEFAULT_RECREATED_DIR,
        )
        resolve_named_candidate_namespace(restored)
        self.assertEqual(
            restored.restored_dir,
            DEFAULT_RESTORED_DIR / "_runs" / "restored_smoke_1",
        )

        recreated = SimpleNamespace(
            preset="recreated_smoke_4",
            mode="recreated",
            restored_dir=DEFAULT_RESTORED_DIR,
            recreated_dir=DEFAULT_RECREATED_DIR,
        )
        resolve_named_candidate_namespace(recreated)
        self.assertEqual(
            recreated.recreated_dir,
            DEFAULT_RECREATED_DIR / "_runs" / "recreated_smoke_4",
        )

        custom = SimpleNamespace(
            preset="restored_smoke_1",
            mode="restored",
            restored_dir=ROOT / "elsewhere",
            recreated_dir=DEFAULT_RECREATED_DIR,
        )
        with self.assertRaises(SystemExit):
            resolve_named_candidate_namespace(custom)

        adhoc = SimpleNamespace(
            preset=None,
            mode="restored",
            restored_dir=DEFAULT_RESTORED_DIR,
            recreated_dir=DEFAULT_RECREATED_DIR,
        )
        resolve_named_candidate_namespace(adhoc)
        self.assertEqual(adhoc.restored_dir, DEFAULT_RESTORED_DIR)

    def test_named_restored_preset_parameters_are_canonical(self):
        backends = json.loads(
            (ROOT / "tools/texture_lab/config/ai_backends.json").read_text(
                encoding="utf-8"
            )
        )
        qwen = json.loads(
            (ROOT / "tools/texture_lab/config/qwen_2511_contract.json").read_text(
                encoding="utf-8"
            )
        )
        args = SimpleNamespace(
            preset="restored_smoke_1",
            mode="restored",
            selection=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
            policy=ROOT / "tools/texture_lab/config/ai_review_policy.json",
            profiles=ROOT / "tools/texture_lab/profiles/recreate_profiles.json",
            source_dir=ROOT / "assets/textures/classic",
            only=None,
            model_file=[],
            restore_model="RealESRGAN_x4plus",
            factor=4,
            tile=0,
            fp32=True,
            denoise_strength=None,
        )
        validate_named_preset_contract(args, qwen, backends)

        for field, value in [
            ("factor", 2),
            ("tile", 128),
            ("fp32", False),
            ("restore_model", "other"),
            ("denoise_strength", 0.5),
            ("selection", ROOT / "wrong_selection.json"),
            ("policy", ROOT / "wrong_policy.json"),
            ("profiles", ROOT / "wrong_profiles.json"),
            ("source_dir", ROOT / "wrong_source"),
            ("only", ["CORIROCK"]),
            ("model_file", [ROOT / "extra_model.bin"]),
        ]:
            bad = SimpleNamespace(**vars(args))
            setattr(bad, field, value)
            with self.assertRaises(SystemExit):
                validate_named_preset_contract(bad, qwen, backends)

    def test_named_recreated_preset_parameters_are_canonical(self):
        backends = json.loads(
            (ROOT / "tools/texture_lab/config/ai_backends.json").read_text(
                encoding="utf-8"
            )
        )
        qwen = json.loads(
            (ROOT / "tools/texture_lab/config/qwen_2511_contract.json").read_text(
                encoding="utf-8"
            )
        )
        bindings = qwen["canonical_openazrael_workflow"]["bindings"]
        args = SimpleNamespace(
            preset="recreated_smoke_1",
            mode="recreated",
            selection=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
            policy=ROOT / "tools/texture_lab/config/ai_review_policy.json",
            profiles=ROOT / "tools/texture_lab/profiles/recreate_profiles.json",
            source_dir=ROOT / "assets/textures/classic",
            recreate_input_dir=ROOT / "assets/textures/enhanced",
            only=None,
            model_file=[],
            workflow=ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json",
            model_label="Qwen-Image-Edit-2511",
            seed=734234,
            factor=4,
            recreate_input_variant="lanczos_x4.png",
            load_image_node=str(bindings["load_image_node"]),
            prompt_node=str(bindings["prompt_node"]),
            negative_prompt_node=str(bindings["negative_prompt_node"]),
            seed_node=str(bindings["seed_node"]),
            prompt_key="prompt",
            negative_prompt_key="prompt",
            seed_key="seed",
        )
        validate_named_preset_contract(args, qwen, backends)

        mutations = [
            ("workflow", ROOT / "wrong_workflow.json"),
            ("model_label", "other"),
            ("seed", 1),
            ("factor", 2),
            ("recreate_input_variant", "nearest_x4.png"),
            ("load_image_node", "999"),
            ("prompt_node", "999"),
            ("negative_prompt_node", "999"),
            ("seed_node", "999"),
            ("prompt_key", "text"),
            ("negative_prompt_key", "text"),
            ("seed_key", "noise_seed"),
            ("selection", ROOT / "wrong_selection.json"),
            ("policy", ROOT / "wrong_policy.json"),
            ("profiles", ROOT / "wrong_profiles.json"),
            ("source_dir", ROOT / "wrong_source"),
            ("recreate_input_dir", ROOT / "wrong_enhanced"),
            ("only", ["CORIROCK"]),
            ("model_file", [ROOT / "extra_model.bin"]),
        ]
        for field, value in mutations:
            bad = SimpleNamespace(**vars(args))
            setattr(bad, field, value)
            with self.assertRaises(SystemExit):
                validate_named_preset_contract(bad, qwen, backends)

    def test_restored_plan_starts_with_runtime_doctor(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            args = SimpleNamespace(
                run_dir=temp / "run",
                source_dir=temp / "classic",
                restored_dir=temp / "restored",
                factor=4,
                restore_model="RealESRGAN_x4plus",
                tile=0,
                fp32=True,
                denoise_strength=None,
                realesrgan_root=temp / "Real-ESRGAN",
                model_path=temp / "RealESRGAN_x4plus.pth",
                realesrgan_python=str(temp / "venv" / "bin" / "python"),
                selection=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
            )
            jobs = build_restore_plan(
                args,
                [{"id": "CORIROCK", "content_class": "rock_organic_surface"}],
            )

        self.assertEqual(
            [job["stage"] for job in jobs],
            ["realesrgan_doctor", "generate", "technical_qa", "structural_qa", "review_queue", "review_pack"],
        )
        self.assertEqual(jobs[0]["argv"][0], str(temp / "venv" / "bin" / "python"))
        self.assertIn("--realesrgan-root", jobs[0]["argv"])
        self.assertIn("--model-path", jobs[0]["argv"])
        self.assertIn("--python-exe", jobs[1]["argv"])
        self.assertIn(str(temp / "venv" / "bin" / "python"), jobs[1]["argv"])

    def test_recreated_stage_gate_has_exact_generation_record_contract(self):
        with tempfile.TemporaryDirectory() as td:
            run_root = Path(td)

            smoke4 = expected_recreated_job_records(
                "recreated_smoke_4",
                run_root / "recreated_smoke_4",
            )
            self.assertEqual(len(smoke4), 4)
            self.assertEqual(
                sorted(path.name for path in smoke4),
                [
                    "BAPFLOR_.job.json",
                    "CORIROCK.job.json",
                    "ECRDOR01.job.json",
                    "WEL_PUZ1.job.json",
                ],
            )

            atlas = expected_recreated_job_records(
                "recreated_atlas",
                run_root / "recreated_atlas",
            )
            self.assertEqual(len(atlas), 7)
            self.assertEqual(
                sorted(path.name for path in atlas),
                [
                    "BAPTAP_part_00.job.json",
                    "BAPTAP_part_01.job.json",
                    "BAPTAP_part_02.job.json",
                    "BAPTAP_part_03.job.json",
                    "classic_split.json",
                    "enhanced_split.json",
                    "stitch.json",
                ],
            )

            full = expected_recreated_job_records(
                "recreated_full",
                run_root / "recreated_full",
            )
            self.assertEqual(len(full), 16)
            self.assertEqual(
                len([path for path in full if path.suffix == ".json"]),
                16,
            )

    def test_stage_gate_requires_manual_receipt_after_first_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_root = root / "runs"
            approval_root = root / "approvals"

            first = check_prerequisites(
                "restored_smoke_1", run_root, approval_root
            )
            second = check_prerequisites(
                "restored_smoke_4", run_root, approval_root
            )
            recreated_first = check_prerequisites(
                "recreated_smoke_1", run_root, approval_root
            )
            recreated_full = check_prerequisites(
                "recreated_full", run_root, approval_root
            )

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["requires_approval"], [])
        self.assertEqual(second["status"], "HOLD")
        self.assertEqual(second["requires_approval"], ["restored_smoke_1"])
        self.assertEqual(recreated_first["status"], "PASS")
        self.assertEqual(recreated_full["status"], "HOLD")
        self.assertEqual(
            recreated_full["requires_approval"],
            ["recreated_smoke_4", "recreated_atlas"],
        )

    def test_atlas_split_stitch_is_pixel_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "atlas.png"
            parts = root / "parts"
            stitched = root / "stitched.png"

            im = Image.new("RGBA", (16, 8), (0, 0, 0, 255))
            px = im.load()
            for y in range(im.height):
                for x in range(im.width):
                    px[x, y] = (
                        (x * 17) % 256,
                        (y * 31) % 256,
                        (x * 9 + y * 5) % 256,
                        255,
                    )
            im.save(source)

            rows = split_equal(source, parts, "x", 4)
            self.assertEqual(len(rows), 4)
            self.assertEqual([row["size"] for row in rows], [[4, 8]] * 4)

            result = stitch_equal(parts, stitched, "x", 4)
            self.assertEqual(result["size"], [16, 8])
            with Image.open(source) as original, Image.open(stitched) as rebuilt:
                self.assertEqual(
                    list(original.convert("RGBA").getdata()),
                    list(rebuilt.convert("RGBA").getdata()),
                )

    def test_baptap_plan_generates_four_isolated_qwen_parts(self):
        contract = json.loads(
            (ROOT / "tools/texture_lab/config/qwen_2511_contract.json").read_text(encoding="utf-8")
        )
        profiles = json.loads(
            (ROOT / "tools/texture_lab/profiles/recreate_profiles.json").read_text(encoding="utf-8")
        )
        entry = {
            "id": "BAPTAP",
            "content_class": "high_detail_mural",
            "policy": {
                "ai_recreated": True,
                "atlas_split": {"axis": "x", "segments": 4},
            },
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
                factor=4,
            )
            jobs = build_recreate_plan(args, [entry], profiles, contract)

        stages = [job["stage"] for job in jobs]
        self.assertEqual(stages[0:2], ["comfy_doctor", "qwen_preflight"])
        self.assertEqual(stages.count("atlas_split_classic"), 1)
        self.assertEqual(stages.count("atlas_split_enhanced"), 1)
        self.assertEqual(stages.count("generate"), 4)
        self.assertEqual(stages.count("atlas_stitch"), 1)
        self.assertEqual(
            stages[-4:],
            ["technical_qa", "structural_qa", "review_queue", "review_pack"],
        )
        generated_parts = [job for job in jobs if job["stage"] == "generate"]
        self.assertEqual(
            [job["part"] for job in generated_parts],
            ["00", "01", "02", "03"],
        )

    def test_review_queue_flags_drift_without_auto_rejection(self):
        selection = {
            "textures": [
                {
                    "id": "BAPFLOR#",
                    "room": "R8",
                    "content_class": "stone_floor",
                }
            ]
        }
        policy = {
            "defaults": {"ai_recreated": True},
            "classes": {
                "stone_floor": {
                    "ai_recreated": True,
                    "exact_alpha_lock": True,
                    "seam_review": "u_and_v_required",
                }
            },
        }
        sampling = {
            "textures": [
                {
                    "id": "BAPFLOR#",
                    "sampling_class": "repeat_sampling_observed",
                    "repeat_sampling_observed": True,
                    "repeat_axes": ["u", "v"],
                    "seam_review": "u_and_v_required_before_production",
                }
            ]
        }
        baseline = {
            "global_envelope": {
                "low_frequency_luma_mae_0_255": {
                    "p95": 0.25,
                    "max": 0.40,
                }
            }
        }
        drift = {
            "results": [
                {
                    "id": "BAPFLOR#",
                    "low_frequency_luma_mae_0_255": 0.80,
                    "alpha_silhouette_mismatch_fraction": 0.0,
                }
            ]
        }

        rows = build_review_rows(
            "recreated", selection, policy, sampling, baseline, drift
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["review_state"], "MANUAL_REVIEW_REQUIRED")
        self.assertEqual(row["ratio_to_deterministic_p95"], 3.2)
        self.assertIn("drift_above_deterministic_max", row["attention"])
        self.assertIn("exact_alpha_lock", row["attention"])
        self.assertIn("repeat_sampling:u,v", row["attention"])

    def test_visual_review_pack_fingerprints_comparison_and_repeat_tile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "classic"
            enhanced_dir = root / "enhanced"
            restored_dir = root / "restored"
            recreated_dir = root / "recreated"
            out_dir = root / "review_pack"
            source_dir.mkdir()

            texture_id = "TEX_REPEAT"
            source = source_dir / f"{texture_id}.png"
            self._fixture(source)

            with Image.open(source) as im:
                enlarged = im.convert("RGBA").resize(
                    (im.width * 4, im.height * 4),
                    getattr(Image, "Resampling", Image).NEAREST,
                )

            variant_dir = enhanced_dir / texture_id
            variant_dir.mkdir(parents=True)
            for name in ["nearest_x4.png", "bicubic_x4.png", "lanczos_x4.png"]:
                enlarged.save(variant_dir / name)

            candidate_dir = recreated_dir / texture_id
            candidate_dir.mkdir(parents=True)
            candidate = candidate_dir / "selected.png"
            enlarged.save(candidate)

            review_queue = {
                "rows": [
                    {
                        "id": texture_id,
                        "review_state": "MANUAL_REVIEW_REQUIRED",
                        "attention": ["repeat_sampling:u,v"],
                    }
                ]
            }
            sampling = {
                "textures": [
                    {
                        "id": texture_id,
                        "repeat_sampling_observed": True,
                        "repeat_axes": ["u", "v"],
                    }
                ]
            }

            pack = build_review_pack(
                "recreated",
                review_queue,
                sampling,
                source_dir,
                enhanced_dir,
                restored_dir,
                recreated_dir,
                out_dir,
                96,
            )

            self.assertEqual(pack["status"], "READY_FOR_MANUAL_REVIEW")
            self.assertEqual(pack["texture_count"], 1)
            row = pack["rows"][0]
            comparison = Path(row["comparison"]["path"])
            detail = Path(row["detail_comparison"]["path"])
            tile = Path(row["tile_preview"]["path"])
            self.assertTrue(comparison.is_file())
            self.assertTrue(detail.is_file())
            self.assertTrue(tile.is_file())
            self.assertEqual(row["comparison"]["sha256"], sha256_file(comparison))
            self.assertEqual(row["detail_comparison"]["sha256"], sha256_file(detail))
            self.assertEqual(row["tile_preview"]["sha256"], sha256_file(tile))
            self.assertEqual(row["repeat_axes"], ["u", "v"])

    def test_restored_generation_provenance_matches_reviewed_hashes(self):
        pack = {
            "rows": [
                {
                    "id": "CORIROCK",
                    "source": {"sha256": "a" * 64},
                    "candidate": {"sha256": "b" * 64},
                }
            ]
        }
        run = {
            "schema": "openazrael.texture_lab.ai_restore_run.v5",
            "mode": "ai_restored",
            "reproducibility": {
                "runtime_identity": {"status": "PASS"},
            },
            "performance": {
                "texture_count": 1,
                "run_wall_seconds": 1.0,
                "measured_inference_wall_seconds": 0.8,
                "mean_inference_wall_seconds_per_texture": 0.8,
                "textures_per_minute_inference_only": 75.0,
            },
            "textures": [
                {
                    "id": "CORIROCK",
                    "source_sha256": "a" * 64,
                    "output_sha256": "b" * 64,
                    "model": "RealESRGAN_x4plus",
                    "factor": 4,
                    "backend": "realesrgan-python",
                }
            ],
        }
        good = restored_generation_provenance(
            run,
            pack,
            ["CORIROCK"],
        )
        self.assertEqual(good["status"], "PASS")

        bad = json.loads(json.dumps(run))
        bad["textures"][0]["output_sha256"] = "c" * 64
        result = restored_generation_provenance(
            bad,
            pack,
            ["CORIROCK"],
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(
            result["rows"][0]["checks"]["output_hash_matches_review"]
        )

    def test_qwen_job_provenance_matches_pinned_contract(self):
        contract = json.loads(
            (ROOT / "tools/texture_lab/config/qwen_2511_contract.json").read_text(
                encoding="utf-8"
            )
        )
        workflow = (
            ROOT
            / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
        )
        model_files = [
            {
                "file": spec["filename"],
                "sha256": spec["sha256"],
                "size": spec["size_bytes"],
            }
            for spec in contract["required_models"].values()
        ]
        submitted = json.loads(workflow.read_text(encoding="utf-8"))
        bindings = contract["canonical_openazrael_workflow"]["bindings"]
        submitted[str(bindings["load_image_node"])]["inputs"]["image"] = (
            "uploaded.png"
        )
        submitted[str(bindings["prompt_node"])]["inputs"]["prompt"] = (
            "POSITIVE"
        )
        submitted[str(bindings["negative_prompt_node"])]["inputs"]["prompt"] = (
            "NEGATIVE"
        )
        submitted[str(bindings["seed_node"])]["inputs"]["seed"] = (
            contract["poc_sampling"]["seed"]
        )

        job = {
            "schema": "openazrael.texture_lab.ai_recreated_job.v5",
            "source_sha256": "a" * 64,
            "conditioning_image_sha256": "b" * 64,
            "output_sha256": "c" * 64,
            "workflow_template_sha256": sha256_file(workflow),
            "model_label": contract["model_label"],
            "seed": contract["poc_sampling"]["seed"],
            "positive_prompt": "POSITIVE",
            "negative_prompt": "NEGATIVE",
            "uploaded_name": "uploaded.png",
            "submitted_workflow": submitted,
            "performance": {
                "job_wall_seconds": 10.0,
                "upload_wall_seconds": 0.2,
                "submit_wall_seconds": 0.1,
                "submit_to_completion_wall_seconds": 9.5,
                "download_wall_seconds": 0.2,
            },
            "model_files": model_files,
        }
        checks = _qwen_job_checks(
            job,
            "a" * 64,
            "b" * 64,
            "c" * 64,
            contract,
            sha256_file(workflow),
            "POSITIVE",
            "NEGATIVE",
        )
        self.assertTrue(all(checks.values()))

        bad = json.loads(json.dumps(job))
        bad["seed"] = 1
        bad["output_sha256"] = "d" * 64
        bad["positive_prompt"] = "WRONG"
        bad["performance"]["job_wall_seconds"] = -1.0
        checks = _qwen_job_checks(
            bad,
            "a" * 64,
            "b" * 64,
            "c" * 64,
            contract,
            sha256_file(workflow),
            "POSITIVE",
            "NEGATIVE",
        )
        self.assertFalse(checks["seed_ok"])
        self.assertFalse(checks["output_hash_ok"])
        self.assertFalse(checks["positive_prompt_ok"])
        self.assertFalse(checks["performance_ok"])

    def test_restored_runtime_summary_projects_stage_cost_observationally(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            report = {
                "schema": "openazrael.texture_lab.ai_restore_run.v5",
                "performance": {
                    "texture_count": 1,
                    "run_wall_seconds": 2.0,
                    "measured_inference_wall_seconds": 1.5,
                    "mean_inference_wall_seconds_per_texture": 1.5,
                    "textures_per_minute_inference_only": 40.0,
                },
            }
            (run_dir / "ai_restore_run.json").write_text(
                json.dumps(report),
                encoding="utf-8",
            )
            summary = restored_performance_summary(run_dir)
            self.assertEqual(
                summary["status"],
                "OBSERVED_WITH_LINEAR_ESTIMATE",
            )
            self.assertIn(
                "naive linear inference-only projection",
                summary["estimate_scope"],
            )
            smoke4_count = len(
                preset_record("restored_smoke_4")["textures"]
            )
            full_count = len(
                preset_record("restored_full")["textures"]
            )
            self.assertEqual(
                summary["estimates"]["restored_smoke_4"]["texture_count"],
                smoke4_count,
            )
            self.assertAlmostEqual(
                summary["estimates"]["restored_smoke_4"][
                    "linear_inference_only_seconds"
                ],
                1.5 * smoke4_count,
            )
            self.assertEqual(
                summary["estimates"]["restored_full"]["texture_count"],
                full_count,
            )
            self.assertAlmostEqual(
                summary["estimates"]["restored_full"][
                    "linear_inference_only_seconds"
                ],
                1.5 * full_count,
            )

    def test_restored_stage_approval_is_bound_to_reviewed_candidate(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            root = Path(td)
            run_root = root / "runs"
            approval_root = root / "approvals"
            manual_review_root = root / "manual_reviews"
            run_dir = run_root / "restored_smoke_1"
            run_dir.mkdir(parents=True)

            source_test_root = (
                ROOT / "assets/textures/classic/_unit_test_review"
            )
            source = source_test_root / "CORIROCK.png"
            source.parent.mkdir(parents=True, exist_ok=True)
            self.addCleanup(shutil.rmtree, source_test_root, True)
            candidate_test_root = (
                named_candidate_root("restored", "restored_smoke_1")
                / "_unit_test_candidate"
            )
            candidate = candidate_test_root / "CORIROCK" / "realesrgan_x4.png"
            candidate.parent.mkdir(parents=True, exist_ok=True)
            self.addCleanup(shutil.rmtree, candidate_test_root, True)
            review_pack_root = run_dir / "review_pack"
            comparison = review_pack_root / "comparisons/CORIROCK.png"
            detail = review_pack_root / "details/CORIROCK.png"
            comparison.parent.mkdir(parents=True, exist_ok=True)
            detail.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"classic")
            candidate.write_bytes(b"candidate-v1")
            comparison.write_bytes(b"comparison-v1")
            detail.write_bytes(b"detail-v1")

            def record(path: Path) -> dict:
                return {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }

            (run_dir / "restored_plan.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.ai_bakeoff_plan.v5",
                        "preset": {"name": "restored_smoke_1"},
                        "dry_run": False,
                        "run_instance_id": run_instance_id(
                            "restored_smoke_1",
                            False,
                        ),
                        "selected": ["CORIROCK"],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "ai_restored_review_queue.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.ai_review_queue.v1",
                        "status": "OBSERVATIONAL_MANUAL_REVIEW",
                        "mode": "restored",
                        "automatic_promotion": False,
                        "only": ["CORIROCK"],
                        "rows": [
                            {
                                "id": "CORIROCK",
                                "review_state": "MANUAL_REVIEW_REQUIRED",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "ai_restored_validation.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.validation.v5",
                        "variant": "realesrgan_x4.png",
                        "factor": 4,
                        "only": ["CORIROCK"],
                        "technical_failures": 0,
                        "results": [
                            {
                                "id": "CORIROCK",
                                "source_sha256": sha256_file(source),
                                "candidate_sha256": sha256_file(candidate),
                                "technical_status": "PASS",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "ai_restored_structural_drift.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.structural_drift.v2",
                        "status": "OBSERVATIONAL_UNCALIBRATED",
                        "variant": "realesrgan_x4.png",
                        "only": ["CORIROCK"],
                        "missing": [],
                        "results": [
                            {
                                "id": "CORIROCK",
                                "source_sha256": sha256_file(source),
                                "candidate_sha256": sha256_file(candidate),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "local_preflight.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.local_preflight.v2",
                        "preset": "restored_smoke_1",
                        "mode": "restored",
                        "textures": ["CORIROCK"],
                        "blocking_checks": [],
                        "ready_for_runtime_doctors": True,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "stage_gate.json").write_text(
                json.dumps(
                    {
                        "preset": "restored_smoke_1",
                        "requires_approval": [],
                        "receipts": [],
                        "status": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "realesrgan_doctor.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.realesrgan_doctor.v3",
                        "ready": True,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "ai_restore_run.json").write_text(
                json.dumps(
                    {
                        "schema": "openazrael.texture_lab.ai_restore_run.v5",
                        "mode": "ai_restored",
                        "reproducibility": {
                            "runtime_identity": {"status": "PASS"}
                        },
                        "performance": {
                            "texture_count": 1,
                            "run_wall_seconds": 1.0,
                            "measured_inference_wall_seconds": 0.8,
                            "mean_inference_wall_seconds_per_texture": 0.8,
                            "textures_per_minute_inference_only": 75.0
                        },
                        "textures": [
                            {
                                "id": "CORIROCK",
                                "source_sha256": sha256_file(source),
                                "output_sha256": sha256_file(candidate),
                                "model": "RealESRGAN_x4plus",
                                "factor": 4,
                                "backend": "realesrgan-python",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            review_manifest = run_dir / "ai_restored_review_pack.json"
            review_md = run_dir / "ai_restored_review_pack.md"
            review_md.write_text("# review", encoding="utf-8")

            def write_review_manifest() -> None:
                review_manifest.write_text(
                    json.dumps(
                        {
                            "schema": "openazrael.texture_lab.visual_review_pack.v2",
                            "status": "READY_FOR_MANUAL_REVIEW",
                            "mode": "restored",
                            "texture_count": 1,
                            "automatic_promotion": False,
                            "rows": [
                                {
                                    "id": "CORIROCK",
                                    "source": record(source),
                                    "candidate": record(candidate),
                                    "comparison": record(comparison),
                                    "detail_comparison": record(detail),
                                    "tile_preview": None,
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

            write_review_manifest()

            snapshot = evidence_snapshot("restored_smoke_1", run_root)
            self.assertEqual(snapshot["status"], "PASS")
            self.assertEqual(snapshot["outputs"][0]["path"], str(candidate))

            review_profile = build_review_profile(
                "restored_smoke_1",
                run_root,
                {
                    "textures": [
                        {
                            "id": "CORIROCK",
                            "room": "R1",
                            "content_class": "rock_organic_surface",
                            "expected_size": [16, 16],
                        }
                    ]
                },
            )
            self.assertEqual(
                review_profile["schema"],
                "openazrael.texture_lab.review_texture_manifest.v1",
            )
            self.assertTrue(review_profile["runtime_ready"])
            self.assertFalse(review_profile["export_allowed"])
            self.assertEqual(
                review_profile["textures"][0]["path"],
                "res://" + str(candidate.relative_to(ROOT)).replace("\\", "/"),
            )
            self.assertEqual(
                review_profile["textures"][0]["sha256"],
                sha256_file(candidate),
            )

            review_profile_path = run_dir / "godot_review_profile.json"
            review_profile_path.write_text(
                json.dumps(review_profile),
                encoding="utf-8",
            )
            self.assertEqual(
                verify_manifest(review_profile_path, ROOT)["status"],
                "HOLD",
            )

            handoff_path = run_dir / "review_handoff.html"
            handoff = build_handoff(
                "restored_smoke_1",
                run_root,
                handoff_path,
            )
            self.assertEqual(
                handoff["status"],
                "READY_FOR_HUMAN_REVIEW",
            )
            self.assertFalse(handoff["automatic_approval"])
            self.assertTrue(handoff_path.is_file())
            handoff_html = handoff_path.read_text(encoding="utf-8")
            self.assertIn("CORIROCK", handoff_html)
            self.assertIn("OBSERVATIONAL REVIEW HANDOFF", handoff_html)
            self.assertIn("Required manual checks", handoff_html)
            self.assertIn("gameplay_scale_acceptable", handoff_html)

            summary = build_summary("restored_smoke_1", run_root)
            self.assertEqual(summary["evidence_status"], "PASS")
            self.assertEqual(
                summary["manual_review_status"],
                "READY_FOR_MANUAL_REVIEW",
            )
            self.assertFalse(summary["automatic_quality_verdict"])
            self.assertFalse(summary["automatic_stage_approval"])
            self.assertEqual(
                summary["review_handoff"],
                str(handoff_path),
            )
            self.assertEqual(
                summary["performance"]["status"],
                "OBSERVED_WITH_LINEAR_ESTIMATE",
            )
            self.assertEqual(
                summary["textures"][0]["visual_evidence"]["candidate"],
                str(candidate),
            )
            self.assertEqual(
                summary["textures"][0]["visual_evidence"]["detail_comparison"],
                str(detail),
            )

            with self.assertRaises(SystemExit):
                approve(
                    "restored_smoke_1",
                    run_root,
                    approval_root,
                    "must fail before structured manual review",
                    manual_review_root,
                )

            manual = init_review(
                "restored_smoke_1",
                run_root,
                manual_review_root,
            )
            required_checks = manual["rows"][0]["required_checks"]
            record_texture(
                "restored_smoke_1",
                "CORIROCK",
                "ACCEPTED_FOR_STAGE",
                [(name, True) for name in required_checks],
                "synthetic manual visual review",
                manual_review_root,
            )
            manual_status = validate_manual_review(
                "restored_smoke_1",
                run_root,
                manual_review_root,
            )
            self.assertEqual(manual_status["status"], "PASS")

            approved = approve(
                "restored_smoke_1",
                run_root,
                approval_root,
                "synthetic stage approval",
                manual_review_root,
            )
            self.assertEqual(
                approved["receipt"]["schema"],
                "openazrael.texture_lab.stage_approval.v5",
            )
            self.assertEqual(
                validate_receipt(
                    "restored_smoke_1",
                    run_root,
                    approval_root,
                    manual_review_root,
                )["status"],
                "PASS",
            )

            receipt_path = approval_root / "restored_smoke_1.json"
            wrong_schema = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )
            wrong_schema["schema"] = "openazrael.texture_lab.stage_approval.v4"
            receipt_path.write_text(
                json.dumps(wrong_schema),
                encoding="utf-8",
            )
            old_receipt = validate_receipt(
                "restored_smoke_1",
                run_root,
                approval_root,
                manual_review_root,
            )
            self.assertEqual(old_receipt["status"], "STALE")
            self.assertFalse(old_receipt["checks"]["schema_ok"])
            receipt_path.write_text(
                json.dumps(approved["receipt"]),
                encoding="utf-8",
            )

            registry = root / "production_selection.json"
            selected = select_candidate(
                "restored_smoke_1",
                "CORIROCK",
                registry,
                run_root,
                approval_root,
                "synthetic production selection",
                manual_review_root,
            )
            self.assertEqual(selected["selected_tier"], "ai_restored")
            self.assertFalse(selected["automatic_selection"])
            production_ok = registry_status(
                registry,
                run_root,
                approval_root,
                manual_review_root,
            )
            self.assertEqual(production_ok["status"], "PASS")
            self.assertEqual(production_ok["selection_count"], 1)

            candidate.write_bytes(b"candidate-v2")
            write_review_manifest()

            stale_manual = validate_manual_review(
                "restored_smoke_1",
                run_root,
                manual_review_root,
            )
            self.assertEqual(stale_manual["status"], "STALE")

            stale = validate_receipt(
                "restored_smoke_1",
                run_root,
                approval_root,
                manual_review_root,
            )
            self.assertEqual(stale["status"], "STALE")
            self.assertEqual(
                stale.get("reason"),
                "current evidence is incomplete or invalid",
            )
            self.assertEqual(stale["current"]["status"], "FAIL")
            self.assertFalse(
                stale["current"]["checks"]["generation_record_ok"]
            )

            production_stale = registry_status(
                registry,
                run_root,
                approval_root,
                manual_review_root,
            )
            self.assertEqual(production_stale["status"], "STALE")
            self.assertEqual(
                production_stale["rows"][0]["status"],
                "STALE",
            )

    def test_validation_reports_source_relative_seam_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.png"
            candidate = root / "candidate.png"
            self._fixture(source)

            with Image.open(source) as im:
                enlarged = im.convert("RGBA").resize(
                    (im.width * 4, im.height * 4),
                    getattr(Image, "Resampling", Image).NEAREST,
                )
            enlarged.save(candidate)

            result = validate_pair(source, candidate, 4)
            self.assertIn("source_edge_seam_mae_rgba_0_255", result)
            self.assertIn("candidate_edge_seam_mae_rgba_0_255", result)
            self.assertIn("candidate_minus_source_seam_mae_rgba_0_255", result)
            self.assertIn("candidate_to_source_seam_ratio", result)
            self.assertAlmostEqual(
                result["candidate_minus_source_seam_mae_rgba_0_255"]["x"],
                result["candidate_edge_seam_mae_rgba_0_255"]["x"]
                - result["source_edge_seam_mae_rgba_0_255"]["x"],
            )
            self.assertAlmostEqual(
                result["candidate_minus_source_seam_mae_rgba_0_255"]["y"],
                result["candidate_edge_seam_mae_rgba_0_255"]["y"]
                - result["source_edge_seam_mae_rgba_0_255"]["y"],
            )

    def test_review_queue_carries_technical_seam_drift(self):
        selection = {
            "textures": [
                {
                    "id": "BAPFLOR#",
                    "room": "R8",
                    "content_class": "stone_floor",
                }
            ]
        }
        policy = {
            "defaults": {"ai_recreated": True},
            "classes": {
                "stone_floor": {
                    "ai_recreated": True,
                    "seam_review": "u_and_v_required",
                }
            },
        }
        sampling = {
            "textures": [
                {
                    "id": "BAPFLOR#",
                    "repeat_sampling_observed": True,
                    "repeat_axes": ["u", "v"],
                }
            ]
        }
        baseline = {
            "global_envelope": {
                "low_frequency_luma_mae_0_255": {
                    "p95": 0.25,
                    "max": 0.40,
                }
            }
        }
        drift = {
            "results": [
                {
                    "id": "BAPFLOR#",
                    "low_frequency_luma_mae_0_255": 0.20,
                    "alpha_silhouette_mismatch_fraction": 0.0,
                }
            ]
        }
        technical = {
            "results": [
                {
                    "id": "BAPFLOR#",
                    "source_edge_seam_mae_rgba_0_255": {"x": 4.0, "y": 6.0},
                    "candidate_edge_seam_mae_rgba_0_255": {"x": 5.5, "y": 5.0},
                    "candidate_minus_source_seam_mae_rgba_0_255": {
                        "x": 1.5,
                        "y": -1.0,
                    },
                    "candidate_to_source_seam_ratio": {
                        "x": 1.375,
                        "y": 0.8333333333,
                    },
                }
            ]
        }

        rows = build_review_rows(
            "recreated",
            selection,
            policy,
            sampling,
            baseline,
            drift,
            technical_report=technical,
        )
        self.assertEqual(
            rows[0]["candidate_minus_source_seam_mae_rgba_0_255"],
            {"x": 1.5, "y": -1.0},
        )
        self.assertEqual(
            rows[0]["source_edge_seam_mae_rgba_0_255"],
            {"x": 4.0, "y": 6.0},
        )

    def test_qwen_bootstrap_verifies_exact_file_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = b"qwen-test-model"
            path = root / "model.safetensors"
            path.write_bytes(payload)
            spec = {
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }

            good = verify_qwen_bootstrap_model(path, spec)
            self.assertEqual(good["status"], "PASS")
            self.assertTrue(good["size_ok"])
            self.assertTrue(good["sha256_ok"])

            path.write_bytes(b"x" * len(payload))
            bad_hash = verify_qwen_bootstrap_model(path, spec)
            self.assertEqual(bad_hash["status"], "FAIL")
            self.assertTrue(bad_hash["size_ok"])
            self.assertFalse(bad_hash["sha256_ok"])

    def test_qwen_bootstrap_plan_counts_only_unverified_models(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            present = b"present-model"
            missing = b"missing-model"
            contract = {
                "required_models": {
                    "diffusion": {
                        "relative_path": "models/diffusion_models/a.safetensors",
                        "size_bytes": len(present),
                        "sha256": hashlib.sha256(present).hexdigest(),
                        "download_url": "https://example.invalid/a",
                    },
                    "vae": {
                        "relative_path": "models/vae/b.safetensors",
                        "size_bytes": len(missing),
                        "sha256": hashlib.sha256(missing).hexdigest(),
                        "download_url": "https://example.invalid/b",
                    },
                }
            }
            present_path = root / "models/diffusion_models/a.safetensors"
            present_path.parent.mkdir(parents=True)
            present_path.write_bytes(present)

            plan = build_qwen_bootstrap_plan(root, contract)

        self.assertFalse(plan["all_models_ready"])
        self.assertEqual(plan["download_bytes"], len(missing))
        by_role = {row["role"]: row for row in plan["models"]}
        self.assertEqual(by_role["diffusion"]["verification"]["status"], "PASS")
        self.assertEqual(by_role["vae"]["verification"]["status"], "MISSING")

    def test_realesrgan_runtime_contract_accepts_only_pinned_compatibility_pair(self):
        contract = load_realesrgan_runtime_contract()
        good_payload = {
            "python_major_minor": "3.11",
            "torch": "2.1.2",
            "torchvision": "0.16.2",
            "functional_tensor_import": True,
            "basicsr": "1.4.2",
            "realesrgan": "0.3.0",
        }
        good = evaluate_probe(
            good_payload,
            contract,
            require_basicsr=True,
            require_realesrgan=True,
        )
        self.assertEqual(good["status"], "PASS")
        self.assertTrue(all(good["checks"].values()))

        bad_vision = dict(good_payload)
        bad_vision["torchvision"] = "0.17.0"
        bad_vision["functional_tensor_import"] = False
        bad = evaluate_probe(
            bad_vision,
            contract,
            require_basicsr=True,
            require_realesrgan=True,
        )
        self.assertEqual(bad["status"], "FAIL")
        self.assertFalse(bad["checks"]["torchvision_ok"])
        self.assertFalse(bad["checks"]["functional_tensor_ok"])

        bad_python = dict(good_payload)
        bad_python["python_major_minor"] = "3.12"
        bad = evaluate_probe(
            bad_python,
            contract,
            require_basicsr=True,
            require_realesrgan=True,
        )
        self.assertEqual(bad["status"], "FAIL")
        self.assertFalse(bad["checks"]["python_ok"])

        bad_torch = dict(good_payload)
        bad_torch["torch"] = "2.2.0"
        bad = evaluate_probe(
            bad_torch,
            contract,
            require_basicsr=True,
            require_realesrgan=True,
        )
        self.assertEqual(bad["status"], "FAIL")
        self.assertFalse(bad["checks"]["torch_ok"])

    def test_realesrgan_runtime_lock_candidate_requires_complete_doctor_evidence(self):
        contract = load_realesrgan_runtime_contract()
        packages = [
            "basicsr==1.4.2",
            "torch==2.1.2",
            "torchvision==0.16.2",
        ]
        freeze_text = "\n".join(sorted(packages)) + "\n"
        freeze_sha = hashlib.sha256(freeze_text.encode("utf-8")).hexdigest()
        doctor = {
            "schema": "openazrael.texture_lab.realesrgan_doctor.v3",
            "ready": True,
            "python": "3.11.x",
            "platform": "test-platform",
            "source_version": "0.3.0",
            "source_version_ok": True,
            "source_git_head": "fa4c8a03ae3dbc9ea6ed471a6ab5da94ac15c2ea",
            "source_git_head_ok": True,
            "checkpoint": {
                "status": "PASS",
                "sha256": "a" * 64,
                "size_bytes": 10,
            },
            "torch_runtime": {
                "status": "PASS",
                "version": "2.1.2",
                "cuda_available": True,
                "cuda_version": "12.1",
                "devices": [{"name": "Test GPU"}],
            },
            "runtime_contract": {
                "schema": contract["schema"],
                "probe": {
                    "status": "PASS",
                    "observed": {
                        "python_major_minor": "3.11",
                        "torch": "2.1.2",
                        "torchvision": "0.16.2",
                        "basicsr": "1.4.2",
                        "realesrgan": "0.3.0",
                    },
                },
                "pip_freeze": {
                    "status": "PASS",
                    "packages": sorted(packages),
                    "package_count": len(packages),
                    "sha256": freeze_sha,
                },
            },
        }

        candidate = build_lock_candidate(
            "restored_smoke_1",
            doctor,
            contract,
        )
        self.assertEqual(candidate["status"], "PASS")
        self.assertFalse(candidate["automatic_promotion"])
        self.assertFalse(candidate["canonical_config_mutated"])
        self.assertEqual(
            candidate["observed"]["pip_freeze"]["sha256"],
            freeze_sha,
        )
        self.assertEqual(
            requirements_text(candidate),
            freeze_text,
        )

        broken = json.loads(json.dumps(doctor))
        broken["runtime_contract"]["pip_freeze"]["status"] = "FAIL"
        hold = build_lock_candidate(
            "restored_smoke_1",
            broken,
            contract,
        )
        self.assertEqual(hold["status"], "HOLD")
        self.assertFalse(hold["checks"]["pip_freeze_pass"])
        with self.assertRaises(SystemExit):
            requirements_text(hold)

    def test_realesrgan_runtime_lock_promotion_plan_is_non_mutating_and_hash_stable(self):
        contract = load_realesrgan_runtime_contract()
        packages = [
            "basicsr==1.4.2",
            "torch==2.1.2",
            "torchvision==0.16.2",
        ]
        freeze_text = "\n".join(sorted(packages)) + "\n"
        freeze_sha = hashlib.sha256(freeze_text.encode("utf-8")).hexdigest()
        candidate = {
            "schema": "openazrael.texture_lab.realesrgan_runtime_lock_candidate.v1",
            "status": "PASS",
            "preset": "restored_smoke_1",
            "automatic_promotion": False,
            "canonical_config_mutated": False,
            "runtime_contract": {
                "schema": contract["schema"],
                "python_major_minor": "3.11",
                "torch": "2.1.2",
                "torchvision": "0.16.2",
                "basicsr": "1.4.2",
            },
            "observed": {
                "python": "3.11.x",
                "platform": "test-platform",
                "source_version": "0.3.0",
                "source_git_head": "fa4c8a03ae3dbc9ea6ed471a6ab5da94ac15c2ea",
                "checkpoint": {
                    "status": "PASS",
                    "sha256": "a" * 64,
                    "size_bytes": 10,
                },
                "torch_runtime": {
                    "status": "PASS",
                    "version": "2.1.2",
                    "cuda_available": True,
                    "cuda_version": "12.1",
                },
                "runtime_probe": {
                    "status": "PASS",
                    "observed": {
                        "python_major_minor": "3.11",
                        "torch": "2.1.2",
                        "torchvision": "0.16.2",
                        "basicsr": "1.4.2",
                    },
                },
                "pip_freeze": {
                    "status": "PASS",
                    "packages": sorted(packages),
                    "package_count": len(packages),
                    "sha256": freeze_sha,
                },
            },
            "doctor_evidence": {
                "path": "doctor.json",
                "sha256": "b" * 64,
                "size_bytes": 20,
            },
            "approval": {
                "status": "PASS",
                "path": "approval.json",
            },
        }

        compatibility = candidate_compatibility(candidate, contract)
        self.assertEqual(compatibility["status"], "PASS")

        plan = build_promotion_plan(
            candidate,
            "c" * 64,
            contract,
        )
        self.assertEqual(
            plan["status"],
            "READY_FOR_HUMAN_PROMOTION_REVIEW",
        )
        self.assertFalse(plan["automatic_promotion"])
        self.assertFalse(plan["canonical_files_mutated"])
        self.assertEqual(len(plan["proposed_files"]), 2)

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            rendered = write_plan_artifacts(plan, out_dir)
            self.assertTrue(
                Path(
                    rendered["local_proposed_files"]["environment_lock"]
                ).is_file()
            )
            self.assertTrue(
                Path(
                    rendered["local_proposed_files"]["requirements_lock"]
                ).is_file()
            )
            lock_text = Path(
                rendered["local_proposed_files"]["environment_lock"]
            ).read_text(encoding="utf-8")
            req_text = Path(
                rendered["local_proposed_files"]["requirements_lock"]
            ).read_text(encoding="utf-8")
            by_target = {
                row["target"]: row["sha256"]
                for row in rendered["proposed_files"]
            }
            self.assertEqual(
                hashlib.sha256(lock_text.encode("utf-8")).hexdigest(),
                by_target[
                    "tools/texture_lab/config/realesrgan_environment_lock.json"
                ],
            )
            self.assertEqual(
                hashlib.sha256(req_text.encode("utf-8")).hexdigest(),
                by_target[
                    "tools/texture_lab/requirements-realesrgan-lock.txt"
                ],
            )
            self.assertEqual(req_text, freeze_text)

        bad = json.loads(json.dumps(candidate))
        bad["runtime_contract"]["torch"] = "2.2.0"
        hold = build_promotion_plan(
            bad,
            "d" * 64,
            contract,
        )
        self.assertEqual(hold["status"], "HOLD")
        self.assertFalse(hold["compatibility"]["checks"]["torch_ok"])

    def test_realesrgan_texture_dependency_plan_excludes_face_stack(self):
        contract = load_realesrgan_runtime_contract()
        commands = dependency_install_commands(
            "python",
            ROOT / ".local/texture_lab/realesrgan/Real-ESRGAN",
            contract,
        )
        self.assertEqual(len(commands), 2)
        rendered = " ".join(" ".join(command) for command in commands)
        self.assertIn("basicsr==1.4.2", rendered)
        self.assertIn("--no-deps", commands[1])
        self.assertNotIn("gfpgan", rendered.lower())
        self.assertNotIn("facexlib", rendered.lower())
        self.assertEqual(commands[1][-2], "-e")

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

    def test_source_safe_pillow_pin_matches_runtime_and_requirements(self):
        requirements = (
            ROOT / "tools/texture_lab/requirements-source-safe.txt"
        ).read_text(encoding="utf-8").splitlines()
        self.assertIn(f"Pillow=={PINNED_PILLOW_VERSION}", requirements)
        self.assertEqual(PILLOW_VERSION, PINNED_PILLOW_VERSION)

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

    def test_first_restored_smoke_state_machine_is_passive_and_explicit(self):
        cases = [
            ((False, None, None, None), "NOT_EXECUTED"),
            ((True, "FAIL", None, None), "EVIDENCE_HOLD"),
            ((True, "PASS", "MISSING", None), "READY_FOR_MANUAL_REVIEW"),
            ((True, "PASS", "HOLD", None), "MANUAL_REVIEW_IN_PROGRESS"),
            ((True, "PASS", "STALE", None), "MANUAL_REVIEW_STALE"),
            ((True, "PASS", "PASS", "MISSING"), "READY_FOR_STAGE_APPROVAL"),
            ((True, "PASS", "PASS", "STALE"), "APPROVAL_STALE"),
            ((True, "PASS", "PASS", "PASS"), "STAGE_APPROVED"),
        ]
        for args, expected in cases:
            with self.subTest(expected=expected):
                result = classify_restored_smoke_1_state(*args)
                self.assertEqual(result["state"], expected)
                self.assertTrue(result["next_action"])

        approved = classify_restored_smoke_1_state(
            True,
            "PASS",
            "PASS",
            "PASS",
        )
        self.assertIn(
            "production selection remains a separate manual decision",
            approved["next_action"],
        )

    def test_first_recreated_smoke_state_machine_is_passive_and_explicit(self):
        cases = [
            ((False, None, None, None), "NOT_EXECUTED"),
            ((True, "FAIL", None, None), "EVIDENCE_HOLD"),
            ((True, "PASS", "MISSING", None), "READY_FOR_MANUAL_REVIEW"),
            ((True, "PASS", "HOLD", None), "MANUAL_REVIEW_IN_PROGRESS"),
            ((True, "PASS", "STALE", None), "MANUAL_REVIEW_STALE"),
            ((True, "PASS", "PASS", "MISSING"), "READY_FOR_STAGE_APPROVAL"),
            ((True, "PASS", "PASS", "STALE"), "APPROVAL_STALE"),
            ((True, "PASS", "PASS", "PASS"), "STAGE_APPROVED"),
        ]
        for args, expected in cases:
            with self.subTest(expected=expected):
                result = classify_recreated_smoke_1_state(*args)
                self.assertEqual(result["state"], expected)
                self.assertTrue(result["next_action"])

        approved = classify_recreated_smoke_1_state(
            True,
            "PASS",
            "PASS",
            "PASS",
        )
        self.assertIn(
            "production selection remains a separate manual decision",
            approved["next_action"],
        )

    def test_first_run_launchpad_builds_non_generating_recreated_readiness_plan(self):
        with tempfile.TemporaryDirectory() as td:
            comfy_root = Path(td) / "ComfyUI"
            plan = recreated_smoke_check_plan(
                comfy_root,
                "http://127.0.0.1:8188",
            )

        self.assertEqual(
            [row["name"] for row in plan],
            [
                "local_preflight",
                "comfy_doctor",
                "qwen_preflight",
                "canonical_bakeoff_dry_run",
            ],
        )
        self.assertIn("recreated_smoke_1", plan[0]["argv"])
        self.assertIn(str(comfy_root), plan[0]["argv"])

        self.assertIn("oa_tex_comfy_doctor.py", plan[1]["command"])
        self.assertIn("http://127.0.0.1:8188", plan[1]["argv"])

        self.assertIn("oa_tex_qwen_preflight.py", plan[2]["command"])
        self.assertIn("--require-model-files", plan[2]["argv"])
        self.assertIn(str(comfy_root), plan[2]["argv"])

        dry_run = plan[3]["argv"]
        self.assertIn("oa_tex_ai_bakeoff.py", plan[3]["command"])
        self.assertIn("recreated", dry_run)
        self.assertIn("recreated_smoke_1", dry_run)
        self.assertIn("--dry-run", dry_run)
        self.assertNotIn("--replace-existing-run", dry_run)

    def test_first_run_launchpad_recreated_clean_rerun_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            comfy_root = Path(td) / "ComfyUI"
            normal = recreated_smoke_plan(comfy_root)
            replacement = recreated_smoke_plan(
                comfy_root,
                replace_existing_run=True,
            )

        normal_bakeoff = normal[-1]["argv"]
        replacement_bakeoff = replacement[-1]["argv"]
        self.assertNotIn("--replace-existing-run", normal_bakeoff)
        self.assertEqual(
            replacement_bakeoff.count("--replace-existing-run"),
            1,
        )
        self.assertIn(str(comfy_root), replacement_bakeoff)

    def test_first_run_launchpad_builds_non_generating_smoke_readiness_plan(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Path(td) / "runtime"
            paths = runtime_paths(runtime)
            plan = restored_smoke_check_plan(runtime)

            self.assertEqual(
                [row["name"] for row in plan],
                [
                    "runtime_contract",
                    "local_preflight",
                    "runtime_doctor",
                    "canonical_bakeoff_dry_run",
                ],
            )
            runtime_probe = plan[0]["argv"]
            self.assertIn("--require-basicsr", runtime_probe)
            self.assertIn("--require-realesrgan", runtime_probe)
            self.assertIn(str(paths["python"]), runtime_probe)

            self.assertIn("restored_smoke_1", plan[1]["argv"])
            self.assertEqual(plan[2]["argv"][0], str(paths["python"]))

            dry_run = plan[3]["argv"]
            self.assertIn("oa_tex_ai_bakeoff.py", plan[3]["command"])
            self.assertIn("--dry-run", dry_run)
            self.assertNotIn("--replace-existing-run", dry_run)
            self.assertIn("restored_smoke_1", dry_run)

    def test_first_run_launchpad_builds_canonical_smoke_plan(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Path(td) / "runtime"
            paths = runtime_paths(runtime)
            plan = restored_smoke_plan(runtime)

            self.assertEqual(
                [row["name"] for row in plan],
                ["local_preflight", "runtime_doctor", "canonical_bakeoff"],
            )
            self.assertIn("restored_smoke_1", plan[0]["argv"])
            self.assertIn(str(paths["source"]), plan[0]["argv"])
            self.assertIn(str(paths["model"]), plan[0]["argv"])
            self.assertIn(str(paths["python"]), plan[0]["argv"])
            self.assertEqual(plan[1]["argv"][0], str(paths["python"]))
            self.assertIn("oa_tex_realesrgan_doctor.py", plan[1]["command"])
            self.assertIn("oa_tex_ai_bakeoff.py", plan[2]["command"])
            self.assertIn("--preset", plan[2]["argv"])
            self.assertIn("restored_smoke_1", plan[2]["argv"])

    def test_first_run_launchpad_clean_rerun_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Path(td) / "runtime"
            normal = restored_smoke_plan(runtime)
            replacement = restored_smoke_plan(
                runtime,
                replace_existing_run=True,
            )

        normal_bakeoff = normal[-1]["argv"]
        replacement_bakeoff = replacement[-1]["argv"]
        self.assertNotIn("--replace-existing-run", normal_bakeoff)
        self.assertEqual(
            replacement_bakeoff.count("--replace-existing-run"),
            1,
        )

    def test_first_run_launchpad_baseline_and_bootstrap_are_explicit(self):
        baseline = baseline_plan()
        self.assertEqual(
            [row["name"] for row in baseline],
            ["scan_classic", "build_enhanced", "calibrate_drift"],
        )
        commands = " ".join(row["command"] for row in baseline)
        self.assertIn("oa_tex_scan.py", commands)
        self.assertIn("oa_tex_run_poc.py", commands)
        self.assertIn("oa_tex_calibrate_drift.py", commands)

        with tempfile.TemporaryDirectory() as td:
            runtime = Path(td) / "runtime"
            no_deps_plan = bootstrap_plan(runtime, False, "python3.11")
            with_deps_plan = bootstrap_plan(runtime, True, "python3.11")

        self.assertEqual(
            [row["name"] for row in no_deps_plan],
            ["bootstrap_realesrgan"],
        )
        no_deps = no_deps_plan[0]["argv"]
        self.assertIn("--clone-upstream", no_deps)
        self.assertIn("--download-model", no_deps)
        self.assertIn("--create-venv", no_deps)
        self.assertNotIn("--install-python-deps", no_deps)

        self.assertEqual(
            [row["name"] for row in with_deps_plan],
            [
                "bootstrap_realesrgan",
                "verify_user_installed_torch",
                "install_realesrgan_python_deps",
            ],
        )
        self.assertIn("oa_tex_realesrgan_runtime.py", with_deps_plan[1]["command"])
        self.assertIn("check", with_deps_plan[1]["argv"])
        self.assertIn("--python-exe", no_deps_plan[0]["argv"])
        self.assertIn("python3.11", no_deps_plan[0]["argv"])
        self.assertIn(
            "--install-python-deps",
            with_deps_plan[2]["argv"],
        )

    def test_first_run_launchpad_validates_poc_source_ids_and_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "classic"
            source_dir.mkdir()
            selection = root / "selection.json"
            selection.write_text(
                json.dumps(
                    {
                        "textures": [
                            {"id": "A", "expected_size": [16, 8]},
                            {"id": "B", "expected_size": [8, 8]},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            Image.new("RGBA", (16, 8), (1, 2, 3, 255)).save(source_dir / "A.png")
            Image.new("RGBA", (8, 8), (4, 5, 6, 255)).save(source_dir / "B.png")

            good = poc_source_status(source_dir, selection)
            self.assertEqual(good["status"], "PASS")
            self.assertTrue(all(row["size_ok"] for row in good["rows"]))

            Image.new("RGBA", (9, 8), (4, 5, 6, 255)).save(source_dir / "B.png")
            bad = poc_source_status(source_dir, selection)
            self.assertEqual(bad["status"], "HOLD")
            by_id = {row["id"]: row for row in bad["rows"]}
            self.assertFalse(by_id["B"]["size_ok"])

    def test_production_registry_v1_migrates_in_memory_to_v2(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "production_selection.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": LEGACY_REGISTRY_SCHEMA,
                        "status": "NO_PRODUCTION_SELECTIONS",
                        "automatic_selection": False,
                        "profiles": {
                            "remastered": {
                                "CORIROCK": {
                                    "texture_id": "CORIROCK",
                                    "selected_from_preset": "restored_smoke_1",
                                }
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            migrated = load_registry(path)
            self.assertEqual(
                migrated["schema"],
                CURRENT_REGISTRY_SCHEMA,
            )
            self.assertEqual(
                migrated["migrated_from_schema"],
                LEGACY_REGISTRY_SCHEMA,
            )
            self.assertEqual(migrated["superseded_selections"], [])
            self.assertEqual(migrated["revocations"], [])
            self.assertEqual(
                migrated["profiles"]["remastered"]["CORIROCK"]["schema"],
                CURRENT_RECORD_SCHEMA,
            )

            path.write_text(
                json.dumps({"schema": "unsupported.v99"}),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                load_registry(path)

    def test_production_registry_status_marks_malformed_records_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "production_selection.json"
            registry.write_text(
                json.dumps(
                    {
                        "schema": CURRENT_REGISTRY_SCHEMA,
                        "status": "HAS_EXPLICIT_PRODUCTION_SELECTIONS",
                        "automatic_selection": False,
                        "profiles": {
                            "remastered": {
                                "BROKEN": "not-an-object",
                            }
                        },
                        "superseded_selections": [],
                        "revocations": [],
                    }
                ),
                encoding="utf-8",
            )
            status = registry_status(
                registry,
                root / "runs",
                root / "approvals",
                root / "manual_reviews",
            )
            self.assertEqual(status["status"], "STALE")
            self.assertEqual(status["selection_count"], 1)
            self.assertFalse(
                status["rows"][0]["checks"]["record_is_object"]
            )

            registry.write_text(
                json.dumps(
                    {
                        "schema": CURRENT_REGISTRY_SCHEMA,
                        "status": "HAS_EXPLICIT_PRODUCTION_SELECTIONS",
                        "automatic_selection": False,
                        "profiles": {
                            "remastered": {
                                "BROKEN": {
                                    "schema": CURRENT_RECORD_SCHEMA,
                                    "texture_id": "BROKEN",
                                    "presentation_profile": "remastered",
                                    "automatic_selection": False,
                                    "selected_tier": "ai_restored",
                                    "selected_from_preset": "no_such_preset",
                                }
                            }
                        },
                        "superseded_selections": [],
                        "revocations": [],
                    }
                ),
                encoding="utf-8",
            )
            status = registry_status(
                registry,
                root / "runs",
                root / "approvals",
                root / "manual_reviews",
            )
            self.assertEqual(status["status"], "STALE")
            self.assertFalse(status["rows"][0]["checks"]["preset_valid"])

    def test_production_selection_preserves_superseded_history(self):
        registry = {
            "profiles": {"remastered": {}},
            "automatic_selection": False,
        }
        first = {
            "texture_id": "CORIROCK",
            "selected_tier": "ai_restored",
            "selected_from_preset": "restored_smoke_1",
            "selected_at_utc": "2026-09-19T10:00:00+00:00",
            "candidate_sha256": "a" * 64,
        }
        second = {
            "texture_id": "CORIROCK",
            "selected_tier": "ai_recreated",
            "selected_from_preset": "recreated_full",
            "selected_at_utc": "2026-09-19T11:00:00+00:00",
            "candidate_sha256": "b" * 64,
        }

        store_selection_record(registry, "CORIROCK", first)
        self.assertNotIn("superseded_selections", registry)
        self.assertEqual(
            registry["profiles"]["remastered"]["CORIROCK"],
            first,
        )

        store_selection_record(registry, "CORIROCK", second)
        self.assertEqual(
            registry["profiles"]["remastered"]["CORIROCK"],
            second,
        )
        self.assertEqual(len(registry["superseded_selections"]), 1)
        history = registry["superseded_selections"][0]
        self.assertEqual(history["previous_selection"], first)
        self.assertEqual(
            history["replaced_by"]["candidate_sha256"],
            "b" * 64,
        )

    def test_runtime_manifest_profiles_are_fail_safe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for relative, size in [
                ("assets/textures/classic/A.png", (16, 8)),
                ("assets/textures/classic/MASK#.png", (8, 8)),
                ("assets/textures/enhanced/A/lanczos_x4.png", (64, 32)),
                ("assets/textures/enhanced/MASK#/nearest_x4.png", (32, 32)),
                ("assets/textures/ai_restored/A/realesrgan_x4.png", (64, 32)),
            ]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", size, (10, 20, 30, 255)).save(path)

            selection = {
                "textures": [
                    {
                        "id": "A",
                        "room": "R1",
                        "content_class": "rock_organic_surface",
                        "expected_size": [16, 8],
                    },
                    {
                        "id": "MASK#",
                        "room": "R1",
                        "content_class": "binary_mask_hard_edge",
                        "expected_size": [8, 8],
                    },
                ]
            }
            policy = {
                "classes": {
                    "binary_mask_hard_edge": {
                        "preferred_tier": "enhanced_nearest",
                    }
                }
            }
            empty_registry = {
                "profiles": {"remastered": {}},
            }

            classic = build_manifest(
                "classic",
                selection,
                policy,
                empty_registry,
                root / "runs",
                root / "approvals",
                root=root,
            )
            self.assertTrue(classic["runtime_ready"])
            self.assertTrue(
                all(row["resolved_tier"] == "classic" for row in classic["textures"])
            )

            enhanced = build_manifest(
                "enhanced",
                selection,
                policy,
                empty_registry,
                root / "runs",
                root / "approvals",
                enhanced_method="lanczos",
                root=root,
            )
            by_id = {row["id"]: row for row in enhanced["textures"]}
            self.assertEqual(by_id["A"]["resolved_tier"], "enhanced_lanczos")
            self.assertEqual(by_id["MASK#"]["resolved_tier"], "enhanced_nearest")
            self.assertEqual(
                by_id["MASK#"]["resolution_reason"],
                "policy_forced_nearest",
            )

            remastered_empty = build_manifest(
                "remastered",
                selection,
                policy,
                empty_registry,
                root / "runs",
                root / "approvals",
                root=root,
            )
            self.assertEqual(remastered_empty["classic_fallback_count"], 2)
            self.assertEqual(
                remastered_empty["status"],
                "SAFE_CLASSIC_FALLBACKS",
            )

            record = {
                "texture_id": "A",
                "selected_tier": "ai_restored",
                "selected_from_preset": "restored_smoke_1",
                "candidate_path": "assets/textures/ai_restored/A/realesrgan_x4.png",
                "candidate_sha256": sha256_file(
                    root / "assets/textures/ai_restored/A/realesrgan_x4.png"
                ),
            }
            registry = {
                "profiles": {
                    "remastered": {
                        "A": record,
                    }
                }
            }

            def pass_status(_record, _run_root, _approval_root):
                return {"status": "PASS", "checks": {"synthetic": True}}

            remastered_pass = build_manifest(
                "remastered",
                selection,
                policy,
                registry,
                root / "runs",
                root / "approvals",
                root=root,
                status_resolver=pass_status,
            )
            by_id = {row["id"]: row for row in remastered_pass["textures"]}
            self.assertEqual(by_id["A"]["resolved_tier"], "ai_restored")
            self.assertEqual(
                by_id["A"]["resolution_reason"],
                "explicit_current_production_selection",
            )
            self.assertEqual(by_id["MASK#"]["resolved_tier"], "classic")

            def stale_status(_record, _run_root, _approval_root):
                return {"status": "STALE", "checks": {"synthetic": False}}

            remastered_stale = build_manifest(
                "remastered",
                selection,
                policy,
                registry,
                root / "runs",
                root / "approvals",
                root=root,
                status_resolver=stale_status,
            )
            by_id = {row["id"]: row for row in remastered_stale["textures"]}
            self.assertEqual(by_id["A"]["resolved_tier"], "classic")
            self.assertEqual(
                by_id["A"]["resolution_reason"],
                "stale_production_selection_fallback_to_classic",
            )
            self.assertEqual(
                remastered_stale["status"],
                "SAFE_CLASSIC_FALLBACK_STALE_SELECTIONS",
            )

    def test_runtime_manifest_verifier_detects_changed_and_unsafe_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classic = root / "assets/textures/classic/A.png"
            classic.parent.mkdir(parents=True)
            Image.new("RGBA", (16, 8), (1, 2, 3, 255)).save(classic)

            selection_path = root / "selection.json"
            policy_path = root / "policy.json"
            registry_path = root / "registry.json"
            selection = {
                "textures": [
                    {
                        "id": "A",
                        "room": "R1",
                        "content_class": "rock_organic_surface",
                        "expected_size": [16, 8],
                    }
                ]
            }
            policy = {"classes": {}}
            registry = {"profiles": {"remastered": {}}}
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            manifest = build_manifest(
                "classic",
                selection,
                policy,
                registry,
                root / "runs",
                root / "approvals",
                root=root,
            )
            manifest["inputs"] = {
                "selection": input_file_record(selection_path, root),
                "policy": input_file_record(policy_path, root),
                "production_registry": input_file_record(registry_path, root),
            }
            manifest_path = root / "classic_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            good = verify_manifest(manifest_path, root)
            self.assertEqual(good["status"], "PASS")

            stale_declared = json.loads(json.dumps(manifest))
            stale_declared["profile"] = "remastered"
            stale_declared["status"] = "SAFE_CLASSIC_FALLBACK_STALE_SELECTIONS"
            stale_declared["stale_production_selection_count"] = 1
            stale_declared["classic_fallback_count"] = 1
            stale_declared["textures"][0]["profile"] = "remastered"
            stale_declared["textures"][0]["resolution_reason"] = (
                "stale_production_selection_fallback_to_classic"
            )
            stale_declared["textures"][0]["production_selection_status"] = "STALE"
            stale_declared["classic_fallback_count"] = 1
            stale_declared["textures"][0]["profile"] = "remastered"
            stale_declared["textures"][0]["resolution_reason"] = (
                "stale_production_selection_fallback_to_classic"
            )
            stale_declared["textures"][0]["production_selection_status"] = "STALE"
            stale_declared_path = root / "stale_declared_manifest.json"
            stale_declared_path.write_text(
                json.dumps(stale_declared),
                encoding="utf-8",
            )
            self.assertEqual(
                verify_manifest(stale_declared_path, root)["status"],
                "STALE",
            )

            not_ready = json.loads(json.dumps(manifest))
            not_ready["runtime_ready"] = False
            not_ready_path = root / "not_ready_manifest.json"
            not_ready_path.write_text(json.dumps(not_ready), encoding="utf-8")
            self.assertEqual(
                verify_manifest(not_ready_path, root)["status"],
                "HOLD",
            )

            Image.new("RGBA", (16, 8), (9, 9, 9, 255)).save(classic)
            stale = verify_manifest(manifest_path, root)
            self.assertEqual(stale["status"], "STALE")
            self.assertEqual(stale["stale_texture_ids"], ["A"])

            missing_row = json.loads(json.dumps(manifest))
            missing_row["textures"] = []
            missing_row["texture_count"] = 0
            missing_row_path = root / "missing_row_manifest.json"
            missing_row_path.write_text(
                json.dumps(missing_row),
                encoding="utf-8",
            )
            missing_row_status = verify_manifest(missing_row_path, root)
            self.assertEqual(missing_row_status["status"], "HOLD")
            self.assertFalse(
                missing_row_status["coverage"]["selection_coverage_ok"]
            )

            duplicate = json.loads(json.dumps(manifest))
            duplicate["textures"].append(
                json.loads(json.dumps(duplicate["textures"][0]))
            )
            duplicate["texture_count"] = 2
            duplicate_path = root / "duplicate_manifest.json"
            duplicate_path.write_text(
                json.dumps(duplicate),
                encoding="utf-8",
            )
            duplicate_status = verify_manifest(duplicate_path, root)
            self.assertEqual(duplicate_status["status"], "HOLD")
            self.assertFalse(duplicate_status["coverage"]["ids_unique"])

            unknown_profile = json.loads(json.dumps(manifest))
            unknown_profile["profile"] = "experimental"
            unknown_profile["textures"][0]["profile"] = "experimental"
            unknown_profile_path = root / "unknown_profile_manifest.json"
            unknown_profile_path.write_text(
                json.dumps(unknown_profile),
                encoding="utf-8",
            )
            self.assertEqual(
                verify_manifest(unknown_profile_path, root)["status"],
                "HOLD",
            )

            manifest["textures"][0]["path"] = "res://assets/textures/../escape.png"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            unsafe = verify_manifest(manifest_path, root)
            self.assertEqual(unsafe["status"], "HOLD")
            self.assertEqual(unsafe["missing_or_unsafe_texture_ids"], ["A"])

    def test_runtime_export_compiler_requires_verified_immutable_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classic = root / "assets/textures/classic/A.png"
            classic.parent.mkdir(parents=True)
            Image.new("RGBA", (16, 8), (1, 2, 3, 255)).save(classic)

            selection_path = root / "selection.json"
            policy_path = root / "policy.json"
            registry_path = root / "registry.json"
            selection = {
                "textures": [
                    {
                        "id": "A",
                        "room": "R1",
                        "content_class": "rock_organic_surface",
                        "expected_size": [16, 8],
                    }
                ]
            }
            policy = {"classes": {}}
            registry = {"profiles": {"remastered": {}}}
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            manifest = build_manifest(
                "classic",
                selection,
                policy,
                registry,
                root / "runs",
                root / "approvals",
                root=root,
            )
            manifest["inputs"] = {
                "selection": input_file_record(selection_path, root),
                "policy": input_file_record(policy_path, root),
                "production_registry": input_file_record(registry_path, root),
            }
            manifest_path = root / "classic_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            out_script = root / "export/texture_runtime_map.gd"
            snapshot = root / "export/snapshot.json"

            result = compile_export(
                manifest_path,
                root,
                out_script,
                snapshot,
            )
            self.assertEqual(result["status"], "READY_FOR_GODOT_IMPORT")
            self.assertTrue(out_script.is_file())
            self.assertTrue(snapshot.is_file())
            script = out_script.read_text(encoding="utf-8")
            self.assertIn('const PROFILE := "classic"', script)
            self.assertIn(
                '"path": "res://assets/textures/classic/A.png"',
                script,
            )
            self.assertIn(sha256_file(manifest_path), script)

            stale_declared = json.loads(json.dumps(manifest))
            stale_declared["profile"] = "remastered"
            stale_declared["status"] = "SAFE_CLASSIC_FALLBACK_STALE_SELECTIONS"
            stale_declared["stale_production_selection_count"] = 1
            stale_declared_path = root / "stale_export_manifest.json"
            stale_declared_path.write_text(
                json.dumps(stale_declared),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                compile_export(
                    stale_declared_path,
                    root,
                    root / "export/stale_declared_map.gd",
                    root / "export/stale_declared_snapshot.json",
                )

            Image.new("RGBA", (16, 8), (9, 9, 9, 255)).save(classic)
            with self.assertRaises(RuntimeError):
                compile_export(
                    manifest_path,
                    root,
                    root / "export/stale_map.gd",
                    root / "export/stale_snapshot.json",
                )

    def test_texture_lab_cross_contracts_current_repo_pass(self):
        selection = json.loads(
            (ROOT / "tools/texture_lab/config/rt_poc_01_selection.json").read_text(
                encoding="utf-8"
            )
        )
        policy = json.loads(
            (ROOT / "tools/texture_lab/config/ai_review_policy.json").read_text(
                encoding="utf-8"
            )
        )
        smoke = json.loads(
            (ROOT / "tools/texture_lab/config/ai_smoke_sets.json").read_text(
                encoding="utf-8"
            )
        )
        backends = json.loads(
            (ROOT / "tools/texture_lab/config/ai_backends.json").read_text(
                encoding="utf-8"
            )
        )
        models = json.loads(
            (ROOT / "tools/texture_lab/config/model_registry.json").read_text(
                encoding="utf-8"
            )
        )
        qwen = json.loads(
            (ROOT / "tools/texture_lab/config/qwen_2511_contract.json").read_text(
                encoding="utf-8"
            )
        )
        workflow = json.loads(
            (
                ROOT
                / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
            ).read_text(encoding="utf-8")
        )
        policy_summary = json.loads(
            (
                ROOT / "data/texture_lab/rt_poc_01_ai_policy_summary.json"
            ).read_text(encoding="utf-8")
        )

        result = validate_contracts(
            selection,
            policy,
            smoke,
            backends,
            models,
            qwen,
            workflow,
            policy_summary,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failed"], [])

    def test_texture_lab_cross_contracts_detect_drift(self):
        selection = {
            "schema": "openazrael.texture_lab.rt_poc_01_selection.v1",
            "automatic_winner": False,
            "textures": [
                {
                    "id": f"TEX{i}",
                    "room": "R1",
                    "content_class": "rock",
                    "expected_size": [16, 16],
                }
                for i in range(12)
            ],
        }
        policy = {
            "schema": "openazrael.texture_lab.ai_review_policy.v1",
            "defaults": {
                "ai_restored": True,
                "ai_recreated": True,
                "manual_visual_review": True,
                "automatic_production_promotion": False,
            },
            "classes": {"rock": {}},
        }
        all_ids = [f"TEX{i}" for i in range(12)]
        smoke = {
            "schema": "openazrael.texture_lab.ai_smoke_sets.v2",
            "presets": {
                "restored_full": {
                    "mode": "restored",
                    "textures": all_ids[:-1],
                    "requires_approval": ["restored_full"],
                },
                "recreated_full": {
                    "mode": "recreated",
                    "textures": all_ids,
                    "requires_approval": [],
                },
            },
            "recommended_order": ["restored_full", "recreated_full"],
        }
        backends = {
            "ai_restored": {
                "primary": {
                    "model": "RealESRGAN_x4plus",
                    "factor": 2,
                    "tile": 0,
                    "fp32": True,
                }
            },
            "ai_recreated": {
                "primary": {
                    "model_label": "Qwen-Image-Edit-2511",
                    "fixed_seed": 1,
                }
            },
            "automatic_production_promotion": False,
        }
        models = {
            "models": {
                "RealESRGAN_x4plus": {
                    "scale": 4,
                    "default_tile": 0,
                    "default_fp32": True,
                    "checkpoint_size_bytes": 10,
                    "checkpoint_sha256": "a" * 64,
                }
            }
        }
        qwen = {
            "model_label": "Qwen-Image-Edit-2511",
            "poc_sampling": {
                "seed": 734234,
                "steps": 40,
                "cfg": 4,
                "sampler": "euler",
                "scheduler": "simple",
                "lightning_lora_enabled": False,
            },
            "api_workflow_policy": {
                "automatic_production_promotion": False,
                "no_lightning_lora": True,
                "single_primary_load_image": True,
            },
            "canonical_openazrael_workflow": {
                "bindings": {
                    "load_image_node": "1",
                    "prompt_node": "7",
                    "negative_prompt_node": "8",
                    "seed_node": "10",
                }
            },
            "required_models": {
                role: {
                    "filename": filename,
                    "size_bytes": 10,
                    "sha256": "b" * 64,
                }
                for role, filename in {
                    "diffusion": "diff.safetensors",
                    "text_encoder": "clip.safetensors",
                    "vae": "vae.safetensors",
                }.items()
            },
        }
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "x.png"}},
            "2": {
                "class_type": "UNETLoader",
                "inputs": {"unet_name": "diff.safetensors"},
            },
            "3": {
                "class_type": "CLIPLoader",
                "inputs": {"clip_name": "clip.safetensors"},
            },
            "4": {
                "class_type": "VAELoader",
                "inputs": {"vae_name": "vae.safetensors"},
            },
            "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {}},
            "8": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {}},
            "10": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 734234,
                    "steps": 40,
                    "cfg": 4,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                },
            },
        }
        policy_summary = {
            "selection_count": 12,
            "ai_restored": {"eligible_count": 12, "skipped": []},
            "ai_recreated": {"eligible_count": 12, "skipped": []},
            "automatic_production_promotion": False,
        }

        result = validate_contracts(
            selection,
            policy,
            smoke,
            backends,
            models,
            qwen,
            workflow,
            policy_summary,
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(
            "restored_full_matches_policy_eligibility",
            result["failed"],
        )
        self.assertIn("approval_graph_acyclic", result["failed"])
        self.assertIn("restored_scale_matches_registry", result["failed"])
        self.assertIn("qwen_seed_matches_backend", result["failed"])

    def test_comparison_preview_preserves_aspect_ratio(self):
        wide = Image.new("RGBA", (64, 32), (255, 0, 0, 128))
        classic_preview = _fit_preview(wide, 320, True)
        ai_preview = _fit_preview(wide.resize((256, 128)), 320, False)

        self.assertEqual(classic_preview.size, (320, 160))
        self.assertEqual(ai_preview.size, (320, 160))

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
