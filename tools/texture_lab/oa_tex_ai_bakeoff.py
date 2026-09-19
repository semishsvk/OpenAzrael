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


def _quoted_command(argv: list[str]) -> str:
    import shlex
    return shlex.join(argv)


def build_restore_plan(args, entries: list[dict]) -> list[dict]:
    ids = [str(entry["id"]) for entry in entries]
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

    qa = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_structural_drift.py"),
        "--source-dir", str(args.source_dir),
        "--candidate-dir", str(args.restored_dir),
        "--variant", f"realesrgan_x{args.factor}.png",
        "--selection", str(args.selection),
        "--out", str(args.run_dir / "ai_restored_structural_drift.json"),
        "--allow-missing",
    ]
    return [
        {"stage": "generate", "argv": argv, "command": _quoted_command(argv)},
        {"stage": "structural_qa", "argv": qa, "command": _quoted_command(qa)},
    ]


def required_qwen_model_files(comfy_root: Path | None, contract: dict) -> list[Path]:
    if comfy_root is None:
        return []
    return [
        comfy_root / str(spec["relative_path"])
        for spec in contract["required_models"].values()
    ]


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
        prompts = build_prompt_pair(profiles, str(entry["content_class"]))
        output = args.recreated_dir / texture_id / "selected.png"
        conditioning = args.recreate_input_dir / texture_id / args.recreate_input_variant
        job_record = args.run_dir / "recreated_jobs" / f"{texture_id.replace('#', '_')}.job.json"

        argv = [
            sys.executable,
            str(ROOT / "tools/texture_lab/oa_tex_recreate.py"),
            str(args.source_dir / f"{texture_id}.png"),
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
        jobs.append(
            {
                "stage": "generate",
                "id": texture_id,
                "content_class": entry.get("content_class"),
                "conditioning_image": str(conditioning),
                "policy": entry["policy"],
                "argv": argv,
                "command": _quoted_command(argv),
            }
        )

    qa = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_structural_drift.py"),
        "--source-dir", str(args.source_dir),
        "--candidate-dir", str(args.recreated_dir),
        "--variant", "selected.png",
        "--selection", str(args.selection),
        "--out", str(args.run_dir / "ai_recreated_structural_drift.json"),
        "--allow-missing",
    ]
    jobs.append({"stage": "structural_qa", "argv": qa, "command": _quoted_command(qa)})
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
    parser.add_argument("--run-dir", type=Path, default=ROOT / "data/texture_lab/runs/rt_poc_01")
    parser.add_argument("--plan-out", type=Path, default=None)
    parser.add_argument("--factor", type=int, default=4)

    parser.add_argument("--realesrgan-root", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
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
    if args.mode == "restored":
        jobs = build_restore_plan(args, allowed)
    else:
        jobs = build_recreate_plan(args, allowed, profiles, qwen_contract)

    plan = {
        "schema": "openazrael.texture_lab.ai_bakeoff_plan.v2",
        "mode": args.mode,
        "dry_run": bool(args.dry_run),
        "selection_count": len(selection["textures"]),
        "eligible_count": len(allowed),
        "skipped_count": len(skipped),
        "eligible": [
            {
                "id": entry["id"],
                "content_class": entry.get("content_class"),
                "policy": entry["policy"],
            }
            for entry in allowed
        ],
        "skipped": skipped,
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
        f"PLAN mode={args.mode} eligible={len(allowed)} skipped={len(skipped)} "
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
