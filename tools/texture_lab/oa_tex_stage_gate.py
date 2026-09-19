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


def output_path(mode: str, texture_id: str) -> Path:
    if mode == "restored":
        return ROOT / "assets/textures/ai_restored" / texture_id / "realesrgan_x4.png"
    return ROOT / "assets/textures/ai_recreated" / texture_id / "selected.png"


def evidence_snapshot(preset: str, run_root: Path) -> dict:
    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_dir_for(preset, run_root)
    plan = run_dir / plan_filename(mode)
    review = run_dir / review_filename(mode)

    missing = [str(path) for path in [plan, review] if not path.is_file()]
    output_rows = []
    for texture_id in spec.get("textures", []):
        path = output_path(mode, str(texture_id))
        if not path.is_file():
            missing.append(str(path))
            continue
        output_rows.append(
            {
                "id": str(texture_id),
                "path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
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
    selected = [str(value) for value in plan_data.get("selected", [])]
    expected = [str(value) for value in spec.get("textures", [])]
    review_ids = [str(row.get("id")) for row in review_data.get("rows", [])]

    checks = {
        "plan_preset_ok": (
            isinstance(plan_data.get("preset"), dict)
            and plan_data["preset"].get("name") == preset
        ),
        "selected_ids_ok": selected == expected,
        "review_ids_ok": (
            len(review_ids) == len(expected)
            and set(review_ids) == set(expected)
        ),
        "review_complete_ok": all(
            row.get("review_state") == "MANUAL_REVIEW_REQUIRED"
            for row in review_data.get("rows", [])
        ) and len(review_ids) == len(expected),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "preset": preset,
        "mode": mode,
        "run_dir": str(run_dir),
        "plan": {
            "path": str(plan),
            "sha256": sha256_file(plan),
        },
        "review": {
            "path": str(review),
            "sha256": sha256_file(review),
        },
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

    checks = {
        "plan_hash_ok": receipt.get("evidence", {}).get("plan", {}).get("sha256")
        == current["plan"]["sha256"],
        "review_hash_ok": receipt.get("evidence", {}).get("review", {}).get("sha256")
        == current["review"]["sha256"],
        "outputs_ok": receipt.get("evidence", {}).get("outputs") == current["outputs"],
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
        "schema": "openazrael.texture_lab.stage_approval.v1",
        "preset": preset,
        "mode": evidence["mode"],
        "decision": "APPROVED_FOR_NEXT_STAGE",
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "evidence": {
            "plan": evidence["plan"],
            "review": evidence["review"],
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
