#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json

SMOKE_SETS = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"
DEFAULT_RUN_ROOT = ROOT / ".local/texture_lab/runs/rt_poc_01"
DEFAULT_APPROVAL_ROOT = ROOT / ".local/texture_lab/approvals/rt_poc_01"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def preset_record(name: str) -> dict:
    cfg = load_json(SMOKE_SETS)
    preset = cfg.get("presets", {}).get(name)
    if not isinstance(preset, dict):
        raise SystemExit(f"unknown AI smoke preset: {name}")
    return preset


def run_dir_for(preset: str, run_root: Path) -> Path:
    return run_root / preset


def review_filename(mode: str) -> str:
    return f"ai_{mode}_review_queue.json"


def plan_filename(mode: str) -> str:
    return f"{mode}_plan.json"


def technical_filename(mode: str) -> str:
    return f"ai_{mode}_validation.json"


def structural_filename(mode: str) -> str:
    return f"ai_{mode}_structural_drift.json"


def output_path(mode: str, texture_id: str) -> Path:
    if mode == "restored":
        return ROOT / "assets/textures/ai_restored" / texture_id / "realesrgan_x4.png"
    return ROOT / "assets/textures/ai_recreated" / texture_id / "selected.png"


def file_evidence(path: Path) -> dict:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def runtime_evidence_paths(mode: str, run_dir: Path) -> list[Path]:
    common = [
        run_dir / "local_preflight.json",
        run_dir / "stage_gate.json",
    ]
    if mode == "restored":
        return common + [
            run_dir / "realesrgan_doctor.json",
            run_dir / "ai_restore_run.json",
        ]
    return common + [
        run_dir / "comfy_doctor.json",
        run_dir / "qwen_preflight.json",
    ]


def recreated_job_records(run_dir: Path) -> list[Path]:
    jobs = sorted((run_dir / "recreated_jobs").glob("*.job.json"))
    atlases = sorted((run_dir / "atlas_parts").glob("**/*.json"))
    return jobs + atlases


def evidence_snapshot(preset: str, run_root: Path) -> dict:
    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_dir_for(preset, run_root)

    plan = run_dir / plan_filename(mode)
    review = run_dir / review_filename(mode)
    technical = run_dir / technical_filename(mode)
    structural = run_dir / structural_filename(mode)
    runtime_paths = runtime_evidence_paths(mode, run_dir)

    required = [plan, review, technical, structural, *runtime_paths]
    missing = [str(path) for path in required if not path.is_file()]

    job_paths: list[Path] = []
    if mode == "recreated":
        job_paths = recreated_job_records(run_dir)
        if not job_paths:
            missing.append(str(run_dir / "recreated_jobs/*.job.json"))

    output_rows = []
    for texture_id in spec.get("textures", []):
        path = output_path(mode, str(texture_id))
        if not path.is_file():
            missing.append(str(path))
            continue
        output_rows.append(
            {
                "id": str(texture_id),
                **file_evidence(path),
            }
        )

    if missing:
        return {
            "status": "MISSING",
            "preset": preset,
            "mode": mode,
            "missing": missing,
        }

    plan_data = load_json(plan)
    review_data = load_json(review)
    technical_data = load_json(technical)
    local_preflight = load_json(run_dir / "local_preflight.json")
    stage_gate = load_json(run_dir / "stage_gate.json")

    selected = [str(value) for value in plan_data.get("selected", [])]
    expected = [str(value) for value in spec.get("textures", [])]
    review_rows = [
        row for row in review_data.get("rows", []) if isinstance(row, dict)
    ]
    review_ids = [str(row.get("id")) for row in review_rows]
    technical_rows = [
        row for row in technical_data.get("results", []) if isinstance(row, dict)
    ]
    technical_ids = [str(row.get("id")) for row in technical_rows]

    checks = {
        "plan_preset_ok": (
            isinstance(plan_data.get("preset"), dict)
            and plan_data["preset"].get("name") == preset
            and plan_data.get("dry_run") is False
        ),
        "selected_ids_ok": selected == expected,
        "review_ids_ok": (
            len(review_ids) == len(expected)
            and set(review_ids) == set(expected)
        ),
        "review_complete_ok": (
            len(review_rows) == len(expected)
            and all(
                row.get("review_state") == "MANUAL_REVIEW_REQUIRED"
                for row in review_rows
            )
        ),
        "technical_ids_ok": (
            len(technical_ids) == len(expected)
            and set(technical_ids) == set(expected)
        ),
        "technical_pass_ok": (
            technical_data.get("technical_failures") == 0
            and all(
                row.get("technical_status") == "PASS"
                for row in technical_rows
            )
        ),
        "local_preflight_ok": local_preflight.get("ready_for_runtime_doctors") is True,
        "stage_prerequisites_ok": stage_gate.get("status") == "PASS",
    }

    if mode == "restored":
        doctor = load_json(run_dir / "realesrgan_doctor.json")
        restore_run = load_json(run_dir / "ai_restore_run.json")
        checks["runtime_doctor_ok"] = doctor.get("ready") is True
        checks["generation_record_ok"] = (
            len(restore_run.get("textures", [])) == len(expected)
            and {
                str(row.get("id"))
                for row in restore_run.get("textures", [])
                if isinstance(row, dict)
            } == set(expected)
        )
    else:
        comfy = load_json(run_dir / "comfy_doctor.json")
        qwen = load_json(run_dir / "qwen_preflight.json")
        checks["runtime_doctor_ok"] = comfy.get("ready") is True
        checks["qwen_preflight_ok"] = qwen.get("ready_for_execution") is True
        checks["generation_records_present"] = bool(job_paths)

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "preset": preset,
        "mode": mode,
        "run_dir": str(run_dir),
        "plan": file_evidence(plan),
        "review": file_evidence(review),
        "technical": file_evidence(technical),
        "structural": file_evidence(structural),
        "runtime": [file_evidence(path) for path in runtime_paths],
        "generation_records": [file_evidence(path) for path in job_paths],
        "outputs": output_rows,
        "checks": checks,
    }


