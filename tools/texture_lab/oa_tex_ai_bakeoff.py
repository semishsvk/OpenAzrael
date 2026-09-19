#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from common import (
    AI_RECREATED_ROOT,
    AI_RESTORED_ROOT,
    ROOT,
    named_candidate_root,
    write_json,
)
from oa_tex_prompt import build_prompt_pair

QWEN_CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
QWEN_WORKFLOW = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
AI_BACKENDS = ROOT / "tools/texture_lab/config/ai_backends.json"
SMOKE_SETS = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"
CANONICAL_SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
CANONICAL_POLICY = ROOT / "tools/texture_lab/config/ai_review_policy.json"
CANONICAL_PROFILES = ROOT / "tools/texture_lab/profiles/recreate_profiles.json"
CANONICAL_SOURCE_DIR = ROOT / "assets/textures/classic"
CANONICAL_ENHANCED_DIR = ROOT / "assets/textures/enhanced"
DEFAULT_RESTORED_DIR = AI_RESTORED_ROOT
DEFAULT_RECREATED_DIR = AI_RECREATED_ROOT


def run_instance_id(preset: str | None, dry_run: bool) -> str | None:
    if not preset or dry_run:
        return None
    return uuid.uuid4().hex


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def policy_for(entry: dict, policy: dict) -> dict:
    merged = dict(policy.get("defaults", {}))
    merged.update(policy.get("classes", {}).get(str(entry.get("content_class", "")), {}))
    return merged


def eligible_entries(selection: dict, policy: dict, mode: str) -> tuple[list[dict], list[dict]]:
    allowed = []
    skipped = []
    key = "ai_restored" if mode == "restored" else "ai_recreated"
    for entry in selection["textures"]:
        rules = policy_for(entry, policy)
        if bool(rules.get(key, False)):
            allowed.append({**entry, "policy": rules})
        else:
            skipped.append(
                {
                    "id": entry["id"],
                    "content_class": entry.get("content_class"),
                    "reason": rules.get("reason", f"{key}=false"),
                    "preferred_tier": rules.get("preferred_tier"),
                }
            )
    return allowed, skipped


def apply_execution_subset(
    mode: str,
    allowed: list[dict],
    preset_name: str | None,
    only: list[str] | None,
) -> tuple[list[dict], list[dict], dict | None]:
    if preset_name and only:
        raise SystemExit("--preset and --only are mutually exclusive")

    selected_ids: set[str] | None = None
    preset_meta = None
    if preset_name:
        smoke_sets = load_json(SMOKE_SETS)
        preset = smoke_sets.get("presets", {}).get(preset_name)
        if not isinstance(preset, dict):
            raise SystemExit(f"unknown AI smoke preset: {preset_name}")
        if str(preset.get("mode")) != mode:
            raise SystemExit(
                f"preset {preset_name!r} is for mode={preset.get('mode')}, not {mode}"
            )
        selected_ids = {str(value) for value in preset.get("textures", [])}
        preset_meta = {
            "name": preset_name,
            "purpose": preset.get("purpose"),
            "textures": list(preset.get("textures", [])),
        }
    elif only:
        selected_ids = {str(value) for value in only}

    if selected_ids is None:
        return allowed, [], preset_meta

    selected = [entry for entry in allowed if str(entry["id"]) in selected_ids]
    deferred = [
        {
            "id": entry["id"],
            "content_class": entry.get("content_class"),
            "reason": "not_selected_for_this_execution_stage",
        }
        for entry in allowed
        if str(entry["id"]) not in selected_ids
    ]
    missing_requested = selected_ids - {str(entry["id"]) for entry in allowed}
    if missing_requested:
        raise SystemExit(
            "requested textures are not eligible for this mode: "
            + ", ".join(sorted(missing_requested))
        )
    return selected, deferred, preset_meta


def _quoted_command(argv: list[str]) -> str:
    import shlex
    return shlex.join(argv)


