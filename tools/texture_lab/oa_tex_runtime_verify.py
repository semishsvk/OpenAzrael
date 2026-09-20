#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json

EXPECTED_SCHEMA = "openazrael.texture_lab.runtime_texture_manifest.v1"
ALLOWED_PREFIX = "res://assets/textures/"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str, root: Path) -> Path:
    if value.startswith("res://"):
        return root / value[len("res://"):]
    return Path(value)


def safe_texture_path(value: str) -> bool:
    return (
        value.startswith(ALLOWED_PREFIX)
        and ".." not in value
        and value.endswith(".png")
    )


def verify_file_record(record: dict, root: Path) -> dict:
    value = str(record.get("path", ""))
    path = resolve_path(value, root)
    exists = path.is_file()
    expected_sha = record.get("sha256")
    expected_size = record.get("size_bytes")
    actual_sha = sha256_file(path) if exists else None
    actual_size = path.stat().st_size if exists else None
    return {
        "path": value,
        "exists": exists,
        "sha256_expected": expected_sha,
        "sha256_actual": actual_sha,
        "sha256_ok": bool(exists and expected_sha and actual_sha == expected_sha),
        "size_bytes_expected": expected_size,
        "size_bytes_actual": actual_size,
        "size_ok": bool(exists and expected_size is not None and actual_size == expected_size),
    }


