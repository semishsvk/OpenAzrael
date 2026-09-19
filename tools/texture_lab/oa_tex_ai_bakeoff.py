#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from common import ROOT, write_json
from oa_tex_prompt import build_prompt_pair

QWEN_CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
QWEN_WORKFLOW = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
SMOKE_SETS = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"


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
    ]
    review = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_report.py"),
        "restored",
        "--drift", str(drift_out),
        "--selection", str(args.selection),
        "--out-json", str(args.run_dir / "ai_restored_review_queue.json"),
        "--out-md", str(args.run_dir / "ai_restored_review_queue.md"),
    ]
    return [
        {"stage": "realesrgan_doctor", "argv": doctor, "command": _quoted_command(doctor)},
        {"stage": "generate", "argv": argv, "command": _quoted_command(argv)},
        {"stage": "structural_qa", "argv": qa, "command": _quoted_command(qa)},
        {"stage": "review_queue", "argv": review, "command": _quoted_command(review)},
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
    ]
    jobs.append({"stage": "structural_qa", "argv": qa, "command": _quoted_command(qa)})

    review = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_review_report.py"),
        "recreated",
        "--drift", str(drift_out),
        "--selection", str(args.selection),
        "--out-json", str(args.run_dir / "ai_recreated_review_queue.json"),
        "--out-md", str(args.run_dir / "ai_recreated_review_queue.md"),
    ]
    jobs.append({"stage": "review_queue", "argv": review, "command": _quoted_command(review)})
    return jobs

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
    parser.add_argument("--preset", default=None, help="Named staged execution set from ai_smoke_sets.json.")
    parser.add_argument("--only", nargs="*", default=None, help="Explicit eligible texture IDs for this run.")
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "tools/texture_lab/config/ai_review_policy.json",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=ROOT / "tools/texture_lab/profiles/recreate_profiles.json",
    )
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--restored-dir", type=Path, default=ROOT / "assets/textures/ai_restored")
    parser.add_argument("--recreated-dir", type=Path, default=ROOT / "assets/textures/ai_recreated")
    parser.add_argument("--recreate-input-dir", type=Path, default=ROOT / "assets/textures/enhanced")
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
    resolve_qwen_defaults(args, qwen_contract)
    validate_execution_args(args)

    allowed, skipped = eligible_entries(selection, policy, args.mode)
    selected, deferred, preset_meta = apply_execution_subset(
        args.mode, allowed, args.preset, args.only
    )
    if not selected:
        raise SystemExit("execution subset contains no eligible textures")

    if args.mode == "restored":
        jobs = build_restore_plan(args, selected)
    else:
        jobs = build_recreate_plan(args, selected, profiles, qwen_contract)

    plan = {
        "schema": "openazrael.texture_lab.ai_bakeoff_plan.v2",
        "mode": args.mode,
        "dry_run": bool(args.dry_run),
        "selection_count": len(selection["textures"]),
        "eligible_count": len(allowed),
        "selected_count": len(selected),
        "skipped_count": len(skipped),
        "deferred_count": len(deferred),
        "preset": preset_meta,
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

    plan_out = args.plan_out or args.run_dir / f"{args.mode}_plan.json"
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