def build_restore_plan(args, entries: list[dict]) -> list[dict]:
    ids = [str(entry["id"]) for entry in entries]
    doctor = [
        args.realesrgan_python,
        str(ROOT / "tools/texture_lab/oa_tex_realesrgan_doctor.py"),
        "--model", args.restore_model,
        "--report", str(args.run_dir / "realesrgan_doctor.json"),
    ]
    if args.realesrgan_root:
        doctor.extend(["--realesrgan-root", str(args.realesrgan_root)])
    if args.model_path:
        doctor.extend(["--model-path", str(args.model_path)])

    report = args.run_dir / "ai_restore_run.json"
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_restore.py"),
        "--input", str(args.source_dir),
        "--output", str(args.restored_dir),
        "--report", str(report),
        "--factor", str(args.factor),
        "--model", args.restore_model,
        "--backend", "realesrgan-python",
        "--python-exe", args.realesrgan_python,
        "--tile", str(args.tile),
        "--only",
        *ids,
    ]
    if args.realesrgan_root:
        argv.extend(["--realesrgan-root", str(args.realesrgan_root)])
    if args.model_path:
        argv.extend(["--model-path", str(args.model_path)])
    argv.append("--fp32" if args.fp32 else "--no-fp32")
    if args.denoise_strength is not None:
        argv.extend(["--denoise-strength", str(args.denoise_strength)])

    technical_out = args.run_dir / "ai_restored_validation.json"
    technical = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_validate.py"),
        "--source-dir", str(args.source_dir),
        "--candidate-dir", str(args.restored_dir),
        "--variant", f"realesrgan_x{args.factor}.png",
        "--factor", str(args.factor),
        "--out", str(technical_out),
        "--only", *ids,
    ]

    drift_out = args.run_dir / "ai_restored_structural_drift.json"
    qa = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_structural_drift.py"),
        "--source-dir", str(args.source_dir),
        "--candidate-dir", str(args.restored_dir),
        "--variant", f"realesrgan_x{args.factor}.png",
        "--selection", str(args.selection),
        "--out", str(drift_out),
        "--allow-missing",
        "--only", *ids,
    ]
    review_json = args.run_dir / "ai_restored_review_queue.json"
    review = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_report.py"),
        "restored",
        "--drift", str(drift_out),
        "--selection", str(args.selection),
        "--technical", str(technical_out),
        "--out-json", str(review_json),
        "--out-md", str(args.run_dir / "ai_restored_review_queue.md"),
        "--only", *ids,
    ]
    review_pack = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_pack.py"),
        "restored",
        "--review-queue", str(review_json),
        "--source-dir", str(args.source_dir),
        "--restored-dir", str(args.restored_dir),
        "--out-dir", str(args.run_dir / "review_pack"),
        "--manifest", str(args.run_dir / "ai_restored_review_pack.json"),
        "--markdown", str(args.run_dir / "ai_restored_review_pack.md"),
    ]
    enhanced_dir = getattr(args, "recreate_input_dir", None)
    if enhanced_dir is not None:
        review_pack.extend(["--enhanced-dir", str(enhanced_dir)])
    return [
        {"stage": "realesrgan_doctor", "argv": doctor, "command": _quoted_command(doctor)},
        {"stage": "generate", "argv": argv, "command": _quoted_command(argv)},
        {"stage": "technical_qa", "argv": technical, "command": _quoted_command(technical)},
        {"stage": "structural_qa", "argv": qa, "command": _quoted_command(qa)},
        {"stage": "review_queue", "argv": review, "command": _quoted_command(review)},
        {"stage": "review_pack", "argv": review_pack, "command": _quoted_command(review_pack)},
    ]


def required_qwen_model_files(comfy_root: Path | None, contract: dict) -> list[Path]:
    if comfy_root is None:
        return []
    return [
        comfy_root / str(spec["relative_path"])
        for spec in contract["required_models"].values()
    ]


