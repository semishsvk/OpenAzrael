#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json
from oa_tex_stage_gate import evidence_snapshot, preset_record

DEFAULT_RUN_ROOT = ROOT / ".local/texture_lab/runs/rt_poc_01"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _review_rows(run_dir: Path, mode: str) -> list[dict]:
    review = run_dir / f"ai_{mode}_review_queue.json"
    if not review.is_file():
        return []
    data = load_json(review)
    return [row for row in data.get("rows", []) if isinstance(row, dict)]


def _pack_rows(run_dir: Path, mode: str) -> dict[str, dict]:
    manifest = run_dir / f"ai_{mode}_review_pack.json"
    if not manifest.is_file():
        return {}
    data = load_json(manifest)
    return {
        str(row["id"]): row
        for row in data.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    }


def build_summary(preset: str, run_root: Path) -> dict:
    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_root / preset
    evidence = evidence_snapshot(preset, run_root)
    godot_review_profile = run_dir / "godot_review_profile.json"

    rows = []
    pack = _pack_rows(run_dir, mode)
    for review in _review_rows(run_dir, mode):
        texture_id = str(review.get("id"))
        visual = pack.get(texture_id, {})
        rows.append(
            {
                "id": texture_id,
                "review_state": review.get("review_state"),
                "low_frequency_luma_mae_0_255": review.get(
                    "low_frequency_luma_mae_0_255"
                ),
                "ratio_to_deterministic_p95": review.get(
                    "ratio_to_deterministic_p95"
                ),
                "alpha_silhouette_mismatch_fraction": review.get(
                    "alpha_silhouette_mismatch_fraction"
                ),
                "source_edge_seam_mae_rgba_0_255": review.get(
                    "source_edge_seam_mae_rgba_0_255"
                ),
                "candidate_edge_seam_mae_rgba_0_255": review.get(
                    "candidate_edge_seam_mae_rgba_0_255"
                ),
                "candidate_minus_source_seam_mae_rgba_0_255": review.get(
                    "candidate_minus_source_seam_mae_rgba_0_255"
                ),
                "attention": list(review.get("attention", [])),
                "visual_evidence": {
                    key: value.get("path")
                    if isinstance(value, dict)
                    else None
                    for key, value in {
                        "comparison": visual.get("comparison"),
                        "detail_comparison": visual.get("detail_comparison"),
                        "tile_preview": visual.get("tile_preview"),
                        "candidate": visual.get("candidate"),
                    }.items()
                },
            }
        )

    ready = evidence.get("status") == "PASS"
    return {
        "schema": "openazrael.texture_lab.run_summary.v1",
        "preset": preset,
        "mode": mode,
        "run_dir": str(run_dir),
        "evidence_status": evidence.get("status"),
        "manual_review_status": (
            "READY_FOR_MANUAL_REVIEW" if ready else "INCOMPLETE_OR_INVALID"
        ),
        "automatic_quality_verdict": False,
        "automatic_stage_approval": False,
        "evidence_checks": evidence.get("checks"),
        "godot_review_profile": (
            str(godot_review_profile)
            if godot_review_profile.is_file()
            else None
        ),
        "textures": rows,
        "manual_next_steps": (
            [
                "Inspect each full comparison sheet for composition and authored-structure preservation.",
                "Inspect each detail comparison sheet for invented microdetail, ringing, plastic texture, false edges or lost original features.",
                "Inspect 3x3 tile previews wherever present and interpret seam deltas relative to Classic.",
                "Run the isolated Godot Texture Lab A/B scene at gameplay-like viewing scale; use O to select REVIEW and P to toggle the stage review profile.",
                f"Initialize the structured review with oa_tex_manual_review.py init {preset}.",
                "Record every texture decision and all required checks; ACCEPTED_FOR_STAGE requires every required check=true.",
                f"Confirm oa_tex_manual_review.py status {preset} returns PASS.",
                f"Only then record stage approval with oa_tex_stage_gate.py approve {preset}.",
            ]
            if ready
            else [
                "Resolve the incomplete or invalid run evidence before manual approval.",
                "Do not approve or promote any candidate from this run.",
            ]
        ),
    }


def markdown(summary: dict) -> str:
    lines = [
        f"# OpenAzrael Texture Lab — {summary['preset']} Run Summary",
        "",
        f"Evidence status: **{summary['evidence_status']}**",
        f"Manual review status: **{summary['manual_review_status']}**",
        "",
        "This summary is observational. It does not select a visual winner and does not approve or promote any texture automatically.",
        "",
    ]
    if summary.get("godot_review_profile"):
        lines.extend(
            [
                f"Godot stage review profile: {summary['godot_review_profile']}",
                "",
            ]
        )

    for row in summary.get("textures", []):
        seam = row.get("candidate_minus_source_seam_mae_rgba_0_255") or {}
        lines.extend(
            [
                f"## {row['id']}",
                "",
                f"- Low-frequency MAE: {_fmt(row.get('low_frequency_luma_mae_0_255'))}",
                f"- vs deterministic p95: {_fmt(row.get('ratio_to_deterministic_p95'), 2)}×",
                f"- Seam ΔU vs Classic: {_fmt(seam.get('x'), 3)}",
                f"- Seam ΔV vs Classic: {_fmt(seam.get('y'), 3)}",
                "- Attention: "
                + (", ".join(row.get("attention", [])) or "general visual fidelity"),
            ]
        )
        visual = row.get("visual_evidence", {})
        for label, key in [
            ("Candidate", "candidate"),
            ("Full comparison", "comparison"),
            ("Detail comparison", "detail_comparison"),
            ("3x3 tile preview", "tile_preview"),
        ]:
            if visual.get(key):
                lines.append(f"- {label}: {visual[key]}")
        lines.append("")

    lines.extend(["## Manual next steps", ""])
    for step in summary.get("manual_next_steps", []):
        lines.append(f"- {step}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize completed Texture Lab stage evidence for manual visual review."
    )
    parser.add_argument("preset")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    run_dir = args.run_root / args.preset
    out_json = args.out_json or run_dir / "run_summary.json"
    out_md = args.out_md or run_dir / "run_summary.md"

    summary = build_summary(args.preset, args.run_root)
    write_json(out_json, summary)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(summary), encoding="utf-8")

    print(
        f"{'PASS' if summary['evidence_status'] == 'PASS' else 'HOLD'} "
        f"run_summary preset={args.preset} json={out_json} md={out_md}"
    )
    return 0 if summary["evidence_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
