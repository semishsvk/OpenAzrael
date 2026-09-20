#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json
from oa_tex_production_selection import DEFAULT_REGISTRY, registry_status
from oa_tex_review_pack_01 import (
    DEFAULT_POLICY,
    DEFAULT_REVIEW,
    DEFAULT_SAMPLING,
    DEFAULT_SELECTION,
    DEFAULT_SMOKE,
    build_availability,
    build_source_plan,
    load_json,
)
from oa_tex_stage_gate import (
    DEFAULT_APPROVAL_ROOT,
    DEFAULT_MANUAL_REVIEW_ROOT,
    DEFAULT_RUN_ROOT,
)


def _rows_by_id(payload: dict, key: str) -> dict[str, dict]:
    return {
        str(row["id"]): row
        for row in payload.get(key, [])
        if isinstance(row, dict) and row.get("id")
    }


def _production_by_id(status: dict) -> dict[str, dict]:
    return {
        str(row.get("texture_id")): row
        for row in status.get("rows", [])
        if isinstance(row, dict) and row.get("texture_id")
    }


def _ai_state(local: dict, tier: str) -> dict:
    rows = [
        row
        for row in local.get("ai", [])
        if isinstance(row, dict) and row.get("tier") == tier
    ]
    if not rows:
        return {
            "eligible": False,
            "status": "NOT_ELIGIBLE",
            "stage": None,
            "stage_evidence_status": None,
            "candidate": None,
        }

    row = rows[0]
    available = bool(row.get("available"))
    stage_status = row.get("stage_evidence_status")
    if available:
        status = "CURRENT_EVIDENCE"
    elif stage_status == "PASS":
        status = "EVIDENCE_INCOMPLETE"
    else:
        status = "PENDING_STAGE"

    return {
        "eligible": True,
        "status": status,
        "stage": row.get("stage"),
        "stage_evidence_status": stage_status,
        "candidate": row.get("candidate"),
    }


def build_asset_status(
    plan: dict,
    availability: dict,
    production_status: dict,
    classic_manifest: dict | None = None,
) -> dict:
    plan_rows = _rows_by_id(plan, "rows")
    local_rows = _rows_by_id(availability, "rows")
    production_rows = _production_by_id(production_status)
    classic_rows = _rows_by_id(classic_manifest or {}, "textures")

    rows = []
    for texture_id, spec in sorted(
        plan_rows.items(),
        key=lambda item: int(item[1].get("review_order", 9999)),
    ):
        local = local_rows.get(texture_id, {})
        classic = local.get("classic", {"status": "MISSING"})
        enhanced = local.get("enhanced", {"status": "MISSING"})
        restored = _ai_state(local, "ai_restored")
        recreated = _ai_state(local, "ai_recreated")
        production = production_rows.get(texture_id)
        production_state = (
            "NONE"
            if production is None
            else (
                "EXPLICIT_CURRENT"
                if production.get("status") == "PASS"
                else "EXPLICIT_STALE"
            )
        )

        if production_state == "EXPLICIT_STALE":
            overall = "PRODUCTION_SELECTION_STALE"
        elif production_state == "EXPLICIT_CURRENT":
            overall = "PRODUCTION_SELECTED_CURRENT"
        elif not bool(local.get("reference_ready")):
            overall = "REFERENCE_BLOCKED"
        elif int(local.get("available_ai_candidate_count", 0)) > 0:
            overall = "AI_EVIDENCE_READY"
        else:
            overall = "REFERENCE_READY"

        scan = classic_rows.get(texture_id, {})
        rows.append(
            {
                "id": texture_id,
                "review_order": spec.get("review_order"),
                "priority": spec.get("priority"),
                "room": spec.get("room"),
                "content_class": spec.get("content_class"),
                "treatment_class": spec.get("treatment_class"),
                "puzzle_critical": spec.get("content_class") == "mechanical_puzzle",
                "repeat_sampling_observed": bool(
                    spec.get("repeat_sampling_observed")
                ),
                "transparency_mode": scan.get(
                    "transparency_mode",
                    "UNKNOWN_NOT_SCANNED",
                ),
                "transparency_review_required": scan.get(
                    "transparency_review_required"
                ),
                "classic": classic,
                "enhanced": enhanced,
                "ai_restored": restored,
                "ai_recreated": recreated,
                "visual_review_status": local.get("visual_review_status"),
                "production_selection": production_state,
                "production_record_status": (
                    production.get("status")
                    if isinstance(production, dict)
                    else None
                ),
                "overall_status": overall,
                "automatic_decision": False,
            }
        )

    counts: dict[str, int] = {}
    for row in rows:
        key = str(row["overall_status"])
        counts[key] = counts.get(key, 0) + 1

    return {
        "schema": "openazrael.texture_lab.asset_status.v1",
        "status": "OBSERVATIONAL_LOCAL_STATUS",
        "automatic_selection": False,
        "automatic_quality_verdict": False,
        "automatic_production_promotion": False,
        "texture_count": len(rows),
        "status_counts": counts,
        "production_registry_status": production_status.get("status"),
        "rows": rows,
    }


def markdown_status(status: dict) -> str:
    lines = [
        "# OpenAzrael Texture Lab — Asset Status",
        "",
        "Observational lifecycle/readiness status only. This dashboard does not "
        "rank textures, approve quality, or promote production assets.",
        "",
        "| # | Texture | Priority | Classic | Enhanced | Restored | Recreated | Review | Production | Overall |",
        "|---:|---|---|---|---|---|---|---|---|---|",
    ]
    for row in status.get("rows", []):
        lines.append(
            f"| {row.get('review_order')} | {row['id']} | {row.get('priority')} | "
            f"{row.get('classic', {}).get('status')} | "
            f"{row.get('enhanced', {}).get('status')} | "
            f"{row.get('ai_restored', {}).get('status')} | "
            f"{row.get('ai_recreated', {}).get('status')} | "
            f"{row.get('visual_review_status')} | "
            f"{row.get('production_selection')} | "
            f"{row.get('overall_status')} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a passive per-asset Texture Lab lifecycle/readiness dashboard."
        )
    )
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--sampling", type=Path, default=DEFAULT_SAMPLING)
    parser.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT / "assets/textures/classic",
    )
    parser.add_argument(
        "--enhanced-dir",
        type=Path,
        default=ROOT / "assets/textures/enhanced",
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
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--classic-manifest",
        type=Path,
        default=ROOT / "data/texture_lab/classic_manifest.json",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / ".local/texture_lab/asset_status.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / ".local/texture_lab/asset_status.md",
    )
    args = parser.parse_args()

    review = load_json(args.review)
    selection = load_json(args.selection)
    policy = load_json(args.policy)
    sampling = load_json(args.sampling)
    smoke = load_json(args.smoke)
    plan = build_source_plan(review, selection, policy, sampling, smoke)
    availability = build_availability(
        plan,
        args.source_dir,
        args.enhanced_dir,
        args.run_root,
    )
    production = registry_status(
        args.registry,
        args.run_root,
        args.approval_root,
        args.manual_review_root,
    )
    classic_manifest = (
        json.loads(args.classic_manifest.read_text(encoding="utf-8"))
        if args.classic_manifest.is_file()
        else None
    )

    result = build_asset_status(
        plan,
        availability,
        production,
        classic_manifest,
    )
    write_json(args.out_json, result)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown_status(result), encoding="utf-8")
    print(
        "PASS asset_status "
        f"textures={result['texture_count']} "
        f"production={result['production_registry_status']} "
        f"json={args.out_json} md={args.out_md}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