def _recreate_generate_job(
    args,
    entry: dict,
    source: Path,
    conditioning: Path,
    output: Path,
    job_record: Path,
    profiles: dict,
    model_args: list[str],
    suffix: str | None = None,
) -> dict:
    texture_id = str(entry["id"])
    prompts = build_prompt_pair(profiles, str(entry["content_class"]))
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_recreate.py"),
        str(source),
        "--conditioning-image", str(conditioning),
        "--workflow", str(args.workflow),
        "--server", args.server,
        "--output", str(output),
        "--job-record", str(job_record),
        "--load-image-node", str(args.load_image_node),
        "--prompt-node", str(args.prompt_node),
        "--prompt-key", args.prompt_key,
        "--prompt", prompts["positive"],
        "--negative-prompt-node", str(args.negative_prompt_node),
        "--negative-prompt-key", args.negative_prompt_key,
        "--negative-prompt", prompts["negative"],
        "--seed-node", str(args.seed_node),
        "--seed-key", args.seed_key,
        "--seed", str(args.seed),
        "--model-label", args.model_label,
        *model_args,
    ]
    return {
        "stage": "generate",
        "id": texture_id,
        "part": suffix,
        "content_class": entry.get("content_class"),
        "conditioning_image": str(conditioning),
        "policy": entry["policy"],
        "argv": argv,
        "command": _quoted_command(argv),
    }


