#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json

DEFAULT_CANDIDATE = (
    ROOT / ".local/texture_lab/runtime_locks/qwen_2511_rt_poc_01_candidate.json"
)
DEFAULT_OUT_DIR = ROOT / ".local/texture_lab/runtime_locks/qwen_promotion_plan"
QWEN_CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
QWEN_WORKFLOW = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
TARGET_LOCK = ROOT / "tools/texture_lab/config/qwen_environment_lock.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_files_match_contract(
    observed: dict,
    contract: dict,
) -> bool:
    required = contract.get("required_models", {})
    if not isinstance(observed, dict) or set(observed) != set(required):
        return False
    for role, spec in required.items():
        row = observed.get(role)
        if not isinstance(row, dict):
            return False
        if row.get("status") != "PASS":
            return False
        if str(row.get("sha256", "")).lower() != str(spec.get("sha256", "")).lower():
            return False
        if int(row.get("size_bytes", -1)) != int(spec.get("size_bytes", -2)):
            return False
        expected_path = str(spec.get("relative_path", ""))
        if expected_path and not str(row.get("path", "")).replace("\\", "/").endswith(
            expected_path.replace("\\", "/")
        ):
            return False
    return True


def candidate_compatibility(
    candidate: dict,
    contract: dict,
    canonical_workflow_sha256: str,
) -> dict:
    observed = candidate.get("observed", {})
    jobs = observed.get("jobs", [])
    sampling = contract.get("poc_sampling", {})
    expected_seed = sampling.get("seed")
    checks = {
        "candidate_schema_ok": (
            candidate.get("schema")
            == "openazrael.texture_lab.qwen_runtime_lock_candidate.v1"
        ),
        "candidate_pass": candidate.get("status") == "PASS",
        "preset_ok": candidate.get("preset") == "recreated_smoke_1",
        "automatic_promotion_off": candidate.get("automatic_promotion") is False,
        "canonical_config_not_mutated": (
            candidate.get("canonical_config_mutated") is False
        ),
        "contract_schema_ok": (
            candidate.get("contract", {}).get("schema")
            == contract.get("schema")
        ),
        "model_label_ok": (
            candidate.get("contract", {}).get("model_label")
            == contract.get("model_label")
        ),
        "workflow_hash_ok": (
            observed.get("workflow_sha256") == canonical_workflow_sha256
        ),
        "model_files_ok": model_files_match_contract(
            observed.get("model_files", {}),
            contract,
        ),
        "system_identity_ok": (
            isinstance(observed.get("system"), dict)
            and bool(observed["system"].get("python_version"))
            and bool(observed["system"].get("pytorch_version"))
            and bool(observed["system"].get("comfyui_version"))
        ),
        "job_records_present": isinstance(jobs, list) and bool(jobs),
        "job_contract_ok": (
            isinstance(jobs, list)
            and bool(jobs)
            and all(
                isinstance(row, dict)
                and row.get("schema")
                == "openazrael.texture_lab.ai_recreated_job.v5"
                and row.get("model_label") == contract.get("model_label")
                and row.get("seed") == expected_seed
                and row.get("workflow_template_sha256")
                == canonical_workflow_sha256
                for row in jobs
            )
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "HOLD",
        "checks": checks,
    }


def build_environment_lock(
    candidate: dict,
    candidate_sha256: str,
) -> dict:
    return {
        "schema": "openazrael.texture_lab.qwen_environment_lock.v1",
        "status": "PROPOSED_FROM_APPROVED_REAL_SMOKE",
        "source_preset": candidate.get("preset"),
        "source_candidate_sha256": candidate_sha256,
        "automatic_promotion": False,
        "human_promotion_required": True,
        "contract": candidate.get("contract"),
        "observed": candidate.get("observed"),
        "provenance": {
            "approval": candidate.get("approval"),
            "evidence": candidate.get("evidence"),
        },
    }


def build_promotion_plan(
    candidate: dict,
    candidate_sha256: str,
    contract: dict,
    canonical_workflow_sha256: str,
) -> dict:
    compatibility = candidate_compatibility(
        candidate,
        contract,
        canonical_workflow_sha256,
    )
    if compatibility["status"] != "PASS":
        return {
            "schema": "openazrael.texture_lab.qwen_lock_promotion_plan.v1",
            "status": "HOLD",
            "automatic_promotion": False,
            "compatibility": compatibility,
        }

    lock = build_environment_lock(candidate, candidate_sha256)
    lock_text = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    return {
        "schema": "openazrael.texture_lab.qwen_lock_promotion_plan.v1",
        "status": "READY_FOR_HUMAN_PROMOTION_REVIEW",
        "automatic_promotion": False,
        "canonical_files_mutated": False,
        "compatibility": compatibility,
        "source_candidate_sha256": candidate_sha256,
        "proposed_files": [
            {
                "target": str(TARGET_LOCK.relative_to(ROOT)),
                "sha256": text_sha256(lock_text),
                "content_kind": "json",
            }
        ],
        "review_requirements": [
            "confirm recreated_smoke_1 is the intended approved calibration run",
            "confirm ComfyUI/Python/PyTorch runtime identity",
            "confirm canonical Qwen workflow SHA-256 and bindings",
            "confirm all pinned model file SHA-256/size identities",
            "confirm fixed sampling contract and submitted job seeds/model labels",
            "review GPU/device provenance before repository promotion",
        ],
        "_rendered": {"environment_lock": lock_text},
    }


def write_plan_artifacts(plan: dict, out_dir: Path) -> dict:
    if plan.get("status") != "READY_FOR_HUMAN_PROMOTION_REVIEW":
        raise SystemExit("cannot render Qwen promotion files from HOLD plan")

    rendered = plan.pop("_rendered")
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "promotion_plan.json"
    lock_path = out_dir / "qwen_environment_lock.json"
    lock_path.write_text(
        rendered["environment_lock"],
        encoding="utf-8",
    )
    plan["local_proposed_files"] = {
        "promotion_plan": str(plan_path),
        "environment_lock": str(lock_path),
    }
    write_json(plan_path, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a local, non-mutating repository promotion proposal from "
            "an approved ComfyUI/Qwen runtime lock candidate."
        )
    )
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--contract", type=Path, default=QWEN_CONTRACT)
    parser.add_argument("--workflow", type=Path, default=QWEN_WORKFLOW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not args.candidate.is_file():
        raise SystemExit(f"Qwen runtime lock candidate missing: {args.candidate}")

    candidate = load_json(args.candidate)
    plan = build_promotion_plan(
        candidate,
        sha256_file(args.candidate),
        load_json(args.contract),
        sha256_file(args.workflow),
    )
    if plan.get("status") != "READY_FOR_HUMAN_PROMOTION_REVIEW":
        print("HOLD qwen_lock_promotion_plan")
        return 1

    result = write_plan_artifacts(plan, args.out_dir)
    print(
        "PASS qwen_lock_promotion_plan "
        f"out={result['local_proposed_files']['promotion_plan']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
