#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from common import ROOT, sha256_file, write_json
from oa_tex_production_selection import DEFAULT_REGISTRY, load_registry, validate_record
from oa_tex_stage_gate import DEFAULT_APPROVAL_ROOT, DEFAULT_RUN_ROOT

DEFAULT_SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
DEFAULT_POLICY = ROOT / "tools/texture_lab/config/ai_review_policy.json"
DEFAULT_OUTPUT_ROOT = ROOT / ".local/texture_lab/runtime_manifests"
ENHANCED_METHODS = {"nearest", "bicubic", "lanczos"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def res_path(project_relative: str) -> str:
    normalized = project_relative.replace("\\", "/").lstrip("/")
    return "res://" + normalized


def classic_path(texture_id: str) -> str:
    return f"res://assets/textures/classic/{texture_id}.png"


def enhanced_method_for(entry: dict, policy: dict, requested: str) -> str:
    if requested not in ENHANCED_METHODS:
        raise ValueError(f"unsupported Enhanced method: {requested}")
    content_class = str(entry.get("content_class", ""))
    class_policy = policy.get("classes", {}).get(content_class, {})
    if class_policy.get("preferred_tier") == "enhanced_nearest":
        return "nearest"
    return requested


def enhanced_path(texture_id: str, method: str) -> str:
    return f"res://assets/textures/enhanced/{texture_id}/{method}_x4.png"


def resolved_file_fields(path: str, root: Path = ROOT) -> dict:
    if not path.startswith("res://"):
        return {
            "file_present": False,
            "sha256": None,
            "size_bytes": None,
        }
    resolved = root / path[len("res://"):]
    present = resolved.is_file()
    return {
        "file_present": present,
        "sha256": sha256_file(resolved) if present else None,
        "size_bytes": resolved.stat().st_size if present else None,
    }


def portable_input_path(path: Path, root: Path = ROOT) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve())
        return "res://" + str(relative).replace("\\", "/")
    except ValueError:
        return str(path)


def input_file_record(path: Path, root: Path = ROOT) -> dict:
    present = path.is_file()
    return {
        "path": portable_input_path(path, root),
        "present": present,
        "sha256": sha256_file(path) if present else None,
        "size_bytes": path.stat().st_size if present else None,
    }


def resolve_entry(
    profile: str,
    entry: dict,
    policy: dict,
    production_record: dict | None,
    production_status: dict | None,
    enhanced_method: str,
    root: Path = ROOT,
) -> dict:
    texture_id = str(entry["id"])
    base = {
        "id": texture_id,
        "room": entry.get("room"),
        "content_class": entry.get("content_class"),
        "expected_size": entry.get("expected_size"),
        "profile": profile,
        "automatic_promotion": False,
    }

    if profile == "classic":
        path = classic_path(texture_id)
        return {
            **base,
            "resolved_tier": "classic",
            "path": path,
            "resolution_reason": "classic_profile",
            **resolved_file_fields(path, root),
        }

    if profile == "enhanced":
        method = enhanced_method_for(entry, policy, enhanced_method)
        path = enhanced_path(texture_id, method)
        return {
            **base,
            "resolved_tier": f"enhanced_{method}",
            "path": path,
            "resolution_reason": (
                "policy_forced_nearest"
                if method != enhanced_method
                else "requested_deterministic_enhanced"
            ),
            **resolved_file_fields(path, root),
        }

    if profile != "remastered":
        raise ValueError(f"unsupported profile: {profile}")

    if production_record is not None and production_status is not None:
        if production_status.get("status") == "PASS":
            candidate = str(production_record["candidate_path"])
            path = res_path(candidate)
            return {
                **base,
                "resolved_tier": str(production_record["selected_tier"]),
                "path": path,
                "resolution_reason": "explicit_current_production_selection",
                "production_preset": production_record.get("selected_from_preset"),
                "production_selection_status": "PASS",
                "expected_selection_sha256": production_record.get("candidate_sha256"),
                **resolved_file_fields(path, root),
            }

        path = classic_path(texture_id)
        return {
            **base,
            "resolved_tier": "classic",
            "path": path,
            "resolution_reason": "stale_production_selection_fallback_to_classic",
            "production_selection_status": production_status.get("status"),
            "production_selection_checks": production_status.get("checks"),
            **resolved_file_fields(path, root),
        }

    path = classic_path(texture_id)
    return {
        **base,
        "resolved_tier": "classic",
        "path": path,
        "resolution_reason": "no_production_selection_fallback_to_classic",
        "production_selection_status": "NONE",
        **resolved_file_fields(path, root),
    }