def build_recreate_plan(args, entries: list[dict], profiles: dict, contract: dict) -> list[dict]:
    jobs = []

    doctor = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_comfy_doctor.py"),
        "--server", args.server,
        "--out", str(args.run_dir / "comfy_doctor.json"),
    ]
    jobs.append({"stage": "comfy_doctor", "argv": doctor, "command": _quoted_command(doctor)})

    preflight = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_qwen_preflight.py"),
        str(args.workflow),
        "--load-image-node", str(args.load_image_node),
        "--prompt-node", str(args.prompt_node),
        "--negative-prompt-node", str(args.negative_prompt_node),
        "--seed-node", str(args.seed_node),
        "--out", str(args.run_dir / "qwen_preflight.json"),
    ]
    if args.comfy_root is not None:
        preflight.extend(["--comfy-root", str(args.comfy_root), "--require-model-files"])
    jobs.append({"stage": "qwen_preflight", "argv": preflight, "command": _quoted_command(preflight)})

    model_files = required_qwen_model_files(args.comfy_root, contract) + list(args.model_file)
    model_args = []
    for model_file in model_files:
        model_args.extend(["--model-file", str(model_file)])

    for entry in entries:
        texture_id = str(entry["id"])
        atlas = entry["policy"].get("atlas_split")
        final_output = args.recreated_dir / texture_id / "selected.png"

        if isinstance(atlas, dict):
            axis = str(atlas["axis"])
            segments = int(atlas["segments"])
            atlas_root = args.run_dir / "atlas_parts" / texture_id
            classic_parts = atlas_root / "classic"
            enhanced_parts = atlas_root / "enhanced"
            generated_parts = atlas_root / "generated"
            classic_source = args.source_dir / f"{texture_id}.png"
            enhanced_source = (
                args.recreate_input_dir / texture_id / args.recreate_input_variant
            )

            split_classic = [
                sys.executable,
                str(ROOT / "tools/texture_lab/oa_tex_atlas.py"),
                "split",
                str(classic_source),
                "--output-dir", str(classic_parts),
                "--axis", axis,
                "--segments", str(segments),
                "--manifest", str(atlas_root / "classic_split.json"),
            ]
            jobs.append(
                {
                    "stage": "atlas_split_classic",
                    "id": texture_id,
                    "argv": split_classic,
                    "command": _quoted_command(split_classic),
                }
            )

            split_enhanced = [
                sys.executable,
                str(ROOT / "tools/texture_lab/oa_tex_atlas.py"),
                "split",
                str(enhanced_source),
                "--output-dir", str(enhanced_parts),
                "--axis", axis,
                "--segments", str(segments),
                "--manifest", str(atlas_root / "enhanced_split.json"),
            ]
            jobs.append(
                {
                    "stage": "atlas_split_enhanced",
                    "id": texture_id,
                    "argv": split_enhanced,
                    "command": _quoted_command(split_enhanced),
                }
            )

            for index in range(segments):
                part_name = f"part_{index:02d}.png"
                jobs.append(
                    _recreate_generate_job(
                        args,
                        entry,
                        classic_parts / part_name,
                        enhanced_parts / part_name,
                        generated_parts / part_name,
                        args.run_dir / "recreated_jobs" / f"{texture_id}_part_{index:02d}.job.json",
                        profiles,
                        model_args,
                        suffix=f"{index:02d}",
                    )
                )

            stitch = [
                sys.executable,
                str(ROOT / "tools/texture_lab/oa_tex_atlas.py"),
                "stitch",
                "--input-dir", str(generated_parts),
                "--output", str(final_output),
                "--axis", axis,
                "--segments", str(segments),
                "--manifest", str(atlas_root / "stitch.json"),
            ]
            jobs.append(
                {
                    "stage": "atlas_stitch",
                    "id": texture_id,
                    "argv": stitch,
                    "command": _quoted_command(stitch),
                }
            )
            continue

        conditioning = args.recreate_input_dir / texture_id / args.recreate_input_variant
        jobs.append(
            _recreate_generate_job(
                args,
                entry,
                args.source_dir / f"{texture_id}.png",
                conditioning,
                final_output,
                args.run_dir / "recreated_jobs" / f"{texture_id.replace('#', '_')}.job.json",
                profiles,
                model_args,
            )
        )

    review_ids = [str(entry["id"]) for entry in entries]
    technical_out = args.run_dir / "ai_recreated_validation.json"
    technical = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_validate.py"),
        "--source-dir", str(args.source_dir),
        "--candidate-dir", str(args.recreated_dir),
        "--variant", "selected.png",
        "--factor", str(args.factor),
        "--out", str(technical_out),
        "--only", *review_ids,
    ]
    jobs.append(
        {"stage": "technical_qa", "argv": technical, "command": _quoted_command(technical)}
    )

    drift_out = args.run_dir / "ai_recreated_structural_drift.json"
    qa = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_structural_drift.py"),
        "--source-dir", str(args.source_dir),
        "--candidate-dir", str(args.recreated_dir),
        "--variant", "selected.png",
        "--selection", str(args.selection),
        "--out", str(drift_out),
        "--allow-missing",
        "--only", *review_ids,
    ]
    jobs.append({"stage": "structural_qa", "argv": qa, "command": _quoted_command(qa)})

    review_json = args.run_dir / "ai_recreated_review_queue.json"
    review = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_report.py"),
        "recreated",
        "--drift", str(drift_out),
        "--selection", str(args.selection),
        "--technical", str(technical_out),
        "--out-json", str(review_json),
        "--out-md", str(args.run_dir / "ai_recreated_review_queue.md"),
        "--only", *review_ids,
    ]
    jobs.append({"stage": "review_queue", "argv": review, "command": _quoted_command(review)})

    review_pack = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_pack.py"),
        "recreated",
        "--review-queue", str(review_json),
        "--source-dir", str(args.source_dir),
        "--enhanced-dir", str(args.recreate_input_dir),
        "--recreated-dir", str(args.recreated_dir),
        "--out-dir", str(args.run_dir / "review_pack"),
        "--manifest", str(args.run_dir / "ai_recreated_review_pack.json"),
        "--markdown", str(args.run_dir / "ai_recreated_review_pack.md"),
    ]
    jobs.append(
        {"stage": "review_pack", "argv": review_pack, "command": _quoted_command(review_pack)}
    )
    return jobs

def build_local_preflight_job(args) -> dict | None:
    if not args.preset:
        return None
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_local_preflight.py"),
        "--preset", args.preset,
        "--out", str(args.run_dir / "local_preflight.json"),
    ]
    if args.mode == "restored":
        if args.realesrgan_root:
            argv.extend(["--realesrgan-root", str(args.realesrgan_root)])
        if args.model_path:
            argv.extend(["--model-path", str(args.model_path)])
        if args.realesrgan_python:
            argv.extend(["--realesrgan-python", str(args.realesrgan_python)])
    else:
        if args.comfy_root:
            argv.extend(["--comfy-root", str(args.comfy_root)])
        argv.extend(["--enhanced-variant", args.recreate_input_variant])
    return {
        "stage": "local_preflight",
        "argv": argv,
        "command": _quoted_command(argv),
    }


