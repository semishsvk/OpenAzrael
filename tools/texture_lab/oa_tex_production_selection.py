#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from common import (
    ROOT,
    named_candidate_root,
    path_is_within,
    sha256_file,
    write_json,
)
from oa_tex_stage_gate import (
    DEFAULT_APPROVAL_ROOT,
    DEFAULT_MANUAL_REVIEW_ROOT,
    DEFAULT_RUN_ROOT,
    file_evidence,
    preset_record,
    receipt_path,
    validate_receipt,
)

DEFAULT_REGISTRY = ROOT / "data/texture_lab/production_selection.json"
CURRENT_REGISTRY_SCHEMA = "openazrael.texture_lab.production_selection.v2"
LEGACY_REGISTRY_SCHEMA = "openazrael.texture_lab.production_selection.v1"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(path: Path) -> dict:
    if not path.is_file():
        return {
            "schema": CURRENT_REGISTRY_SCHEMA,
            "status": "NO_PRODUCTION_SELECTIONS",
            "automatic_selection": False,
            "profiles": {"remastered": {}},
            "superseded_selections": [],
            "revocations": [],
        }

    data = load_json(path)
    schema = data.get("schema")
    if schema not in {CURRENT_REGISTRY_SCHEMA, LEGACY_REGISTRY_SCHEMA}:
        raise SystemExit(f"unsupported production selection registry: {path}")

    if schema == LEGACY_REGISTRY_SCHEMA:
        data["schema"] = CURRENT_REGISTRY_SCHEMA
        data["migrated_from_schema"] = LEGACY_REGISTRY_SCHEMA

    data.setdefault("profiles", {}).setdefault("remastered", {})
    data.setdefault("superseded_selections", [])
    data.setdefault("revocations", [])
    return data


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    try:
        return str(resolved.relative_to(root)).replace("\\", "/")
    except ValueError as exc:
        raise SystemExit(
            f"production candidate must remain inside the project tree: {path}"
        ) from exc


def _review_pack_row(preset: str, texture_id: str, run_root: Path) -> tuple[dict, Path]:
    spec = preset_record(preset)
    mode = str(spec["mode"])
    manifest = run_root / preset / f"ai_{mode}_review_pack.json"
    if not manifest.is_file():
        raise SystemExit(f"review pack manifest not found: {manifest}")
    data = load_json(manifest)
    for row in data.get("rows", []):
        if isinstance(row, dict) and str(row.get("id")) == texture_id:
            return row, manifest
    raise SystemExit(
        f"texture {texture_id!r} is not present in the reviewed stage {preset!r}"
    )


def store_selection_record(
    registry: dict,
    texture_id: str,
    record: dict,
) -> None:
    profile = registry.setdefault("profiles", {}).setdefault("remastered", {})
    previous = profile.get(texture_id)
    if isinstance(previous, dict):
        registry.setdefault("superseded_selections", []).append(
            {
                "texture_id": texture_id,
                "superseded_at_utc": record.get("selected_at_utc"),
                "replaced_by": {
                    "selected_tier": record.get("selected_tier"),
                    "selected_from_preset": record.get("selected_from_preset"),
                    "candidate_sha256": record.get("candidate_sha256"),
                },
                "previous_selection": previous,
            }
        )
    profile[texture_id] = record
    registry["status"] = "HAS_EXPLICIT_PRODUCTION_SELECTIONS"


