#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json
from oa_tex_stage_gate import DEFAULT_RUN_ROOT, file_evidence, preset_record

DEFAULT_MANUAL_REVIEW_ROOT = ROOT / ".local/texture_lab/manual_reviews/rt_poc_01"

BASE_CHECKS = [
    "composition_geometry_preserved",
    "no_invented_objects_symbols_or_text",
    "material_detail_plausible",
    "detail_artifacts_acceptable",
    "alpha_mask_boundaries_acceptable",
    "gameplay_scale_acceptable",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mode_for(preset: str) -> str:
    return str(preset_record(preset)["mode"])


def record_path(preset: str, review_root: Path) -> Path:
    return review_root / f"{preset}.json"


def review_pack_path(preset: str, run_root: Path) -> Path:
    mode = mode_for(preset)
    return run_root / preset / f"ai_{mode}_review_pack.json"


def review_queue_path(preset: str, run_root: Path) -> Path:
    mode = mode_for(preset)
    return run_root / preset / f"ai_{mode}_review_queue.json"


def required_checks_for(review_row: dict, pack_row: dict) -> list[str]:
    checks = list(BASE_CHECKS)
    attention = [str(value) for value in review_row.get("attention", [])]

    if isinstance(pack_row.get("tile_preview"), dict):
        checks.append("repeat_seams_acceptable")
    if any("manual_text_review:" in value for value in attention):
        checks.append("text_character_and_layout_exact")
    if any("manual_artwork_review:" in value for value in attention):
        checks.append("artwork_figures_objects_preserved")
    if any("manual_geometry_review:" in value for value in attention):
        checks.append("special_geometry_preserved")
    if any("atlas_" in value for value in attention):
        checks.append("atlas_boundaries_preserved")
    if any("alpha" in value for value in attention):
        checks.append("alpha_policy_satisfied")
    return list(dict.fromkeys(checks))


def build_template(preset: str, run_root: Path) -> dict:
    pack_path = review_pack_path(preset, run_root)
    queue_path = review_queue_path(preset, run_root)
    if not pack_path.is_file() or not queue_path.is_file():
        raise SystemExit(
            "manual review init requires completed review pack and queue; "
            f"pack={pack_path} queue={queue_path}"
        )

    pack = load_json(pack_path)
    queue = load_json(queue_path)
    pack_by_id = {
        str(row["id"]): row
        for row in pack.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    }
    queue_rows = [
        row for row in queue.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    ]
    expected = [str(value) for value in preset_record(preset).get("textures", [])]
    queue_by_id = {str(row["id"]): row for row in queue_rows}

    if set(pack_by_id) != set(expected) or set(queue_by_id) != set(expected):
        raise SystemExit(
            "manual review init refused: queue/pack IDs do not match preset"
        )

    rows = []
    for texture_id in expected:
        review_row = queue_by_id[texture_id]
        pack_row = pack_by_id[texture_id]
        required = required_checks_for(review_row, pack_row)
        candidate = pack_row.get("candidate")
        if not isinstance(candidate, dict):
            raise SystemExit(f"{texture_id}: missing candidate evidence")
        rows.append(
            {
                "id": texture_id,
                "decision": "PENDING",
                "required_checks": required,
                "checks": {name: None for name in required},
                "note": None,
                "candidate": candidate,
                "attention": list(review_row.get("attention", [])),
            }
        )

    return {
        "schema": "openazrael.texture_lab.manual_review.v1",
        "preset": preset,
        "mode": mode_for(preset),
        "status": "PENDING_MANUAL_REVIEW",
        "automatic_approval": False,
        "review_pack": file_evidence(pack_path),
        "review_queue": file_evidence(queue_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }


def init_review(
    preset: str,
    run_root: Path,
    review_root: Path,
    replace: bool = False,
) -> dict:
    path = record_path(preset, review_root)
    if path.exists() and not replace:
        raise SystemExit(
            f"manual review already exists: {path}; use --replace only to restart review"
        )
    payload = build_template(preset, run_root)
    review_root.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)
    return payload


def parse_check(value: str) -> tuple[str, bool]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("check must use NAME=true|false")
    name, raw = value.split("=", 1)
    normalized = raw.strip().lower()
    if normalized not in {"true", "false", "yes", "no", "1", "0"}:
        raise argparse.ArgumentTypeError("check value must be true or false")
    return name.strip(), normalized in {"true", "yes", "1"}


def record_texture(
    preset: str,
    texture_id: str,
    decision: str,
    checks: list[tuple[str, bool]],
    note: str | None,
    review_root: Path,
) -> dict:
    path = record_path(preset, review_root)
    if not path.is_file():
        raise SystemExit(f"manual review not initialized: {path}")
    payload = load_json(path)
    rows = payload.get("rows", [])
    row = next(
        (
            value
            for value in rows
            if isinstance(value, dict) and str(value.get("id")) == texture_id
        ),
        None,
    )
    if row is None:
        raise SystemExit(f"texture {texture_id!r} is not part of manual review {preset}")

    valid_decisions = {"ACCEPTED_FOR_STAGE", "HOLD", "REJECTED"}
    if decision not in valid_decisions:
        raise SystemExit(f"unsupported manual review decision: {decision}")

    required = set(str(value) for value in row.get("required_checks", []))
    supplied_names = set()
    for name, value in checks:
        if name not in required:
            raise SystemExit(
                f"{texture_id}: unknown/non-required check {name!r}; "
                f"required={sorted(required)}"
            )
        row["checks"][name] = bool(value)
        supplied_names.add(name)

    if decision == "ACCEPTED_FOR_STAGE":
        missing = [
            name
            for name in sorted(required)
            if row.get("checks", {}).get(name) is not True
        ]
        if missing:
            raise SystemExit(
                f"{texture_id}: ACCEPTED_FOR_STAGE requires every check=true; "
                f"missing_or_false={missing}"
            )
    elif not note:
        raise SystemExit(f"{texture_id}: {decision} requires --note")

    row["decision"] = decision
    row["note"] = note
    row["reviewed_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(path, payload)
    return row


def validate_manual_review(
    preset: str,
    run_root: Path,
    review_root: Path,
) -> dict:
    path = record_path(preset, review_root)
    if not path.is_file():
        return {
            "status": "MISSING",
            "preset": preset,
            "path": str(path),
        }

    payload = load_json(path)
    pack_path = review_pack_path(preset, run_root)
    queue_path = review_queue_path(preset, run_root)
    if not pack_path.is_file() or not queue_path.is_file():
        return {
            "status": "STALE",
            "preset": preset,
            "path": str(path),
            "reason": "current review pack/queue missing",
        }

    expected = [str(value) for value in preset_record(preset).get("textures", [])]
    rows = [
        row for row in payload.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    ]
    ids = [str(row["id"]) for row in rows]

    evidence_current = (
        payload.get("review_pack") == file_evidence(pack_path)
        and payload.get("review_queue") == file_evidence(queue_path)
    )
    row_results = []
    for row in rows:
        required = [str(value) for value in row.get("required_checks", [])]
        checks = row.get("checks", {})
        all_checks_true = (
            isinstance(checks, dict)
            and all(checks.get(name) is True for name in required)
        )
        accepted = row.get("decision") == "ACCEPTED_FOR_STAGE"
        candidate = row.get("candidate")
        candidate_current = False
        if isinstance(candidate, dict):
            candidate_path = Path(str(candidate.get("path", "")))
            candidate_current = (
                candidate_path.is_file()
                and file_evidence(candidate_path) == candidate
            )
        row_results.append(
            {
                "id": str(row["id"]),
                "accepted": accepted,
                "all_required_checks_true": all_checks_true,
                "candidate_current": candidate_current,
                "status": (
                    "PASS"
                    if accepted and all_checks_true and candidate_current
                    else "HOLD"
                ),
            }
        )

    ids_ok = len(ids) == len(expected) and set(ids) == set(expected)
    candidates_current = (
        len(row_results) == len(expected)
        and all(row["candidate_current"] for row in row_results)
    )
    rows_pass = len(row_results) == len(expected) and all(
        row["status"] == "PASS" for row in row_results
    )
    if not evidence_current or not candidates_current:
        status = "STALE"
    elif ids_ok and rows_pass:
        status = "PASS"
    else:
        status = "HOLD"

    return {
        "status": status,
        "preset": preset,
        "path": str(path),
        "record": file_evidence(path),
        "ids_ok": ids_ok,
        "evidence_current": evidence_current,
        "candidates_current": candidates_current,
        "rows": row_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Structured per-texture manual review required before Texture Lab "
            "stage approval."
        )
    )
    parser.add_argument("command", choices=["init", "record", "status"])
    parser.add_argument("preset")
    parser.add_argument("texture_id", nargs="?")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--review-root",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_ROOT,
    )
    parser.add_argument("--replace", action="store_true")
    parser.add_argument(
        "--decision",
        choices=["ACCEPTED_FOR_STAGE", "HOLD", "REJECTED"],
        default=None,
    )
    parser.add_argument(
        "--check",
        action="append",
        type=parse_check,
        default=[],
        help="Repeat NAME=true|false for required review checks.",
    )
    parser.add_argument("--note", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "init":
        result = init_review(
            args.preset,
            args.run_root,
            args.review_root,
            args.replace,
        )
        status = result["status"]
    elif args.command == "record":
        if not args.texture_id or not args.decision:
            parser.error("record requires texture_id and --decision")
        result = record_texture(
            args.preset,
            args.texture_id,
            args.decision,
            args.check,
            args.note,
            args.review_root,
        )
        status = result["decision"]
    else:
        result = validate_manual_review(
            args.preset,
            args.run_root,
            args.review_root,
        )
        status = result["status"]

    if args.out:
        write_json(args.out, result)

    print(
        f"{status} manual_review command={args.command} "
        f"preset={args.preset} texture={args.texture_id or '-'}"
    )
    if args.command == "status":
        return 0 if status == "PASS" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