def build_stage_gate_job(args) -> dict | None:
    if not args.preset:
        return None
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_stage_gate.py"),
        "check",
        args.preset,
        "--run-root", str(args.run_root),
        "--out", str(args.run_dir / "stage_gate.json"),
    ]
    return {
        "stage": "stage_gate",
        "argv": argv,
        "command": _quoted_command(argv),
    }


def build_review_profile_job(args) -> dict | None:
    if not args.preset:
        return None
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_profile.py"),
        args.preset,
        "--run-root", str(args.run_root),
    ]
    return {
        "stage": "review_profile",
        "argv": argv,
        "command": _quoted_command(argv),
    }


def build_review_handoff_job(args) -> dict | None:
    if not args.preset:
        return None
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_handoff.py"),
        args.preset,
        "--run-root", str(args.run_root),
        "--out", str(args.run_dir / "review_handoff.html"),
    ]
    return {
        "stage": "review_handoff",
        "argv": argv,
        "command": _quoted_command(argv),
    }


def build_run_summary_job(args) -> dict | None:
    if not args.preset:
        return None
    argv = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_run_summary.py"),
        args.preset,
        "--run-root", str(args.run_root),
    ]
    return {
        "stage": "run_summary",
        "argv": argv,
        "command": _quoted_command(argv),
    }


def resolve_qwen_defaults(args, contract: dict) -> None:
    bindings = contract["canonical_openazrael_workflow"]["bindings"]
    if args.workflow is None:
        args.workflow = QWEN_WORKFLOW
    if args.load_image_node is None:
        args.load_image_node = str(bindings["load_image_node"])
    if args.prompt_node is None:
        args.prompt_node = str(bindings["prompt_node"])
    if args.negative_prompt_node is None:
        args.negative_prompt_node = str(bindings["negative_prompt_node"])
    if args.seed_node is None:
        args.seed_node = str(bindings["seed_node"])
    args.seed = int(contract["poc_sampling"]["seed"])


def resolve_named_candidate_namespace(args) -> None:
    if not args.preset:
        return

    if args.mode == "restored":
        canonical = named_candidate_root("restored", args.preset)
        if args.restored_dir not in {DEFAULT_RESTORED_DIR, canonical}:
            raise SystemExit(
                "named restored presets use a fixed preset-scoped candidate namespace: "
                f"{canonical}"
            )
        args.restored_dir = canonical
    else:
        canonical = named_candidate_root("recreated", args.preset)
        if args.recreated_dir not in {DEFAULT_RECREATED_DIR, canonical}:
            raise SystemExit(
                "named recreated presets use a fixed preset-scoped candidate namespace: "
                f"{canonical}"
            )
        args.recreated_dir = canonical


def prepare_run_storage(
    run_dir: Path,
    candidate_dir: Path,
    replace_existing: bool,
    dry_run: bool,
) -> dict:
    def has_content(path: Path) -> bool:
        return path.exists() and any(path.iterdir())

    run_has_content = has_content(run_dir)
    candidate_has_content = has_content(candidate_dir)
    existing = run_has_content or candidate_has_content

    if dry_run:
        if replace_existing:
            raise SystemExit("--replace-existing-run is not valid with --dry-run")
        return {
            "status": "DRY_RUN_NO_MUTATION",
            "run_dir_has_content": run_has_content,
            "candidate_dir_has_content": candidate_has_content,
        }

    if existing and not replace_existing:
        raise SystemExit(
            "named preset already has local run/candidate artifacts; refusing "
            "to mix a rerun with stale evidence. Review/backup the old local "
            "run, then rerun with --replace-existing-run to start clean."
        )

    if replace_existing:
        if run_dir.exists():
            shutil.rmtree(run_dir)
        if candidate_dir.exists():
            shutil.rmtree(candidate_dir)

    return {
        "status": "CLEAN",
        "run_dir_has_content_before": run_has_content,
        "candidate_dir_has_content_before": candidate_has_content,
        "replaced_existing": bool(replace_existing and existing),
    }


