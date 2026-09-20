#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json
from oa_tex_review_report import merged_policy, policy_reasons, sampling_reasons

DEFAULT_REVIEW = ROOT / "tools/texture_lab/config/review_pack_01.json"
DEFAULT_SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
DEFAULT_POLICY = ROOT / "tools/texture_lab/config/ai_review_policy.json"
DEFAULT_SAMPLING = ROOT / "data/texture_lab/rt_poc_01_sampling_review.json"
DEFAULT_SMOKE = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"

PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}
TREATMENTS = {"safe_upscale", "ai_recreation_candidate", "conservative"}
ENHANCED_METHODS = {"nearest", "bicubic", "lanczos"}
EXPECTED_RUBRIC = [
    "fidelity_to_original",
    "readability_detail",
    "material_believability",
    "atmosphere_period_feel",
    "tiling_seam_safety",
    "semantic_gameplay_safety",
    "artifact_cleanliness",
    "alpha_transparency_safety",
]
EXPECTED_P1 = {
    "CORIROCK",
    "KEYHOLE#",
    "WEL_PUZ1",
    "BAPFLOR#",
    "BAPTAP",
    "SHIELD1",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_by_id(payload: dict, key: str) -> dict[str, dict]:
    return {
        str(row["id"]): row
        for row in payload.get(key, [])
        if isinstance(row, dict) and row.get("id")
    }


def earliest_preset(
    smoke: dict,
    mode: str,
    texture_id: str,
) -> str | None:
    presets = smoke.get("presets", {})
    for name in smoke.get("recommended_order", []):
        spec = presets.get(str(name))
        if not isinstance(spec, dict) or spec.get("mode") != mode:
            continue
        if texture_id in [str(value) for value in spec.get("textures", [])]:
            return str(name)
    return None


def validate_review_pack(
    review: dict,
    selection: dict,
    policy: dict,
    sampling: dict,
    smoke: dict,
) -> dict:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    selection_rows = _rows_by_id(selection, "textures")
    review_rows = [
        row for row in review.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    ]
    review_ids = [str(row["id"]) for row in review_rows]
    sampling_rows = _rows_by_id(sampling, "textures")

    checks["schema"] = (
        review.get("schema")
        == "openazrael.texture_lab.review_pack_01.v1"
    )
    checks["status_observational"] = (
        review.get("status") == "OBSERVATIONAL_PLAN"
    )
    checks["automatic_selection_off"] = (
        review.get("automatic_selection") is False
    )
    checks["automatic_quality_verdict_off"] = (
        review.get("automatic_quality_verdict") is False
    )
    checks["automatic_production_promotion_off"] = (
        review.get("automatic_production_promotion") is False
    )
    checks["exact_selection_ids"] = (
        len(review_ids) == len(selection_rows) == 12
        and len(review_ids) == len(set(review_ids))
        and set(review_ids) == set(selection_rows)
    )
    checks["all_sampling_rows_present"] = set(review_ids).issubset(
        set(sampling_rows)
    )
    checks["priorities_valid"] = all(
        row.get("priority") in PRIORITY_ORDER for row in review_rows
    )
    checks["treatments_valid"] = all(
        row.get("treatment_class") in TREATMENTS for row in review_rows
    )
    checks["enhanced_methods_valid"] = all(
        row.get("enhanced_reference") in ENHANCED_METHODS
        for row in review_rows
    )
    checks["review_focus_present"] = all(
        isinstance(row.get("review_focus"), list)
        and len(row.get("review_focus", [])) > 0
        and all(
            isinstance(value, str) and value
            for value in row["review_focus"]
        )
        for row in review_rows
    )

    counts = {
        priority: sum(row.get("priority") == priority for row in review_rows)
        for priority in PRIORITY_ORDER
    }
    details["priority_counts"] = counts
    checks["priority_mix"] = counts == {"P1": 6, "P2": 5, "P3": 1}
    checks["p1_exact"] = {
        str(row["id"]) for row in review_rows
        if row.get("priority") == "P1"
    } == EXPECTED_P1

    rubric = review.get("rubric", {})
    dimensions = [
        str(row.get("id"))
        for row in rubric.get("dimensions", [])
        if isinstance(row, dict)
    ]
    checks["rubric_scale"] = (
        rubric.get("scale_min") == 1
        and rubric.get("scale_max") == 5
        and rubric.get("higher_is_better") is True
    )
    checks["rubric_dimensions_exact"] = dimensions == EXPECTED_RUBRIC
    checks["rubric_no_aggregate"] = (
        rubric.get("automatic_aggregate") is False
        and rubric.get("automatic_threshold") is False
    )
    checks["rubric_anchors_present"] = all(
        isinstance(row.get("anchor_1"), str)
        and bool(row.get("anchor_1"))
        and isinstance(row.get("anchor_5"), str)
        and bool(row.get("anchor_5"))
        for row in rubric.get("dimensions", [])
        if isinstance(row, dict)
    )

    by_id = {str(row["id"]): row for row in review_rows}
    policy_classes = policy.get("classes", {})
    checks["canonical_classes_have_policy"] = all(
        str(selection_rows.get(texture_id, {}).get("content_class", ""))
        in policy_classes
        for texture_id in review_ids
    )

    keyhole = by_id.get("KEYHOLE#", {})
    keyhole_rules = merged_policy(
        selection_rows.get("KEYHOLE#", {}),
        policy,
    )
    checks["keyhole_conservative_nearest"] = (
        keyhole.get("treatment_class") == "conservative"
        and keyhole.get("enhanced_reference") == "nearest"
        and keyhole_rules.get("ai_restored") is False
        and keyhole_rules.get("ai_recreated") is False
    )

    shield_rules = merged_policy(
        selection_rows.get("SHIELD1", {}),
        policy,
    )
    checks["shield_text_conservative"] = (
        by_id.get("SHIELD1", {}).get("treatment_class") == "conservative"
        and shield_rules.get("ai_recreated") is False
        and bool(shield_rules.get("manual_text_review"))
    )

    puzzle_rules = merged_policy(
        selection_rows.get("WEL_PUZ1", {}),
        policy,
    )
    checks["puzzle_conservative"] = (
        by_id.get("WEL_PUZ1", {}).get("treatment_class") == "conservative"
        and bool(puzzle_rules.get("manual_geometry_review"))
    )

    bap_floor_rules = merged_policy(
        selection_rows.get("BAPFLOR#", {}),
        policy,
    )
    checks["bap_floor_conservative_alpha_repeat"] = (
        by_id.get("BAPFLOR#", {}).get("treatment_class") == "conservative"
        and bap_floor_rules.get("exact_alpha_lock") is True
        and sampling_rows.get("BAPFLOR#", {}).get(
            "repeat_sampling_observed"
        ) is True
    )

    baptap_rules = merged_policy(
        selection_rows.get("BAPTAP", {}),
        policy,
    )
    atlas = baptap_rules.get("atlas_split")
    checks["baptap_recreation_candidate_atlas_lock"] = (
        by_id.get("BAPTAP", {}).get("treatment_class")
        == "ai_recreation_candidate"
        and baptap_rules.get("atlas_boundary_lock") is True
        and isinstance(atlas, dict)
        and atlas.get("axis") == "x"
        and atlas.get("segments") == 4
    )

    checks["selection_still_no_automatic_winner"] = (
        selection.get("automatic_winner") is False
    )
    checks["smoke_order_available"] = isinstance(
        smoke.get("recommended_order"),
        list,
    ) and bool(smoke.get("recommended_order"))

    failed = sorted(name for name, value in checks.items() if not value)
    return {
        "schema": "openazrael.texture_lab.review_pack_01_validation.v1",
        "status": "PASS" if not failed else "FAIL",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed": failed,
        "checks": checks,
        "details": details,
    }


def build_source_plan(
    review: dict,
    selection: dict,
    policy: dict,
    sampling: dict,
    smoke: dict,
) -> dict:
    validation = validate_review_pack(
        review,
        selection,
        policy,
        sampling,
        smoke,
    )
    if validation["status"] != "PASS":
        raise ValueError(
            "Review Pack 01 contract invalid: "
            + ", ".join(validation["failed"])
        )

    selection_rows = _rows_by_id(selection, "textures")
    sampling_rows = _rows_by_id(sampling, "textures")
    config_order = {
        str(row["id"]): index
        for index, row in enumerate(review["textures"])
    }
    rows = []

    for spec in review["textures"]:
        texture_id = str(spec["id"])
        selection_row = selection_rows[texture_id]
        sampling_row = sampling_rows[texture_id]
        rules = merged_policy(selection_row, policy)

        variants = [
            {
                "tier": "classic",
                "role": "immutable_reference",
                "stage": None,
            },
            {
                "tier": "enhanced_" + str(spec["enhanced_reference"]),
                "role": "deterministic_reference",
                "stage": None,
            },
        ]
        if bool(rules.get("ai_restored", False)):
            variants.append(
                {
                    "tier": "ai_restored",
                    "role": "observational_candidate",
                    "stage": earliest_preset(
                        smoke,
                        "restored",
                        texture_id,
                    ),
                }
            )
        if bool(rules.get("ai_recreated", False)):
            variants.append(
                {
                    "tier": "ai_recreated",
                    "role": "observational_candidate",
                    "stage": earliest_preset(
                        smoke,
                        "recreated",
                        texture_id,
                    ),
                }
            )

        attention = list(spec.get("review_focus", []))
        attention.extend(policy_reasons(rules))
        attention.extend(sampling_reasons(sampling_row))
        attention = list(dict.fromkeys(str(value) for value in attention))

        rows.append(
            {
                "id": texture_id,
                "priority": spec["priority"],
                "treatment_class": spec["treatment_class"],
                "room": selection_row.get("room"),
                "content_class": selection_row.get("content_class"),
                "primitive_uses": sampling_row.get("primitive_uses"),
                "sampling_class": sampling_row.get("sampling_class"),
                "repeat_sampling_observed": bool(
                    sampling_row.get("repeat_sampling_observed")
                ),
                "comparison_variants": variants,
                "review_attention": attention,
                "rubric_scores": {
                    dimension["id"]: None
                    for dimension in review["rubric"]["dimensions"]
                },
                "manual_note": None,
                "automatic_decision": False,
                "_config_order": config_order[texture_id],
            }
        )

    rows.sort(
        key=lambda row: (
            PRIORITY_ORDER[str(row["priority"])],
            int(row["_config_order"]),
        )
    )
    for rank, row in enumerate(rows, 1):
        row["review_order"] = rank
        row.pop("_config_order", None)

    return {
        "schema": "openazrael.texture_lab.review_pack_01_source_plan.v1",
        "status": "SOURCE_PLAN_PASS",
        "review_pack": "Review Pack 01",
        "texture_count": len(rows),
        "automatic_selection": False,
        "automatic_quality_verdict": False,
        "automatic_production_promotion": False,
        "real_ai_output_status": "STAGE_DEPENDENT_NOT_INFERRED",
        "rubric": review["rubric"],
        "rows": rows,
    }


def markdown_plan(plan: dict) -> str:
    lines = [
        "# OpenAzrael Texture Lab — Review Pack 01",
        "",
        "Source-safe review plan only. It does not claim that Real-ESRGAN or "
        "Qwen outputs exist and it never selects or promotes a production texture.",
        "",
        "| # | Texture | Room | Priority | Treatment | Comparison variants | Review attention |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in plan["rows"]:
        variants = ", ".join(
            (
                variant["tier"]
                + (
                    f" [{variant['stage']}]"
                    if variant.get("stage")
                    else ""
                )
            )
            for variant in row["comparison_variants"]
        )
        attention = "; ".join(row["review_attention"])
        lines.append(
            f"| {row['review_order']} | {row['id']} | {row['room']} | "
            f"{row['priority']} | {row['treatment_class']} | {variants} | "
            f"{attention} |"
        )

    lines.extend(
        [
            "",
            "## Manual rubric",
            "",
            "Score 1–5, where 5 is best. N/A is allowed when a dimension "
            "does not apply. No aggregate score, threshold or winner is computed.",
            "",
            "| Dimension | 1 | 5 |",
            "|---|---|---|",
        ]
    )
    for dimension in plan["rubric"]["dimensions"]:
        lines.append(
            f"| {dimension['label']} | {dimension['anchor_1']} | "
            f"{dimension['anchor_5']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or render the source-safe Texture Lab Review Pack 01 plan."
        )
    )
    parser.add_argument("command", choices=["validate", "render"])
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--sampling", type=Path, default=DEFAULT_SAMPLING)
    parser.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    review = load_json(args.review)
    selection = load_json(args.selection)
    policy = load_json(args.policy)
    sampling = load_json(args.sampling)
    smoke = load_json(args.smoke)

    validation = validate_review_pack(
        review,
        selection,
        policy,
        sampling,
        smoke,
    )
    if args.command == "validate":
        print(
            f"{validation['status']} review_pack_01 "
            f"checks={validation['check_count']} "
            f"failed={validation['failed_count']}"
        )
        if validation["failed"]:
            print("failed: " + ", ".join(validation["failed"]))
        return 0 if validation["status"] == "PASS" else 1

    if validation["status"] != "PASS":
        print(
            "FAIL review_pack_01: "
            + ", ".join(validation["failed"])
        )
        return 1

    plan = build_source_plan(
        review,
        selection,
        policy,
        sampling,
        smoke,
    )
    if args.out_json:
        write_json(args.out_json, plan)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(markdown_plan(plan), encoding="utf-8")
    print(
        "PASS review_pack_01_render "
        f"textures={plan['texture_count']} "
        f"json={args.out_json or '-'} md={args.out_md or '-'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