def build_manifest(
    profile: str,
    selection: dict,
    policy: dict,
    registry: dict,
    run_root: Path,
    approval_root: Path,
    enhanced_method: str = "lanczos",
    root: Path = ROOT,
    status_resolver: Callable[[dict, Path, Path], dict] = validate_record,
) -> dict:
    if profile not in {"classic", "enhanced", "remastered"}:
        raise ValueError(f"unsupported profile: {profile}")

    production = registry.get("profiles", {}).get("remastered", {})
    rows = []
    stale_ids = []
    explicit_ids = []
    fallback_ids = []
    missing_ids = []
    integrity_failure_ids = []

    for entry in selection.get("textures", []):
        texture_id = str(entry["id"])
        record = production.get(texture_id) if isinstance(production, dict) else None
        status = None
        if profile == "remastered" and isinstance(record, dict):
            status = status_resolver(record, run_root, approval_root)

        row = resolve_entry(
            profile,
            entry,
            policy,
            record if isinstance(record, dict) else None,
            status,
            enhanced_method,
            root,
        )
        row["integrity_ok"] = bool(row.get("file_present"))
        if row["resolution_reason"] == "explicit_current_production_selection":
            expected = row.get("expected_selection_sha256")
            row["selection_hash_matches_resolved"] = (
                bool(expected)
                and bool(row.get("sha256"))
                and expected == row.get("sha256")
            )
            row["integrity_ok"] = (
                row["integrity_ok"]
                and row["selection_hash_matches_resolved"]
            )
        else:
            row["selection_hash_matches_resolved"] = None

        rows.append(row)

        if row["resolution_reason"] == "explicit_current_production_selection":
            explicit_ids.append(texture_id)
        if "fallback_to_classic" in row["resolution_reason"]:
            fallback_ids.append(texture_id)
        if row.get("production_selection_status") == "STALE":
            stale_ids.append(texture_id)
        if not row["file_present"]:
            missing_ids.append(texture_id)
        if not row["integrity_ok"]:
            integrity_failure_ids.append(texture_id)

    runtime_ready = not missing_ids and not integrity_failure_ids
    if missing_ids:
        status = "MISSING_FILES"
    elif integrity_failure_ids:
        status = "INTEGRITY_FAILURE"
    elif profile == "remastered" and stale_ids:
        status = "SAFE_CLASSIC_FALLBACK_STALE_SELECTIONS"
    elif profile == "remastered" and fallback_ids:
        status = "SAFE_CLASSIC_FALLBACKS"
    else:
        status = "READY"

    return {
        "schema": "openazrael.texture_lab.runtime_texture_manifest.v1",
        "profile": profile,
        "status": status,
        "runtime_ready": runtime_ready,
        "automatic_promotion": False,
        "enhanced_method_requested": enhanced_method if profile == "enhanced" else None,
        "texture_count": len(rows),
        "explicit_production_selection_count": len(explicit_ids),
        "classic_fallback_count": len(fallback_ids),
        "stale_production_selection_count": len(stale_ids),
        "missing_resolved_file_count": len(missing_ids),
        "integrity_failure_count": len(integrity_failure_ids),
        "explicit_ids": explicit_ids,
        "fallback_ids": fallback_ids,
        "stale_ids": stale_ids,
        "missing_ids": missing_ids,
        "integrity_failure_ids": integrity_failure_ids,
        "textures": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a fail-safe OpenAzrael texture presentation manifest. "
            "Remastered uses only current explicit production selections and "
            "falls back to Classic otherwise."
        )
    )
    parser.add_argument("profile", choices=["classic", "enhanced", "remastered"])
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--approval-root", type=Path, default=DEFAULT_APPROVAL_ROOT)
    parser.add_argument(
        "--enhanced-method",
        choices=sorted(ENHANCED_METHODS),
        default="lanczos",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Return HOLD when files are missing or when Remastered contains "
            "stale production selections. Safe Classic fallbacks without stale "
            "records remain allowed unless files are missing."
        ),
    )
    args = parser.parse_args()

    selection = load_json(args.selection)
    policy = load_json(args.policy)
    registry = load_registry(args.registry)
    manifest = build_manifest(
        args.profile,
        selection,
        policy,
        registry,
        args.run_root,
        args.approval_root,
        args.enhanced_method,
        args.root,
    )
    manifest["inputs"] = {
        "selection": input_file_record(args.selection, args.root),
        "policy": input_file_record(args.policy, args.root),
        "production_registry": input_file_record(args.registry, args.root),
    }

    out = args.out or DEFAULT_OUTPUT_ROOT / f"{args.profile}.json"
    write_json(out, manifest)

    hold = bool(manifest["missing_ids"] or manifest["integrity_failure_ids"])
    if args.profile == "remastered" and args.strict and manifest["stale_ids"]:
        hold = True

    print(
        f"{'HOLD' if hold else 'PASS'} runtime_manifest "
        f"profile={args.profile} explicit={manifest['explicit_production_selection_count']} "
        f"fallbacks={manifest['classic_fallback_count']} "
        f"stale={manifest['stale_production_selection_count']} "
        f"missing={manifest['missing_resolved_file_count']} "
        f"integrity_failures={manifest['integrity_failure_count']} out={out}"
    )
    return 1 if hold else 0


if __name__ == "__main__":
    raise SystemExit(main())
