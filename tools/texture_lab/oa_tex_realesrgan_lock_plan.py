#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json

DEFAULT_CANDIDATE = (
    ROOT
    / ".local/texture_lab/runtime_locks/realesrgan_rt_poc_01_candidate.json"
)
DEFAULT_OUT_DIR = ROOT / ".local/texture_lab/runtime_locks/promotion_plan"
RUNTIME_CONTRACT = ROOT / "tools/texture_lab/config/realesrgan_runtime_contract.json"

TARGET_LOCK = ROOT / "tools/texture_lab/config/realesrgan_environment_lock.json"
TARGET_REQUIREMENTS = (
    ROOT / "tools/texture_lab/requirements-realesrgan-lock.txt"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_requirements(packages: list[object]) -> str:
    rows = sorted(
        str(row).strip()
        for row in packages
        if str(row).strip()
    )
    return "\n".join(rows) + ("\n" if rows else "")


def candidate_compatibility(
    candidate: dict,
    runtime_contract: dict,
) -> dict:
    observed = candidate.get("observed", {})
    probe = observed.get("runtime_probe", {})
    probe_observed = (
        probe.get("observed", {})
        if isinstance(probe, dict)
        else {}
    )
    contract = candidate.get("runtime_contract", {})
    expected_packages = runtime_contract.get("packages", {})

    checks = {
        "candidate_schema_ok": (
            candidate.get("schema")
            == "openazrael.texture_lab.realesrgan_runtime_lock_candidate.v1"
        ),
        "candidate_pass": candidate.get("status") == "PASS",
        "automatic_promotion_off": (
            candidate.get("automatic_promotion") is False
        ),
        "canonical_config_not_mutated": (
            candidate.get("canonical_config_mutated") is False
        ),
        "preset_ok": candidate.get("preset") == "restored_smoke_1",
        "contract_schema_ok": (
            contract.get("schema") == runtime_contract.get("schema")
        ),
        "python_ok": (
            str(contract.get("python_major_minor"))
            == str(runtime_contract.get("python", {}).get("major_minor"))
            == str(probe_observed.get("python_major_minor"))
        ),
        "torch_ok": (
            str(contract.get("torch"))
            == str(expected_packages.get("torch", {}).get("version"))
            == str(probe_observed.get("torch"))
        ),
        "torchvision_ok": (
            str(contract.get("torchvision"))
            == str(expected_packages.get("torchvision", {}).get("version"))
            == str(probe_observed.get("torchvision"))
        ),
        "basicsr_ok": (
            str(contract.get("basicsr"))
            == str(expected_packages.get("basicsr", {}).get("version"))
            == str(probe_observed.get("basicsr"))
        ),
        "runtime_probe_pass": (
            isinstance(probe, dict)
            and probe.get("status") == "PASS"
        ),
        "pip_freeze_pass": (
            isinstance(observed.get("pip_freeze"), dict)
            and observed["pip_freeze"].get("status") == "PASS"
            and isinstance(observed["pip_freeze"].get("packages"), list)
            and isinstance(observed["pip_freeze"].get("sha256"), str)
            and bool(observed["pip_freeze"].get("sha256"))
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
    observed = candidate["observed"]
    freeze = observed["pip_freeze"]
    return {
        "schema": "openazrael.texture_lab.realesrgan_environment_lock.v1",
        "status": "PROPOSED_FROM_APPROVED_REAL_SMOKE",
        "source_preset": candidate["preset"],
        "source_candidate_sha256": candidate_sha256,
        "automatic_promotion": False,
        "human_promotion_required": True,
        "python": observed.get("python"),
        "platform": observed.get("platform"),
        "source_version": observed.get("source_version"),
        "source_git_head": observed.get("source_git_head"),
        "checkpoint": observed.get("checkpoint"),
        "torch_runtime": observed.get("torch_runtime"),
        "runtime_probe": observed.get("runtime_probe"),
        "pip_freeze": {
            "status": freeze.get("status"),
            "package_count": freeze.get("package_count"),
            "sha256": freeze.get("sha256"),
            "packages": freeze.get("packages"),
        },
        "provenance": {
            "doctor_evidence": candidate.get("doctor_evidence"),
            "approval": candidate.get("approval"),
        },
    }


def build_promotion_plan(
    candidate: dict,
    candidate_sha256: str,
    runtime_contract: dict,
) -> dict:
    compatibility = candidate_compatibility(candidate, runtime_contract)
    if compatibility["status"] != "PASS":
        return {
            "schema": "openazrael.texture_lab.realesrgan_lock_promotion_plan.v1",
            "status": "HOLD",
            "automatic_promotion": False,
            "compatibility": compatibility,
        }

    lock = build_environment_lock(candidate, candidate_sha256)
    lock_text = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    requirements = normalize_requirements(
        candidate["observed"]["pip_freeze"]["packages"]
    )

    return {
        "schema": "openazrael.texture_lab.realesrgan_lock_promotion_plan.v1",
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
            },
            {
                "target": str(TARGET_REQUIREMENTS.relative_to(ROOT)),
                "sha256": text_sha256(requirements),
                "content_kind": "requirements",
            },
        ],
        "proposed_runtime_contract_update": {
            "dependency_policy.current_environment_lock_status":
                "VALIDATED_BY_APPROVED_REAL_SMOKE",
            "dependency_policy.final_lock_promotion_condition":
                "explicit human-reviewed repository promotion from the "
                "approved runtime-lock candidate",
        },
        "review_requirements": [
            "confirm the approved restored_smoke_1 is the intended calibration run",
            "confirm Python/Torch/torchvision/BasicSR versions still match the provisional contract",
            "confirm source commit and model checkpoint identity",
            "confirm CUDA/GPU/platform metadata are acceptable as reference provenance",
            "inspect the exact pip-freeze package list before repository promotion",
        ],
        "_rendered": {
            "environment_lock": lock_text,
            "requirements_lock": requirements,
        },
    }


def write_plan_artifacts(
    plan: dict,
    out_dir: Path,
) -> dict:
    if plan.get("status") != "READY_FOR_HUMAN_PROMOTION_REVIEW":
        raise SystemExit("cannot render promotion files from HOLD plan")

    rendered = plan.pop("_rendered")
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "promotion_plan.json"
    lock_path = out_dir / "realesrgan_environment_lock.json"
    requirements_path = out_dir / "requirements-realesrgan-lock.txt"

    lock_path.write_text(
        rendered["environment_lock"],
        encoding="utf-8",
    )
    requirements_path.write_text(
        rendered["requirements_lock"],
        encoding="utf-8",
    )
    plan["local_proposed_files"] = {
        "promotion_plan": str(plan_path),
        "environment_lock": str(lock_path),
        "requirements_lock": str(requirements_path),
    }
    write_json(plan_path, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a local, non-mutating repository promotion proposal from "
            "an approved Real-ESRGAN runtime lock candidate."
        )
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=DEFAULT_CANDIDATE,
    )
    parser.add_argument(
        "--runtime-contract",
        type=Path,
        default=RUNTIME_CONTRACT,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
    )
    args = parser.parse_args()

    if not args.candidate.is_file():
        raise SystemExit(f"runtime lock candidate missing: {args.candidate}")

    candidate = load_json(args.candidate)
    plan = build_promotion_plan(
        candidate,
        sha256_file(args.candidate),
        load_json(args.runtime_contract),
    )
    if plan.get("status") != "READY_FOR_HUMAN_PROMOTION_REVIEW":
        print("HOLD realesrgan_lock_promotion_plan")
        return 1

    result = write_plan_artifacts(plan, args.out_dir)
    print(
        "PASS realesrgan_lock_promotion_plan "
        f"out={result['local_proposed_files']['promotion_plan']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