def select_candidate(
    preset: str,
    texture_id: str,
    registry_path: Path,
    run_root: Path,
    approval_root: Path,
    note: str,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    receipt_status = validate_receipt(
        preset,
        run_root,
        approval_root,
        manual_review_root,
    )
    if receipt_status.get("status") != "PASS":
        raise SystemExit(
            "production selection requires a current approved stage receipt; "
            f"preset={preset} status={receipt_status.get('status')}"
        )

    spec = preset_record(preset)
    mode = str(spec["mode"])
    if mode not in {"restored", "recreated"}:
        raise SystemExit(f"unsupported production selection mode: {mode}")

    row, review_manifest = _review_pack_row(preset, texture_id, run_root)
    candidate = row.get("candidate")
    source = row.get("source")
    if not isinstance(candidate, dict) or not isinstance(source, dict):
        raise SystemExit("review pack row does not contain source/candidate evidence")

    candidate_path = Path(str(candidate.get("path", "")))
    source_path = Path(str(source.get("path", "")))
    expected_root = named_candidate_root(mode, preset)
    if not path_is_within(candidate_path, expected_root):
        raise SystemExit(
            "reviewed candidate is outside the preset-scoped named-stage namespace; "
            f"candidate={candidate_path} expected_root={expected_root}"
        )
    if not candidate_path.is_file() or not source_path.is_file():
        raise SystemExit("reviewed source/candidate files are no longer present")

    current_candidate = file_evidence(candidate_path)
    current_source = file_evidence(source_path)
    if current_candidate != candidate:
        raise SystemExit("reviewed candidate changed after review-pack generation")
    if current_source != source:
        raise SystemExit("Classic source changed after review-pack generation")

    receipt_file = receipt_path(preset, approval_root)
    registry = load_registry(registry_path)
    selected_at = datetime.now(timezone.utc).isoformat()

    record = {
        "texture_id": texture_id,
        "presentation_profile": "remastered",
        "selected_tier": "ai_restored" if mode == "restored" else "ai_recreated",
        "selected_from_preset": preset,
        "selected_at_utc": selected_at,
        "manual_note": note,
        "candidate_path": project_relative(candidate_path),
        "candidate_sha256": current_candidate["sha256"],
        "candidate_size_bytes": current_candidate["size_bytes"],
        "classic_source_path": project_relative(source_path),
        "classic_source_sha256": current_source["sha256"],
        "review_pack_manifest": file_evidence(review_manifest),
        "stage_approval_receipt": file_evidence(receipt_file),
        "automatic_selection": False,
    }
    store_selection_record(registry, texture_id, record)
    write_json(registry_path, registry)
    return record


def validate_record(
    record: dict,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    preset = str(record.get("selected_from_preset", ""))
    texture_id = str(record.get("texture_id", ""))
    checks = {}

    receipt = validate_receipt(
        preset,
        run_root,
        approval_root,
        manual_review_root,
    )
    checks["stage_approval_current"] = receipt.get("status") == "PASS"

    candidate_path = ROOT / str(record.get("candidate_path", ""))
    source_path = ROOT / str(record.get("classic_source_path", ""))
    mode = str(preset_record(preset).get("mode", ""))
    expected_root = named_candidate_root(mode, preset)
    checks["candidate_namespace_current"] = path_is_within(
        candidate_path,
        expected_root,
    )
    checks["candidate_present"] = candidate_path.is_file()
    checks["source_present"] = source_path.is_file()
    checks["candidate_hash_current"] = (
        candidate_path.is_file()
        and sha256_file(candidate_path) == record.get("candidate_sha256")
    )
    checks["source_hash_current"] = (
        source_path.is_file()
        and sha256_file(source_path) == record.get("classic_source_sha256")
    )

    try:
        review_row, review_manifest = _review_pack_row(preset, texture_id, run_root)
        current_candidate = review_row.get("candidate")
        current_source = review_row.get("source")
        checks["review_pack_candidate_matches_selection"] = (
            isinstance(current_candidate, dict)
            and current_candidate.get("sha256") == record.get("candidate_sha256")
        )
        checks["review_pack_source_matches_selection"] = (
            isinstance(current_source, dict)
            and current_source.get("sha256") == record.get("classic_source_sha256")
        )
        stored_manifest = record.get("review_pack_manifest")
        checks["review_pack_manifest_current"] = (
            isinstance(stored_manifest, dict)
            and file_evidence(review_manifest) == stored_manifest
        )
    except SystemExit:
        checks["review_pack_candidate_matches_selection"] = False
        checks["review_pack_source_matches_selection"] = False
        checks["review_pack_manifest_current"] = False

    receipt_file = receipt_path(preset, approval_root)
    stored_receipt = record.get("stage_approval_receipt")
    checks["approval_receipt_file_current"] = (
        receipt_file.is_file()
        and isinstance(stored_receipt, dict)
        and file_evidence(receipt_file) == stored_receipt
    )

    return {
        "texture_id": texture_id,
        "status": "PASS" if all(checks.values()) else "STALE",
        "checks": checks,
    }


def registry_status(
    registry_path: Path,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    registry = load_registry(registry_path)
    profile = registry["profiles"]["remastered"]
    rows = [
        validate_record(
            record,
            run_root,
            approval_root,
            manual_review_root,
        )
        for _, record in sorted(profile.items())
        if isinstance(record, dict)
    ]
    return {
        "schema": "openazrael.texture_lab.production_selection_status.v1",
        "registry": str(registry_path),
        "selection_count": len(rows),
        "status": (
            "EMPTY"
            if not rows
            else ("PASS" if all(row["status"] == "PASS" for row in rows) else "STALE")
        ),
        "rows": rows,
    }


def revoke_candidate(
    texture_id: str,
    registry_path: Path,
    note: str,
) -> dict:
    registry = load_registry(registry_path)
    profile = registry["profiles"]["remastered"]
    previous = profile.pop(texture_id, None)
    if previous is None:
        raise SystemExit(f"no remastered production selection exists for {texture_id}")
    registry["status"] = (
        "HAS_EXPLICIT_PRODUCTION_SELECTIONS"
        if profile
        else "NO_PRODUCTION_SELECTIONS"
    )
    registry.setdefault("revocations", []).append(
        {
            "texture_id": texture_id,
            "revoked_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": note,
            "previous_selection": previous,
        }
    )
    write_json(registry_path, registry)
    return previous


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Explicit production-selection registry for reviewed OpenAzrael "
            "Texture Lab candidates. Never selects or copies pixels automatically."
        )
    )
    parser.add_argument("command", choices=["select", "status", "revoke"])
    parser.add_argument("texture_id", nargs="?")
    parser.add_argument("--preset", default=None)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--approval-root", type=Path, default=DEFAULT_APPROVAL_ROOT)
    parser.add_argument(
        "--manual-review-root",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_ROOT,
    )
    parser.add_argument("--note", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "select":
        if not args.texture_id or not args.preset:
            parser.error("select requires texture_id and --preset")
        if not args.note:
            parser.error("select requires --note documenting the manual production decision")
        result = select_candidate(
            args.preset,
            args.texture_id,
            args.registry,
            args.run_root,
            args.approval_root,
            args.note,
            args.manual_review_root,
        )
        status = "PASS"
    elif args.command == "revoke":
        if not args.texture_id:
            parser.error("revoke requires texture_id")
        if not args.note:
            parser.error("revoke requires --note")
        result = revoke_candidate(args.texture_id, args.registry, args.note)
        status = "PASS"
    else:
        result = registry_status(
            args.registry,
            args.run_root,
            args.approval_root,
            args.manual_review_root,
        )
        status = str(result["status"])

    if args.out:
        write_json(args.out, result)

    print(
        f"{status} production_selection command={args.command} "
        f"texture={args.texture_id or '-'} registry={args.registry}"
    )
    if args.command == "status":
        return 0 if status in {"PASS", "EMPTY"} else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
