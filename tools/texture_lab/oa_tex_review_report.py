#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def merged_policy(entry: dict, policy: dict) -> dict:
    result = dict(policy.get("defaults", {}))
    result.update(policy.get("classes", {}).get(str(entry.get("content_class", "")), {}))
    return result


def policy_reasons(rules: dict) -> list[str]:
    reasons = []
    for key in [
        "manual_text_review",
        "manual_artwork_review",
        "manual_geometry_review",
        "manual_review",
        "seam_review",
    ]:
        value = rules.get(key)
        if value:
            reasons.append(f"{key}:{value}")
    if rules.get("exact_alpha_lock"):
        reasons.append("exact_alpha_lock")
    if rules.get("atlas_boundary_lock"):
        reasons.append("atlas_boundary_lock")
    atlas = rules.get("atlas_split")
    if isinstance(atlas, dict):
        reasons.append(
            f"atlas_split:{atlas.get('axis')}x{atlas.get('segments')}"
        )
    if rules.get("repeat_sampling_observed"):
        reasons.append("repeat_sampling_observed")
    return reasons


def sampling_reasons(record: dict | None) -> list[str]:
    if not isinstance(record, dict):
        return []
    reasons = []
    seam = record.get("seam_review")
    if seam and seam != "none":
        reasons.append(f"sampling_seam:{seam}")
    if record.get("repeat_sampling_observed"):
        axes = ",".join(record.get("repeat_axes", []))
        reasons.append(f"repeat_sampling:{axes or 'observed'}")
    if record.get("sampling_class"):
        reasons.append(f"sampling_class:{record['sampling_class']}")
    return reasons


def report_index(report: dict | None) -> dict[str, dict]:
    if not isinstance(report, dict):
        return {}
    return {
        str(row["id"]): row
        for row in report.get("results", [])
        if isinstance(row, dict) and row.get("id")
    }


def drift_index(report: dict) -> dict[str, dict]:
    return {
        str(row["id"]): row
        for row in report.get("results", [])
        if isinstance(row, dict) and row.get("id")
    }


def build_review_rows(
    mode: str,
    selection: dict,
    policy: dict,
    sampling: dict,
    baseline: dict,
    drift_report: dict,
    only_ids: set[str] | None = None,
    technical_report: dict | None = None,
) -> list[dict]:
    key = "ai_restored" if mode == "restored" else "ai_recreated"
    drift = drift_index(drift_report)
    technical = report_index(technical_report)
    sampling_by_id = {
        str(row["id"]): row
        for row in sampling.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    }

    low = baseline["global_envelope"]["low_frequency_luma_mae_0_255"]
    deterministic_p95 = float(low["p95"])
    deterministic_max = float(low["max"])

    rows = []
    for entry in selection["textures"]:
        rules = merged_policy(entry, policy)
        if not bool(rules.get(key, False)):
            continue

        texture_id = str(entry["id"])
        if only_ids is not None and texture_id not in only_ids:
            continue
        result = drift.get(texture_id)
        technical_result = technical.get(texture_id)
        reasons = policy_reasons(rules) + sampling_reasons(sampling_by_id.get(texture_id))

        row = {
            "id": texture_id,
            "room": entry.get("room"),
            "content_class": entry.get("content_class"),
            "mode": mode,
            "review_state": "PENDING_OUTPUT",
            "low_frequency_luma_mae_0_255": None,
            "ratio_to_deterministic_p95": None,
            "ratio_to_deterministic_max": None,
            "alpha_silhouette_mismatch_fraction": None,
            "source_edge_seam_mae_rgba_0_255": None,
            "candidate_edge_seam_mae_rgba_0_255": None,
            "candidate_minus_source_seam_mae_rgba_0_255": None,
            "candidate_to_source_seam_ratio": None,
            "source_transparency_mode": None,
            "source_transparency_review_required": None,
            "source_transparency_reason": None,
            "exact_alpha_mask_ok": None,
            "alpha_mask_mismatch_pixels": None,
            "transparent_rgb_nonzero_pixels": None,
            "attention": reasons,
        }

        if result is not None:
            value = float(result["low_frequency_luma_mae_0_255"])
            alpha = result.get("alpha_silhouette_mismatch_fraction")
            row.update(
                {
                    "review_state": "MANUAL_REVIEW_REQUIRED",
                    "low_frequency_luma_mae_0_255": value,
                    "ratio_to_deterministic_p95": (
                        value / deterministic_p95 if deterministic_p95 else None
                    ),
                    "ratio_to_deterministic_max": (
                        value / deterministic_max if deterministic_max else None
                    ),
                    "alpha_silhouette_mismatch_fraction": alpha,
                }
            )
            if value > deterministic_max:
                row["attention"].append("drift_above_deterministic_max")
            elif value > deterministic_p95:
                row["attention"].append("drift_above_deterministic_p95")
            if alpha is not None and float(alpha) > 0.0:
                row["attention"].append("alpha_silhouette_mismatch")

        if technical_result is not None:
            row["source_edge_seam_mae_rgba_0_255"] = technical_result.get(
                "source_edge_seam_mae_rgba_0_255"
            )
            row["candidate_edge_seam_mae_rgba_0_255"] = technical_result.get(
                "candidate_edge_seam_mae_rgba_0_255"
            )
            row["candidate_minus_source_seam_mae_rgba_0_255"] = technical_result.get(
                "candidate_minus_source_seam_mae_rgba_0_255"
            )
            row["candidate_to_source_seam_ratio"] = technical_result.get(
                "candidate_to_source_seam_ratio"
            )
            row["source_transparency_mode"] = technical_result.get(
                "source_transparency_mode"
            )
            row["source_transparency_review_required"] = technical_result.get(
                "source_transparency_review_required"
            )
            row["source_transparency_reason"] = technical_result.get(
                "source_transparency_reason"
            )
            row["exact_alpha_mask_ok"] = technical_result.get(
                "exact_alpha_mask_ok"
            )
            row["alpha_mask_mismatch_pixels"] = technical_result.get(
                "alpha_mask_mismatch_pixels"
            )
            row["transparent_rgb_nonzero_pixels"] = technical_result.get(
                "transparent_rgb_nonzero_pixels"
            )
            if technical_result.get("source_transparency_review_required") is True:
                row["attention"].append("transparency_classification_ambiguous")
            if technical_result.get("exact_alpha_mask_ok") is False:
                row["attention"].append("exact_alpha_mask_mismatch")
            if int(technical_result.get("transparent_rgb_nonzero_pixels") or 0) > 0:
                row["attention"].append("transparent_rgb_not_normalized")
            if int(technical_result.get("visible_legacy_magenta_pixels") or 0) > 0:
                row["attention"].append("visible_legacy_magenta")

        # Stable de-duplication while preserving reason order.
        row["attention"] = list(dict.fromkeys(row["attention"]))
        rows.append(row)

    rows.sort(
        key=lambda row: (
            row["low_frequency_luma_mae_0_255"] is None,
            -(row["low_frequency_luma_mae_0_255"] or 0.0),
            row["id"],
        )
    )
    return rows


