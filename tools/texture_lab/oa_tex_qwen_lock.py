#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json
from oa_tex_stage_gate import (
    DEFAULT_APPROVAL_ROOT,
    DEFAULT_MANUAL_REVIEW_ROOT,
    DEFAULT_RUN_ROOT,
    validate_receipt,
)

DEFAULT_LOCK_ROOT = ROOT / ".local/texture_lab/runtime_locks"
QWEN_CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_record(path: Path) -> dict:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def build_qwen_lock_candidate(
    preset: str,
    comfy_doctor: dict,
    qwen_preflight: dict,
    contract: dict,
    job_records: list[dict],
) -> dict:
    system = comfy_doctor.get("system")
    model_files = qwen_preflight.get("model_files")
    sampling = qwen_preflight.get("sampling_check")
    bindings = qwen_preflight.get("canonical_bindings")

    model_files_ok = (
        isinstance(model_files, dict)
        and bool(model_files)
        and all(
            isinstance(row, dict) and row.get("status") == "PASS"
            for row in model_files.values()
        )
    )
    system_identity_ok = (
        isinstance(system, dict)
        and isinstance(system.get("python_version"), str)
        and bool(system.get("python_version"))
        and isinstance(system.get("pytorch_version"), str)
        and bool(system.get("pytorch_version"))
        and isinstance(system.get("comfyui_version"), str)
        and bool(system.get("comfyui_version"))
    )
    jobs_ok = (
        bool(job_records)
        and all(
            row.get("schema")
            == "openazrael.texture_lab.ai_recreated_job.v5"
            for row in job_records
        )
    )

    checks = {
        "preset_ok": preset == "recreated_smoke_1",
        "comfy_doctor_schema_ok": (
            comfy_doctor.get("schema")
            == "openazrael.texture_lab.comfy_doctor.v1"
        ),
        "comfy_ready": comfy_doctor.get("ready") is True,
        "system_identity_ok": system_identity_ok,
        "qwen_preflight_schema_ok": (
            qwen_preflight.get("schema")
            == "openazrael.texture_lab.qwen_2511_preflight.v2"
        ),
        "qwen_ready": qwen_preflight.get("ready_for_execution") is True,
        "model_files_required": (
            qwen_preflight.get("model_files_required") is True
        ),
        "model_files_ok": model_files_ok,
        "workflow_hash_present": (
            isinstance(qwen_preflight.get("workflow_sha256"), str)
            and bool(qwen_preflight.get("workflow_sha256"))
        ),
        "bindings_present": isinstance(bindings, dict) and bool(bindings),
        "sampling_pass": (
            isinstance(sampling, dict)
            and sampling.get("status") == "PASS"
        ),
        "job_records_v5": jobs_ok,
    }

    return {
        "schema": "openazrael.texture_lab.qwen_runtime_lock_candidate.v1",
        "status": "PASS" if all(checks.values()) else "HOLD",
        "preset": preset,
        "automatic_promotion": False,
        "canonical_config_mutated": False,
        "checks": checks,
        "contract": {
            "schema": contract.get("schema"),
            "model_label": contract.get("model_label"),
            "official_template": contract.get("official_template"),
            "poc_sampling": contract.get("poc_sampling"),
        },
        "observed": {
            "server": comfy_doctor.get("server"),
            "system": system,
            "node_contract": comfy_doctor.get("node_contract"),
            "workflow": qwen_preflight.get("workflow"),
            "workflow_sha256": qwen_preflight.get("workflow_sha256"),
            "canonical_bindings": bindings,
            "sampling_check": sampling,
            "model_files": model_files,
            "jobs": [
                {
                    "schema": row.get("schema"),
                    "prompt_id": row.get("prompt_id"),
                    "workflow_template_sha256":
                        row.get("workflow_template_sha256"),
                    "model_label": row.get("model_label"),
                    "seed": row.get("seed"),
                    "model_files": row.get("model_files"),
                    "performance": row.get("performance"),
                }
                for row in job_records
            ],
        },
        "promotion_condition": (
            "human review of this candidate plus an explicit repository "
            "change; this tool never promotes it"
        ),
    }


def propose_lock(
    preset: str,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path,
    out_json: Path,
) -> dict:
    if preset != "recreated_smoke_1":
        raise SystemExit(
            "RT-POC-01 Qwen runtime lock candidate is currently defined only "
            "after recreated_smoke_1"
        )

    receipt = validate_receipt(
        preset,
        run_root,
        approval_root,
        manual_review_root,
    )
    if receipt.get("status") != "PASS":
        raise SystemExit(
            "Qwen runtime lock candidate requires a current PASS stage "
            f"approval; status={receipt.get('status')}"
        )

    run_dir = run_root / preset
    comfy_path = run_dir / "comfy_doctor.json"
    qwen_path = run_dir / "qwen_preflight.json"
    if not comfy_path.is_file() or not qwen_path.is_file():
        raise SystemExit(
            "Qwen runtime lock candidate requires current Comfy doctor and "
            "Qwen preflight evidence"
        )

    job_paths = sorted((run_dir / "recreated_jobs").glob("*.job.json"))
    if not job_paths:
        raise SystemExit("Qwen runtime lock candidate requires job evidence")

    candidate = build_qwen_lock_candidate(
        preset,
        load_json(comfy_path),
        load_json(qwen_path),
        load_json(QWEN_CONTRACT),
        [load_json(path) for path in job_paths],
    )
    if candidate.get("status") != "PASS":
        raise SystemExit(
            "Comfy/Qwen evidence is not sufficient for a runtime lock candidate"
        )

    approval_path = Path(str(receipt["path"]))
    candidate["approval"] = {
        "status": "PASS",
        "path": str(approval_path),
        "sha256": sha256_file(approval_path),
        "size_bytes": approval_path.stat().st_size,
    }
    candidate["evidence"] = {
        "comfy_doctor": file_record(comfy_path),
        "qwen_preflight": file_record(qwen_path),
        "jobs": [file_record(path) for path in job_paths],
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_json(out_json, candidate)
    candidate["output"] = str(out_json)
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local, non-promoting ComfyUI/Qwen runtime lock candidate "
            "after a current approved recreated_smoke_1."
        )
    )
    parser.add_argument(
        "preset",
        nargs="?",
        default="recreated_smoke_1",
    )
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--approval-root",
        type=Path,
        default=DEFAULT_APPROVAL_ROOT,
    )
    parser.add_argument(
        "--manual-review-root",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_ROOT,
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=DEFAULT_LOCK_ROOT / "qwen_2511_rt_poc_01_candidate.json",
    )
    args = parser.parse_args()

    result = propose_lock(
        args.preset,
        args.run_root,
        args.approval_root,
        args.manual_review_root,
        args.out_json,
    )
    print(
        "PASS qwen_runtime_lock_candidate "
        f"preset={args.preset} json={args.out_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
