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
RUNTIME_CONTRACT = ROOT / "tools/texture_lab/config/realesrgan_runtime_contract.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_lock_candidate(
    preset: str,
    doctor: dict,
    runtime_contract: dict,
) -> dict:
    freeze = (
        doctor.get("runtime_contract", {}).get("pip_freeze")
        if isinstance(doctor.get("runtime_contract"), dict)
        else None
    )
    probe = (
        doctor.get("runtime_contract", {}).get("probe")
        if isinstance(doctor.get("runtime_contract"), dict)
        else None
    )
    torch_runtime = doctor.get("torch_runtime")
    checkpoint = doctor.get("checkpoint")

    checks = {
        "doctor_schema_ok": (
            doctor.get("schema")
            == "openazrael.texture_lab.realesrgan_doctor.v3"
        ),
        "doctor_ready": doctor.get("ready") is True,
        "runtime_contract_schema_ok": (
            doctor.get("runtime_contract", {}).get("schema")
            == runtime_contract.get("schema")
        ),
        "runtime_probe_pass": (
            isinstance(probe, dict)
            and probe.get("status") == "PASS"
        ),
        "pip_freeze_pass": (
            isinstance(freeze, dict)
            and freeze.get("status") == "PASS"
            and isinstance(freeze.get("sha256"), str)
            and bool(freeze.get("sha256"))
            and isinstance(freeze.get("packages"), list)
        ),
        "torch_runtime_pass": (
            isinstance(torch_runtime, dict)
            and torch_runtime.get("status") == "PASS"
        ),
        "source_identity_ok": (
            doctor.get("source_version_ok") is True
            and doctor.get("source_git_head_ok") is True
        ),
        "checkpoint_identity_ok": (
            isinstance(checkpoint, dict)
            and checkpoint.get("status") == "PASS"
            and isinstance(checkpoint.get("sha256"), str)
            and bool(checkpoint.get("sha256"))
        ),
    }

    status = "PASS" if all(checks.values()) else "HOLD"
    return {
        "schema": "openazrael.texture_lab.realesrgan_runtime_lock_candidate.v1",
        "status": status,
        "preset": preset,
        "automatic_promotion": False,
        "canonical_config_mutated": False,
        "checks": checks,
        "runtime_contract": {
            "schema": runtime_contract.get("schema"),
            "python_major_minor": runtime_contract.get("python", {}).get(
                "major_minor"
            ),
            "torch": runtime_contract.get("packages", {})
            .get("torch", {})
            .get("version"),
            "torchvision": runtime_contract.get("packages", {})
            .get("torchvision", {})
            .get("version"),
            "basicsr": runtime_contract.get("packages", {})
            .get("basicsr", {})
            .get("version"),
        },
        "observed": {
            "python": doctor.get("python"),
            "platform": doctor.get("platform"),
            "source_version": doctor.get("source_version"),
            "source_git_head": doctor.get("source_git_head"),
            "checkpoint": checkpoint,
            "torch_runtime": torch_runtime,
            "runtime_probe": probe,
            "pip_freeze": freeze,
        },
        "promotion_condition": (
            "human review of this candidate plus an explicit repository "
            "change to the canonical runtime lock; this tool never promotes it"
        ),
    }


def requirements_text(candidate: dict) -> str:
    freeze = candidate.get("observed", {}).get("pip_freeze", {})
    packages = freeze.get("packages", []) if isinstance(freeze, dict) else []
    if candidate.get("status") != "PASS" or not isinstance(packages, list):
        raise SystemExit("cannot write requirements lock from HOLD candidate")
    normalized = [str(row).strip() for row in packages if str(row).strip()]
    return "\n".join(normalized) + ("\n" if normalized else "")


def propose_lock(
    preset: str,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path,
    out_json: Path,
    out_requirements: Path,
) -> dict:
    if preset != "restored_smoke_1":
        raise SystemExit(
            "RT-POC-01 runtime lock candidate is currently defined only after "
            "restored_smoke_1"
        )

    receipt = validate_receipt(
        preset,
        run_root,
        approval_root,
        manual_review_root,
    )
    if receipt.get("status") != "PASS":
        raise SystemExit(
            "runtime lock candidate requires a current PASS stage approval; "
            f"status={receipt.get('status')}"
        )

    run_dir = run_root / preset
    doctor_path = run_dir / "realesrgan_doctor.json"
    if not doctor_path.is_file():
        raise SystemExit(f"Real-ESRGAN doctor evidence missing: {doctor_path}")

    candidate = build_lock_candidate(
        preset,
        load_json(doctor_path),
        load_json(RUNTIME_CONTRACT),
    )
    if candidate.get("status") != "PASS":
        raise SystemExit(
            "Real-ESRGAN doctor evidence is not sufficient for a runtime lock "
            "candidate"
        )

    candidate["approval"] = {
        "status": receipt.get("status"),
        "path": receipt.get("path"),
    }
    candidate["doctor_evidence"] = {
        "path": str(doctor_path),
        "sha256": sha256_file(doctor_path),
        "size_bytes": doctor_path.stat().st_size,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_requirements.parent.mkdir(parents=True, exist_ok=True)
    write_json(out_json, candidate)
    out_requirements.write_text(
        requirements_text(candidate),
        encoding="utf-8",
    )
    candidate["outputs"] = {
        "candidate_json": str(out_json),
        "requirements_lock": str(out_requirements),
    }
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local, non-promoting Real-ESRGAN runtime lock candidate "
            "after a current approved restored_smoke_1."
        )
    )
    parser.add_argument(
        "preset",
        nargs="?",
        default="restored_smoke_1",
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
        default=DEFAULT_LOCK_ROOT / "realesrgan_rt_poc_01_candidate.json",
    )
    parser.add_argument(
        "--out-requirements",
        type=Path,
        default=DEFAULT_LOCK_ROOT / "realesrgan_rt_poc_01_requirements.txt",
    )
    args = parser.parse_args()

    candidate = propose_lock(
        args.preset,
        args.run_root,
        args.approval_root,
        args.manual_review_root,
        args.out_json,
        args.out_requirements,
    )
    print(
        "PASS realesrgan_runtime_lock_candidate "
        f"preset={args.preset} json={args.out_json} "
        f"requirements={args.out_requirements}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