def markdown_report(mode: str, rows: list[dict], baseline: dict) -> str:
    low = baseline["global_envelope"]["low_frequency_luma_mae_0_255"]
    lines = [
        f"# OpenAzrael Texture Lab — {mode.title()} Review Queue",
        "",
        "This report is observational. It does not automatically approve or reject AI-generated assets.",
        "",
        (
            "Deterministic low-frequency reference: "
            f"p95={low['p95']} / 255, max={low['max']} / 255."
        ),
        "",
        "| Texture | State | Transparency | Low-freq MAE | vs p95 | Seam ΔU | Seam ΔV | Review attention |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        value = row["low_frequency_luma_mae_0_255"]
        ratio = row["ratio_to_deterministic_p95"]
        value_text = "—" if value is None else f"{value:.4f}"
        ratio_text = "—" if ratio is None else f"{ratio:.2f}×"
        seam_delta = row.get("candidate_minus_source_seam_mae_rgba_0_255") or {}
        seam_u = seam_delta.get("x")
        seam_v = seam_delta.get("y")
        seam_u_text = "—" if seam_u is None else f"{float(seam_u):+.3f}"
        seam_v_text = "—" if seam_v is None else f"{float(seam_v):+.3f}"
        transparency = row.get("source_transparency_mode") or "—"
        attention = "; ".join(row["attention"]) or "visual fidelity review"
        lines.append(
            f"| {row['id']} | {row['review_state']} | {transparency} | "
            f"{value_text} | {ratio_text} | {seam_u_text} | {seam_v_text} | "
            f"{attention} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an observational manual-review queue for AI texture candidates."
    )
    parser.add_argument("mode", choices=["restored", "recreated"])
    parser.add_argument("--drift", type=Path, required=True)
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "tools/texture_lab/config/ai_review_policy.json",
    )
    parser.add_argument(
        "--sampling",
        type=Path,
        default=ROOT / "data/texture_lab/rt_poc_01_sampling_review.json",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=ROOT / "data/texture_lab/rt_poc_01_drift_baseline.json",
    )
    parser.add_argument("--technical", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    selection = load_json(args.selection)
    policy = load_json(args.policy)
    sampling = load_json(args.sampling)
    baseline = load_json(args.baseline)
    drift_report = load_json(args.drift)
    technical_report = load_json(args.technical) if args.technical else None

    only_ids = set(args.only) if args.only else None
    rows = build_review_rows(
        args.mode,
        selection,
        policy,
        sampling,
        baseline,
        drift_report,
        only_ids,
        technical_report,
    )
    payload = {
        "schema": "openazrael.texture_lab.ai_review_queue.v1",
        "status": "OBSERVATIONAL_MANUAL_REVIEW",
        "mode": args.mode,
        "automatic_promotion": False,
        "only": sorted(only_ids) if only_ids is not None else None,
        "rows": rows,
    }
    write_json(args.out_json, payload)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(
        markdown_report(args.mode, rows, baseline),
        encoding="utf-8",
    )
    print(
        f"PASS review_queue mode={args.mode} rows={len(rows)} "
        f"json={args.out_json} md={args.out_md}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
