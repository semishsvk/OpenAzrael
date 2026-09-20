#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

from common import ROOT, sha256_file, write_json
from oa_tex_compare import make_alpha_sheet, make_detail_sheet, make_sheet
from oa_tex_review_report import merged_policy, policy_reasons, sampling_reasons
from oa_tex_stage_gate import DEFAULT_RUN_ROOT, evidence_snapshot

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


def _local_file_status(path: Path) -> dict:
    if not path.is_file():
        return {
            "status": "MISSING",
            "path": str(path),
        }
    return {
        "status": "PRESENT",
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_availability(
    plan: dict,
    source_dir: Path,
    enhanced_dir: Path,
    run_root: Path,
) -> dict:
    stage_cache: dict[str, dict] = {}

    def stage_snapshot(name: str) -> dict:
        if name not in stage_cache:
            stage_cache[name] = evidence_snapshot(name, run_root)
        return stage_cache[name]

    rows = []
    for row in plan["rows"]:
        texture_id = str(row["id"])
        classic = _local_file_status(source_dir / f"{texture_id}.png")

        enhanced_method = next(
            variant["tier"].removeprefix("enhanced_")
            for variant in row["comparison_variants"]
            if str(variant["tier"]).startswith("enhanced_")
        )
        enhanced = _local_file_status(
            enhanced_dir
            / texture_id
            / f"{enhanced_method}_x4.png"
        )

        ai_rows = []
        for variant in row["comparison_variants"]:
            tier = str(variant["tier"])
            if tier not in {"ai_restored", "ai_recreated"}:
                continue
            stage = str(variant.get("stage") or "")
            snapshot = (
                stage_snapshot(stage)
                if stage
                else {"status": "MISSING"}
            )
            output = None
            if snapshot.get("status") == "PASS":
                output = next(
                    (
                        value
                        for value in snapshot.get("outputs", [])
                        if isinstance(value, dict)
                        and str(value.get("id")) == texture_id
                    ),
                    None,
                )
            ai_rows.append(
                {
                    "tier": tier,
                    "stage": stage or None,
                    "stage_evidence_status": snapshot.get("status"),
                    "candidate": output,
                    "available": isinstance(output, dict),
                }
            )

        reference_ready = (
            classic["status"] == "PRESENT"
            and enhanced["status"] == "PRESENT"
        )
        available_ai = sum(
            bool(value.get("available"))
            for value in ai_rows
        )
        if not reference_ready:
            visual_status = "BLOCKED_REFERENCE_INPUTS"
        elif available_ai > 0:
            visual_status = "READY_WITH_CURRENT_AI_EVIDENCE"
        else:
            visual_status = "REFERENCE_ONLY_AI_NOT_CURRENT"

        rows.append(
            {
                "id": texture_id,
                "review_order": row["review_order"],
                "priority": row["priority"],
                "treatment_class": row["treatment_class"],
                "reference_ready": reference_ready,
                "visual_review_status": visual_status,
                "classic": classic,
                "enhanced": enhanced,
                "ai": ai_rows,
                "available_ai_candidate_count": available_ai,
                "automatic_decision": False,
            }
        )

    p1 = [row for row in rows if row["priority"] == "P1"]
    return {
        "schema": "openazrael.texture_lab.review_pack_01_availability.v1",
        "status": "OBSERVATIONAL_LOCAL_STATUS",
        "automatic_selection": False,
        "automatic_quality_verdict": False,
        "texture_count": len(rows),
        "reference_ready_count": sum(
            row["reference_ready"] for row in rows
        ),
        "ready_with_ai_count": sum(
            row["visual_review_status"]
            == "READY_WITH_CURRENT_AI_EVIDENCE"
            for row in rows
        ),
        "p1_ready_with_ai_count": sum(
            row["visual_review_status"]
            == "READY_WITH_CURRENT_AI_EVIDENCE"
            for row in p1
        ),
        "p1_count": len(p1),
        "stage_evidence": {
            name: {
                "status": snapshot.get("status"),
                "mode": snapshot.get("mode"),
            }
            for name, snapshot in sorted(stage_cache.items())
        },
        "rows": rows,
    }


def _evidence_record_current(record: dict) -> bool:
    if not isinstance(record, dict):
        return False
    path = Path(str(record.get("path", "")))
    return (
        path.is_file()
        and int(record.get("size_bytes", -1)) == path.stat().st_size
        and str(record.get("sha256", "")) == sha256_file(path)
    )


def _hub_file_record(path: Path) -> dict:
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_visual_hub(
    plan: dict,
    availability: dict,
    out_dir: Path,
    cell: int = 320,
) -> dict:
    available_by_id = {
        str(row["id"]): row
        for row in availability.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    }
    rows = []
    skipped = []
    out_dir.mkdir(parents=True, exist_ok=True)

    for plan_row in plan["rows"]:
        texture_id = str(plan_row["id"])
        local = available_by_id.get(texture_id)
        if not isinstance(local, dict) or not local.get("reference_ready"):
            skipped.append(
                {
                    "id": texture_id,
                    "reason": "reference_inputs_not_ready",
                }
            )
            continue

        classic_record = local.get("classic")
        enhanced_record = local.get("enhanced")
        if (
            not _evidence_record_current(classic_record)
            or not _evidence_record_current(enhanced_record)
        ):
            raise RuntimeError(
                f"{texture_id}: reference evidence changed after availability snapshot"
            )

        source = Path(str(classic_record["path"]))
        enhanced = Path(str(enhanced_record["path"]))
        variants: list[tuple[str, Path]] = [
            ("Enhanced reference", enhanced),
        ]
        variant_records = [
            {
                "tier": "enhanced",
                "record": enhanced_record,
            }
        ]

        for ai in local.get("ai", []):
            if not isinstance(ai, dict) or not ai.get("available"):
                continue
            candidate = ai.get("candidate")
            if not _evidence_record_current(candidate):
                raise RuntimeError(
                    f"{texture_id}: current {ai.get('tier')} evidence changed"
                )
            tier = str(ai.get("tier"))
            candidate_path = Path(str(candidate["path"]))
            label = (
                "AI Restored"
                if tier == "ai_restored"
                else "AI Recreated"
            )
            variants.append((label, candidate_path))
            variant_records.append(
                {
                    "tier": tier,
                    "stage": ai.get("stage"),
                    "record": candidate,
                }
            )

        texture_dir = out_dir / (
            f"{int(plan_row['review_order']):02d}_{texture_id.replace('#', '_hash')}"
        )
        full = texture_dir / "comparison.png"
        detail = texture_dir / "detail.png"
        make_sheet(texture_id, source, variants, full, cell)
        make_detail_sheet(texture_id, source, variants, detail, cell)

        alpha_evidence = []
        for variant in variant_records:
            tier = str(variant["tier"])
            candidate_path = Path(str(variant["record"]["path"]))
            alpha_path = texture_dir / f"alpha_{tier}.png"
            make_alpha_sheet(
                texture_id,
                source,
                candidate_path,
                alpha_path,
                cell,
            )
            alpha_evidence.append(
                {
                    "tier": tier,
                    "stage": variant.get("stage"),
                    "preview": _hub_file_record(alpha_path),
                }
            )

        rows.append(
            {
                "id": texture_id,
                "review_order": plan_row["review_order"],
                "priority": plan_row["priority"],
                "treatment_class": plan_row["treatment_class"],
                "visual_review_status": local.get(
                    "visual_review_status"
                ),
                "source": classic_record,
                "variants": variant_records,
                "comparison": _hub_file_record(full),
                "detail_comparison": _hub_file_record(detail),
                "alpha_evidence": alpha_evidence,
                "review_attention": list(
                    plan_row.get("review_attention", [])
                ),
                "automatic_decision": False,
            }
        )

    return {
        "schema": "openazrael.texture_lab.review_pack_01_visual_hub.v1",
        "status": (
            "OBSERVATIONAL_HUB_READY"
            if rows
            else "NO_REFERENCE_INPUTS"
        ),
        "automatic_selection": False,
        "automatic_quality_verdict": False,
        "approval_evidence": False,
        "texture_count": len(rows),
        "skipped_count": len(skipped),
        "rows": rows,
        "skipped": skipped,
        "boundary": (
            "Convenience overview only. Stage-specific review packs, manual "
            "review records and approval receipts remain authoritative."
        ),
    }


def _relative_href(path: Path, html_path: Path) -> str:
    return Path(
        os.path.relpath(path.resolve(), html_path.parent.resolve())
    ).as_posix()


def render_visual_hub_html(hub: dict, html_path: Path) -> str:
    sections = []
    for row in hub.get("rows", []):
        comparison = Path(str(row["comparison"]["path"]))
        detail = Path(str(row["detail_comparison"]["path"]))
        comparison_href = html.escape(
            _relative_href(comparison, html_path),
            quote=True,
        )
        detail_href = html.escape(
            _relative_href(detail, html_path),
            quote=True,
        )
        variants = ", ".join(
            str(value.get("tier"))
            + (
                f" [{value.get('stage')}]"
                if value.get("stage")
                else ""
            )
            for value in row.get("variants", [])
        )
        alpha_blocks = "".join(
            (
                '<figure><figcaption>Alpha evidence — '
                + html.escape(str(value.get("tier")))
                + '</figcaption><a href="'
                + html.escape(
                    _relative_href(
                        Path(str(value["preview"]["path"])),
                        html_path,
                    ),
                    quote=True,
                )
                + '"><img src="'
                + html.escape(
                    _relative_href(
                        Path(str(value["preview"]["path"])),
                        html_path,
                    ),
                    quote=True,
                )
                + '" alt="alpha evidence"></a></figure>'
            )
            for value in row.get("alpha_evidence", [])
            if isinstance(value, dict)
            and isinstance(value.get("preview"), dict)
        )
        attention = "".join(
            f"<li>{html.escape(str(value))}</li>"
            for value in row.get("review_attention", [])
        )
        sections.append(
            f"""
<section>
<h2>{row['review_order']}. {html.escape(str(row['id']))}
<small>{html.escape(str(row['priority']))} · {html.escape(str(row['treatment_class']))}</small></h2>
<p>Available comparison variants: {html.escape(variants)}</p>
<div class="grid">
<figure><figcaption>Full comparison</figcaption><a href="{comparison_href}"><img src="{comparison_href}" alt="full comparison"></a></figure>
<figure><figcaption>Detail comparison</figcaption><a href="{detail_href}"><img src="{detail_href}" alt="detail comparison"></a></figure>
{alpha_blocks}
</div>
<h3>Review attention</h3><ul>{attention}</ul>
</section>
"""
        )

    skipped = "".join(
        f"<li>{html.escape(str(row['id']))}: {html.escape(str(row['reason']))}</li>"
        for row in hub.get("skipped", [])
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenAzrael Texture Lab — Review Pack 01</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: system-ui,sans-serif; max-width: 1600px; margin: 2rem; line-height: 1.45; }}
.notice {{ border: 2px solid currentColor; padding: 1rem; font-weight: 700; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:1rem; }}
figure {{ margin:0; }}
img {{ width:100%; height:auto; border:1px solid #777; }}
small {{ opacity:.75; font-weight:400; }}
section {{ border-top:1px solid #555; padding-top:1rem; margin-top:2rem; }}
</style>
</head>
<body>
<h1>OpenAzrael Texture Lab — Review Pack 01</h1>
<p class="notice">OBSERVATIONAL HUB ONLY — no ranking, approval, production selection or promotion is performed here.</p>
<p>Materialized textures: {hub.get('texture_count', 0)} · skipped: {hub.get('skipped_count', 0)}</p>
{''.join(sections)}
<h2>Skipped</h2><ul>{skipped or '<li>none</li>'}</ul>
<p>{html.escape(str(hub.get('boundary', '')))}</p>
</body>
</html>
"""


def markdown_availability(status: dict) -> str:
    lines = [
        "# OpenAzrael Texture Lab — Review Pack 01 Availability",
        "",
        "Observational local evidence status only. Missing/current outputs are "
        "not quality judgments and never imply approval or production selection.",
        "",
        (
            f"References ready: {status['reference_ready_count']}/"
            f"{status['texture_count']} | Ready with current AI evidence: "
            f"{status['ready_with_ai_count']}/{status['texture_count']} | "
            f"P1 ready with AI: {status['p1_ready_with_ai_count']}/"
            f"{status['p1_count']}"
        ),
        "",
        "| # | Texture | Priority | References | AI evidence | Status |",
        "|---:|---|---|---|---|---|",
    ]
    for row in status["rows"]:
        ai_text = ", ".join(
            f"{value['tier']}:{value['stage_evidence_status']}"
            for value in row["ai"]
        ) or "not eligible"
        lines.append(
            f"| {row['review_order']} | {row['id']} | {row['priority']} | "
            f"{'ready' if row['reference_ready'] else 'missing'} | "
            f"{ai_text} | {row['visual_review_status']} |"
        )
    lines.append("")
    return "\n".join(lines)


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
    parser.add_argument(
        "command",
        choices=["validate", "render", "status", "hub"],
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
    parser.add_argument(
        "--run-root",
        type=Path,
        default=DEFAULT_RUN_ROOT,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / ".local/texture_lab/review_pack_01/current",
    )
    parser.add_argument("--cell", type=int, default=320)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    parser.add_argument(
        "--out-html",
        type=Path,
        default=None,
        help="HTML output path for the hub command.",
    )
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
    if args.command == "status":
        result = build_availability(
            plan,
            args.source_dir,
            args.enhanced_dir,
            args.run_root,
        )
        if args.out_json:
            write_json(args.out_json, result)
        if args.out_md:
            args.out_md.parent.mkdir(parents=True, exist_ok=True)
            args.out_md.write_text(
                markdown_availability(result),
                encoding="utf-8",
            )
        print(
            "PASS review_pack_01_status "
            f"references={result['reference_ready_count']}/"
            f"{result['texture_count']} ai={result['ready_with_ai_count']}/"
            f"{result['texture_count']} p1_ai="
            f"{result['p1_ready_with_ai_count']}/{result['p1_count']}"
        )
        return 0

    if args.command == "hub":
        availability = build_availability(
            plan,
            args.source_dir,
            args.enhanced_dir,
            args.run_root,
        )
        hub = build_visual_hub(
            plan,
            availability,
            args.out_dir,
            args.cell,
        )
        manifest = (
            args.out_json
            or args.out_dir / "review_pack_01_visual_hub.json"
        )
        html_path = (
            args.out_html
            or args.out_dir / "review_pack_01_visual_hub.html"
        )
        write_json(manifest, hub)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            render_visual_hub_html(hub, html_path),
            encoding="utf-8",
        )
        print(
            f"{'PASS' if hub['texture_count'] else 'HOLD'} "
            "review_pack_01_hub "
            f"textures={hub['texture_count']} skipped={hub['skipped_count']} "
            f"manifest={manifest} html={html_path}"
        )
        return 0 if hub["texture_count"] else 1

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