def receipt_path(preset: str, approval_root: Path) -> Path:
    return approval_root / f"{preset}.json"


def validate_receipt(preset: str, run_root: Path, approval_root: Path) -> dict:
    path = receipt_path(preset, approval_root)
    if not path.is_file():
        return {"status": "MISSING", "preset": preset, "path": str(path)}

    receipt = load_json(path)
    current = evidence_snapshot(preset, run_root)
    if current.get("status") != "PASS":
        return {
            "status": "STALE",
            "preset": preset,
            "path": str(path),
            "reason": "current evidence is incomplete or invalid",
            "current": current,
        }

    old = receipt.get("evidence", {})
    checks = {
        "plan_hash_ok": old.get("plan") == current["plan"],
        "review_hash_ok": old.get("review") == current["review"],
        "technical_hash_ok": old.get("technical") == current["technical"],
        "structural_hash_ok": old.get("structural") == current["structural"],
        "runtime_ok": old.get("runtime") == current["runtime"],
        "generation_records_ok": (
            old.get("generation_records") == current["generation_records"]
        ),
        "outputs_ok": old.get("outputs") == current["outputs"],
        "approved_ok": receipt.get("decision") == "APPROVED_FOR_NEXT_STAGE",
    }
    return {
        "status": "PASS" if all(checks.values()) else "STALE",
        "preset": preset,
        "path": str(path),
        "checks": checks,
    }


def check_prerequisites(preset: str, run_root: Path, approval_root: Path) -> dict:
    spec = preset_record(preset)
    required = [str(v) for v in spec.get("requires_approval", [])]
    rows = [
        validate_receipt(previous, run_root, approval_root)
        for previous in required
    ]
    return {
        "preset": preset,
        "requires_approval": required,
        "receipts": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "HOLD",
    }


def approve(
    preset: str,
    run_root: Path,
    approval_root: Path,
    note: str | None,
) -> dict:
    evidence = evidence_snapshot(preset, run_root)
    if evidence.get("status") != "PASS":
        raise SystemExit(
            "cannot approve stage: run evidence is incomplete or inconsistent; "
            f"status={evidence.get('status')}"
        )

    approval_root.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "openazrael.texture_lab.stage_approval.v2",
        "preset": preset,
        "mode": evidence["mode"],
        "decision": "APPROVED_FOR_NEXT_STAGE",
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "evidence": {
            "plan": evidence["plan"],
            "review": evidence["review"],
            "technical": evidence["technical"],
            "structural": evidence["structural"],
            "runtime": evidence["runtime"],
            "generation_records": evidence["generation_records"],
            "outputs": evidence["outputs"],
        },
    }
    path = receipt_path(preset, approval_root)
    write_json(path, receipt)
    return {"status": "PASS", "path": str(path), "receipt": receipt}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manual approval gate between staged OpenAzrael AI texture runs."
    )
    parser.add_argument("command", choices=["check", "approve", "status"])
    parser.add_argument("preset")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--approval-root", type=Path, default=DEFAULT_APPROVAL_ROOT)
    parser.add_argument("--note", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "check":
        result = check_prerequisites(args.preset, args.run_root, args.approval_root)
    elif args.command == "status":
        result = validate_receipt(args.preset, args.run_root, args.approval_root)
    else:
        result = approve(args.preset, args.run_root, args.approval_root, args.note)

    if args.out:
        write_json(args.out, result)

    print(
        f"{result.get('status', 'HOLD')} stage_gate "
        f"command={args.command} preset={args.preset}"
    )
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