def prepare_named_run_storage(args) -> dict | None:
    if not args.preset:
        return None

    expected_run_dir = (args.run_root / args.preset).resolve()
    if args.run_dir.resolve() != expected_run_dir:
        raise SystemExit(
            "named preset run directory is not canonical: "
            f"actual={args.run_dir} expected={expected_run_dir}"
        )
    candidate_dir = (
        args.restored_dir if args.mode == "restored" else args.recreated_dir
    )
    expected_candidate = named_candidate_root(args.mode, args.preset).resolve()
    if candidate_dir.resolve() != expected_candidate:
        raise SystemExit(
            "named preset candidate directory is not canonical: "
            f"actual={candidate_dir} expected={expected_candidate}"
        )
    return prepare_run_storage(
        args.run_dir,
        candidate_dir,
        bool(args.replace_existing_run),
        bool(args.dry_run),
    )


def validate_named_preset_contract(
    args,
    qwen_contract: dict,
    backends: dict,
) -> None:
    if not args.preset:
        return

    common_paths = {
        "selection": (args.selection, CANONICAL_SELECTION),
        "policy": (args.policy, CANONICAL_POLICY),
        "profiles": (args.profiles, CANONICAL_PROFILES),
        "source_dir": (args.source_dir, CANONICAL_SOURCE_DIR),
    }
    common_path_failures = [
        name
        for name, (actual, expected_path) in common_paths.items()
        if Path(actual).resolve() != expected_path.resolve()
    ]
    if common_path_failures:
        raise SystemExit(
            "named preset repository inputs are canonical and cannot be "
            "overridden; mismatches=" + ",".join(common_path_failures)
        )

    if args.only:
        raise SystemExit("--only cannot be combined with a named preset")
    if args.model_file:
        raise SystemExit(
            "--model-file cannot extend the canonical model set of a named preset"
        )

    if args.mode == "restored":
        primary = backends["ai_restored"]["primary"]
        expected = {
            "restore_model": str(primary["model"]),
            "factor": int(primary["factor"]),
            "tile": int(primary["tile"]),
            "fp32": bool(primary["fp32"]),
        }
        actual = {
            "restore_model": args.restore_model,
            "factor": int(args.factor),
            "tile": int(args.tile),
            "fp32": bool(args.fp32),
        }
        if actual != expected:
            raise SystemExit(
                "named restored preset parameters are canonical and cannot be "
                f"overridden: expected={expected} actual={actual}"
            )
        if args.denoise_strength is not None:
            raise SystemExit(
                "named restored presets require denoise_strength=None for the "
                "primary RealESRGAN_x4plus baseline"
            )
        return

    bindings = qwen_contract["canonical_openazrael_workflow"]["bindings"]
    sampling = qwen_contract["poc_sampling"]
    primary = backends["ai_recreated"]["primary"]
    checks = {
        "workflow": args.workflow.resolve() == QWEN_WORKFLOW.resolve(),
        "model_label": args.model_label == str(primary["model_label"]),
        "seed": int(args.seed) == int(sampling["seed"]),
        "factor": int(args.factor) == 4,
        "conditioning_variant": args.recreate_input_variant == "lanczos_x4.png",
        "conditioning_dir": (
            args.recreate_input_dir.resolve()
            == CANONICAL_ENHANCED_DIR.resolve()
        ),
        "load_image_node": str(args.load_image_node) == str(bindings["load_image_node"]),
        "prompt_node": str(args.prompt_node) == str(bindings["prompt_node"]),
        "negative_prompt_node": (
            str(args.negative_prompt_node)
            == str(bindings["negative_prompt_node"])
        ),
        "seed_node": str(args.seed_node) == str(bindings["seed_node"]),
        "prompt_key": args.prompt_key == "prompt",
        "negative_prompt_key": args.negative_prompt_key == "prompt",
        "seed_key": args.seed_key == "seed",
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise SystemExit(
            "named recreated preset parameters are canonical and cannot be "
            "overridden; mismatches=" + ",".join(failed)
        )


def validate_execution_args(args) -> None:
    if args.dry_run:
        return
    if args.mode == "restored":
        if not args.realesrgan_root or not args.model_path:
            raise SystemExit("restored execution requires --realesrgan-root and --model-path")
        return

    if not args.workflow.is_file():
        raise SystemExit(f"Qwen API workflow not found: {args.workflow}")
    if args.comfy_root is None:
        raise SystemExit("recreated execution requires --comfy-root for exact model-file verification")
    if not args.recreate_input_dir.is_dir():
        raise SystemExit(
            f"recreated execution requires Enhanced conditioning directory: {args.recreate_input_dir}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or dry-run the canonical OpenAzrael AI texture bake-off.")
    parser.add_argument("mode", choices=["restored", "recreated"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace-existing-run",
        action="store_true",
        help=(
            "For a real named preset only: delete that preset's existing local "
            "run evidence and preset-scoped candidates before a clean rerun."
        ),
    )
    parser.add_argument("--preset", default=None, help="Named staged execution set from ai_smoke_sets.json.")
    parser.add_argument("--only", nargs="*", default=None, help="Explicit eligible texture IDs for this run.")
    parser.add_argument(
        "--selection",
        type=Path,
        default=CANONICAL_SELECTION,
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=CANONICAL_POLICY,
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=CANONICAL_PROFILES,
    )
    parser.add_argument("--source-dir", type=Path, default=CANONICAL_SOURCE_DIR)
    parser.add_argument("--restored-dir", type=Path, default=DEFAULT_RESTORED_DIR)
    parser.add_argument("--recreated-dir", type=Path, default=DEFAULT_RECREATED_DIR)
    parser.add_argument("--recreate-input-dir", type=Path, default=CANONICAL_ENHANCED_DIR)
    parser.add_argument("--recreate-input-variant", default="lanczos_x4.png")
    parser.add_argument("--run-dir", type=Path, default=ROOT / ".local/texture_lab/runs/rt_poc_01")
    parser.add_argument("--plan-out", type=Path, default=None)
    parser.add_argument("--factor", type=int, default=4)

    parser.add_argument("--realesrgan-root", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--realesrgan-python", default=sys.executable)
    parser.add_argument("--restore-model", default="RealESRGAN_x4plus")
    parser.add_argument("--tile", type=int, default=0)
    parser.add_argument("--fp32", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--denoise-strength", type=float, default=None)

    parser.add_argument("--workflow", type=Path, default=None)
    parser.add_argument("--comfy-root", type=Path, default=None)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--load-image-node", default=None)
    parser.add_argument("--prompt-node", default=None)
    parser.add_argument("--prompt-key", default="prompt")
    parser.add_argument("--negative-prompt-node", default=None)
    parser.add_argument("--negative-prompt-key", default="prompt")
    parser.add_argument("--seed-node", default=None)
    parser.add_argument("--seed-key", default="seed")
    parser.add_argument("--seed", type=int, default=734234)
    parser.add_argument("--model-label", default="Qwen-Image-Edit-2511")
    parser.add_argument("--model-file", type=Path, action="append", default=[])
    args = parser.parse_args()

    selection = load_json(args.selection)
    policy = load_json(args.policy)
    profiles = load_json(args.profiles)
    qwen_contract = load_json(QWEN_CONTRACT)
    backends = load_json(AI_BACKENDS)
    resolve_qwen_defaults(args, qwen_contract)
    validate_named_preset_contract(args, qwen_contract, backends)
    validate_execution_args(args)

    allowed, skipped = eligible_entries(selection, policy, args.mode)
    selected, deferred, preset_meta = apply_execution_subset(
        args.mode, allowed, args.preset, args.only
    )
    if not selected:
        raise SystemExit("execution subset contains no eligible textures")

    if args.preset:
        if args.run_dir.name == args.preset:
            args.run_root = args.run_dir.parent
        else:
            args.run_root = args.run_dir
            args.run_dir = args.run_root / args.preset
    else:
        args.run_root = args.run_dir

    resolve_named_candidate_namespace(args)
    storage_state = prepare_named_run_storage(args)

    if args.preset and args.plan_out is not None and not args.dry_run:
        raise SystemExit(
            "--plan-out is not allowed for a real named preset; "
            "the canonical plan path is part of the approval evidence."
        )

    if args.mode == "restored":
        jobs = build_restore_plan(args, selected)
    else:
        jobs = build_recreate_plan(args, selected, profiles, qwen_contract)

    prefix_jobs = []
    gate_job = build_stage_gate_job(args)
    if gate_job is not None:
        prefix_jobs.append(gate_job)
    local_preflight_job = build_local_preflight_job(args)
    if local_preflight_job is not None:
        prefix_jobs.append(local_preflight_job)
    jobs = prefix_jobs + jobs
    review_profile_job = build_review_profile_job(args)
    if review_profile_job is not None:
        jobs.append(review_profile_job)
    review_handoff_job = build_review_handoff_job(args)
    if review_handoff_job is not None:
        jobs.append(review_handoff_job)
    summary_job = build_run_summary_job(args)
    if summary_job is not None:
        jobs.append(summary_job)

    instance_id = run_instance_id(args.preset, args.dry_run)
    plan = {
        "schema": "openazrael.texture_lab.ai_bakeoff_plan.v5",
        "mode": args.mode,
        "dry_run": bool(args.dry_run),
        "run_instance_id": instance_id,
        "selection_count": len(selection["textures"]),
        "eligible_count": len(allowed),
        "selected_count": len(selected),
        "skipped_count": len(skipped),
        "deferred_count": len(deferred),
        "preset": preset_meta,
        "run_dir": str(args.run_dir),
        "candidate_namespace": (
            str(args.restored_dir)
            if args.mode == "restored"
            else str(args.recreated_dir)
        ),
        "candidate_namespace_policy": (
            "named_preset_scoped_v1"
            if args.preset
            else "ad_hoc_explicit"
        ),
        "parameter_policy": (
            "canonical_named_preset_v1"
            if args.preset
            else "ad_hoc_explicit"
        ),
        "run_storage_policy": (
            "clean_named_preset_v1"
            if args.preset
            else "ad_hoc_explicit"
        ),
        "run_storage_state": storage_state,
        "eligible": [
            {
                "id": entry["id"],
                "content_class": entry.get("content_class"),
                "policy": entry["policy"],
            }
            for entry in allowed
        ],
        "selected": [entry["id"] for entry in selected],
        "skipped": skipped,
        "deferred": deferred,
        "recreated_contract": (
            {
                "workflow": str(args.workflow),
                "conditioning_variant": args.recreate_input_variant,
                "seed": args.seed,
                "bindings": {
                    "load_image_node": args.load_image_node,
                    "prompt_node": args.prompt_node,
                    "negative_prompt_node": args.negative_prompt_node,
                    "seed_node": args.seed_node,
                },
            }
            if args.mode == "recreated"
            else None
        ),
        "jobs": [
            {key: value for key, value in job.items() if key != "argv"}
            for job in jobs
        ],
    }

    if args.plan_out is not None:
        plan_out = args.plan_out
    elif args.dry_run and args.preset:
        plan_out = (
            args.run_root
            / "_dry_run_plans"
            / f"{args.preset}_{args.mode}_plan.json"
        )
    else:
        plan_out = args.run_dir / f"{args.mode}_plan.json"
    write_json(plan_out, plan)
    print(
        f"PLAN mode={args.mode} eligible={len(allowed)} selected={len(selected)} "
        f"deferred={len(deferred)} skipped={len(skipped)} "
        f"jobs={len(jobs)} out={plan_out}"
    )

    if args.dry_run:
        for job in jobs:
            print(job["command"])
        return 0

    for job in jobs:
        print("RUN", job["stage"], job.get("id", ""), job["command"])
        subprocess.run(job["argv"], check=True)

    print(f"PASS ai_bakeoff mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