def verify_manifest(manifest_path: Path, root: Path = ROOT) -> dict:
    if not manifest_path.is_file():
        return {
            "schema": "openazrael.texture_lab.runtime_manifest_verification.v1",
            "status": "HOLD",
            "reason": "manifest_missing",
            "manifest": str(manifest_path),
        }

    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "schema": "openazrael.texture_lab.runtime_manifest_verification.v1",
            "status": "HOLD",
            "reason": f"manifest_invalid_json:{type(exc).__name__}",
            "manifest": str(manifest_path),
        }

    schema_ok = manifest.get("schema") == EXPECTED_SCHEMA
    promotion_ok = manifest.get("automatic_promotion") is False
    profile = str(manifest.get("profile", ""))
    profile_ok = profile in {"classic", "enhanced", "remastered"}
    rows = manifest.get("textures")
    rows_ok = isinstance(rows, list)
    fatal = not (schema_ok and promotion_ok and profile_ok and rows_ok)

    declared_status = str(manifest.get("status", ""))
    declared_runtime_ready = manifest.get("runtime_ready") is True
    stale_selection_count = int(
        manifest.get("stale_production_selection_count", 0) or 0
    )
    allowed_ready_statuses = (
        {"READY", "SAFE_CLASSIC_FALLBACKS"}
        if profile == "remastered"
        else {"READY"}
    )

    input_checks = {}
    stale = False
    hold = fatal

    if not declared_runtime_ready:
        hold = True
    if declared_status in {"MISSING_FILES", "INTEGRITY_FAILURE"}:
        hold = True
    elif (
        declared_status == "SAFE_CLASSIC_FALLBACK_STALE_SELECTIONS"
        or stale_selection_count > 0
    ):
        stale = True
    elif declared_status not in allowed_ready_statuses:
        hold = True
    inputs = manifest.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
        hold = True

    for name in ["selection", "policy", "production_registry"]:
        record = inputs.get(name)
        if not isinstance(record, dict):
            input_checks[name] = {"status": "MISSING_RECORD"}
            hold = True
            continue
        check = verify_file_record(record, root)
        input_checks[name] = check
        if not check["exists"]:
            hold = True
        elif not check["sha256_ok"] or not check["size_ok"]:
            stale = True

    expected_selection_rows = []
    selection_record = inputs.get("selection") if isinstance(inputs, dict) else None
    if isinstance(selection_record, dict):
        selection_path = resolve_path(
            str(selection_record.get("path", "")),
            root,
        )
        if selection_path.is_file():
            try:
                selection_payload = load_json(selection_path)
                expected_selection_rows = [
                    row
                    for row in selection_payload.get("textures", [])
                    if isinstance(row, dict) and row.get("id")
                ]
            except (OSError, json.JSONDecodeError):
                hold = True

    expected_by_id = {
        str(row["id"]): row for row in expected_selection_rows
    }
    expected_ids = list(expected_by_id)

    texture_checks = []
    if rows_ok:
        for row in rows:
            if not isinstance(row, dict):
                texture_checks.append({"status": "INVALID_ROW"})
                hold = True
                continue

            texture_id = str(row.get("id", ""))
            value = str(row.get("path", ""))
            safe = safe_texture_path(value)
            path = resolve_path(value, root)
            exists = path.is_file() if safe else False
            actual_sha = sha256_file(path) if exists else None
            actual_size = path.stat().st_size if exists else None
            expected_sha = row.get("sha256")
            expected_size = row.get("size_bytes")
            hash_ok = bool(exists and expected_sha and actual_sha == expected_sha)
            size_ok = bool(exists and expected_size is not None and actual_size == expected_size)
            selection_expected = row.get("expected_selection_sha256")
            selection_hash_ok = (
                None
                if selection_expected is None
                else bool(actual_sha and selection_expected == actual_sha)
            )
            manifest_integrity_flag = row.get("integrity_ok") is True
            selection_entry = expected_by_id.get(texture_id)
            row_profile_ok = row.get("profile") == profile
            row_promotion_ok = row.get("automatic_promotion") is False
            expected_size_ok = bool(
                isinstance(selection_entry, dict)
                and row.get("expected_size")
                == selection_entry.get("expected_size")
            )

            check = {
                "id": texture_id,
                "path": value,
                "safe_path": safe,
                "exists": exists,
                "sha256_expected": expected_sha,
                "sha256_actual": actual_sha,
                "sha256_ok": hash_ok,
                "size_bytes_expected": expected_size,
                "size_bytes_actual": actual_size,
                "size_ok": size_ok,
                "selection_hash_ok": selection_hash_ok,
                "manifest_integrity_flag": manifest_integrity_flag,
                "row_profile_ok": row_profile_ok,
                "row_automatic_promotion_off": row_promotion_ok,
                "expected_size_ok": expected_size_ok,
                "resolution_reason": row.get("resolution_reason"),
                "resolved_tier": row.get("resolved_tier"),
                "production_selection_status": row.get(
                    "production_selection_status"
                ),
            }
            texture_checks.append(check)

            if (
                not texture_id
                or not safe
                or not exists
                or not row_profile_ok
                or not row_promotion_ok
                or not expected_size_ok
            ):
                hold = True
            elif not hash_ok or not size_ok:
                stale = True
            if selection_hash_ok is False:
                stale = True
            if not manifest_integrity_flag:
                stale = True

    row_ids = [
        str(row.get("id", ""))
        for row in rows
        if isinstance(row, dict)
    ] if rows_ok else []
    ids_unique = len(row_ids) == len(set(row_ids))
    selection_coverage_ok = (
        bool(expected_ids)
        and len(row_ids) == len(expected_ids)
        and set(row_ids) == set(expected_ids)
    )
    declared_texture_count_ok = manifest.get("texture_count") == len(row_ids)

    explicit_count = sum(
        1
        for row in rows
        if isinstance(row, dict)
        and row.get("resolution_reason")
        == "explicit_current_production_selection"
    ) if rows_ok else 0
    fallback_count = sum(
        1
        for row in rows
        if isinstance(row, dict)
        and "fallback_to_classic" in str(row.get("resolution_reason", ""))
    ) if rows_ok else 0
    stale_count = sum(
        1
        for row in rows
        if isinstance(row, dict)
        and row.get("production_selection_status") == "STALE"
    ) if rows_ok else 0
    missing_count = sum(
        1 for row in texture_checks if not row.get("exists")
    )
    integrity_failure_count = sum(
        1
        for row in texture_checks
        if row.get("manifest_integrity_flag") is False
        or row.get("selection_hash_ok") is False
    )
    declared_counts_ok = (
        manifest.get("explicit_production_selection_count") == explicit_count
        and manifest.get("classic_fallback_count") == fallback_count
        and manifest.get("stale_production_selection_count") == stale_count
        and manifest.get("missing_resolved_file_count") == missing_count
        and manifest.get("integrity_failure_count") == integrity_failure_count
    )

    if not (
        ids_unique
        and selection_coverage_ok
        and declared_texture_count_ok
        and declared_counts_ok
    ):
        hold = True

    status = "HOLD" if hold else ("STALE" if stale else "PASS")
    return {
        "schema": "openazrael.texture_lab.runtime_manifest_verification.v1",
        "status": status,
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            "size_bytes": manifest_path.stat().st_size,
            "schema_ok": schema_ok,
            "automatic_promotion_off": promotion_ok,
            "rows_ok": rows_ok,
            "profile": profile,
            "profile_ok": profile_ok,
            "declared_status": declared_status,
            "declared_runtime_ready": declared_runtime_ready,
            "stale_production_selection_count": stale_selection_count,
        },
        "inputs": input_checks,
        "textures": texture_checks,
        "texture_count": len(texture_checks),
        "coverage": {
            "expected_ids": expected_ids,
            "row_ids": row_ids,
            "ids_unique": ids_unique,
            "selection_coverage_ok": selection_coverage_ok,
            "declared_texture_count_ok": declared_texture_count_ok,
            "declared_counts_ok": declared_counts_ok,
            "computed_counts": {
                "explicit_production_selection_count": explicit_count,
                "classic_fallback_count": fallback_count,
                "stale_production_selection_count": stale_count,
                "missing_resolved_file_count": missing_count,
                "integrity_failure_count": integrity_failure_count,
            },
        },
        "stale_texture_ids": [
            row.get("id")
            for row in texture_checks
            if isinstance(row, dict)
            and (
                row.get("exists") is True
                and (
                    row.get("sha256_ok") is False
                    or row.get("size_ok") is False
                    or row.get("selection_hash_ok") is False
                    or row.get("manifest_integrity_flag") is False
                )
            )
        ],
        "missing_or_unsafe_texture_ids": [
            row.get("id")
            for row in texture_checks
            if isinstance(row, dict)
            and (
                row.get("safe_path") is False
                or row.get("exists") is False
                or not row.get("id")
            )
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify runtime texture-manifest inputs and every resolved texture hash."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = verify_manifest(args.manifest, args.root)
    if args.out:
        write_json(args.out, result)

    print(
        f"{result['status']} runtime_manifest_verify manifest={args.manifest} "
        f"textures={result.get('texture_count', 0)}"
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
