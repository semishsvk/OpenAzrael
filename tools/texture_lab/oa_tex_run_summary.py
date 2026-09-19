#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json
from oa_tex_stage_gate import evidence_snapshot, preset_record

DEFAULT_RUN_ROOT = ROOT / ".local/texture_lab/runs/rt_poc_01"
SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
AI_POLICY = ROOT / "tools/texture_lab/config/ai_review_policy.json"


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


def restored_performance_summary(run_dir: Path) -> dict | None:
    report_path = run_dir / "ai_restore_run.json"
    if not report_path.is_file():
        return None
    report = load_json(report_path)
    if report.get("schema") != "openazrael.texture_lab.ai_restore_run.v5":
        return None
    performance = report.get("performance")
    if not isinstance(performance, dict):
        return None

    mean = performance.get("mean_inference_wall_seconds_per_texture")
    if not isinstance(mean, (int, float)) or float(mean) <= 0:
        return {
            "status": "OBSERVED_NO_ESTIMATE",
            "report": str(report_path),
            "performance": performance,
        }

    estimates = {}
    for target in ["restored_smoke_4", "restored_full"]:
        spec = preset_record(target)
        count = len(spec.get("textures", []))
        estimates[target] = {
            "texture_count": count,
            "linear_inference_only_seconds": float(mean) * count,
            "linear_inference_only_minutes": float(mean) * count / 60.0,
        }

    return {
        "status": "OBSERVED_WITH_LINEAR_ESTIMATE",
        "report": str(report_path),
        "performance": performance,
        "estimates": estimates,
        "estimate_scope": (
            "naive linear inference-only projection from observed mean wall "
            "time per texture; excludes review, QA, I/O variability, warm-up "
            "effects and GPU contention"
        ),
    }


def recreated_generation_unit_count(preset: str) -> int:
    spec = preset_record(preset)
    selection = load_json(SELECTION)
    policy = load_json(AI_POLICY)
    by_id = {
        str(row["id"]): row
        for row in selection.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    }
    total = 0
    for texture_id in [str(v) for v in spec.get("textures", [])]:
        entry = by_id.get(texture_id, {})
        rules = dict(policy.get("defaults", {}))
        rules.update(
            policy.get("classes", {}).get(
                str(entry.get("content_class", "")),
                {},
            )
        )
        atlas = rules.get("atlas_split")
        if isinstance(atlas, dict):
            total += int(atlas.get("segments", 0))
        else:
            total += 1
    return total


def recreated_performance_summary(run_dir: Path) -> dict | None:
    job_dir = run_dir / "recreated_jobs"
    if not job_dir.is_dir():
        return None

    job_paths = sorted(job_dir.glob("*.job.json"))
    timings = []
    for path in job_paths:
        payload = load_json(path)
        if payload.get("schema") != "openazrael.texture_lab.ai_recreated_job.v5":
            continue
        performance = payload.get("performance")
        if not isinstance(performance, dict):
            continue
        wall = performance.get("job_wall_seconds")
        if isinstance(wall, (int, float)) and float(wall) >= 0.0:
            timings.append(
                {
                    "path": str(path),
                    "job_wall_seconds": float(wall),
                    "submit_to_completion_wall_seconds": (
                        float(
                            performance.get(
                                "submit_to_completion_wall_seconds",
                                0.0,
                            )
                        )
                        if isinstance(
                            performance.get(
                                "submit_to_completion_wall_seconds"
                            ),
                            (int, float),
                        )
                        else None
                    ),
                }
            )

    if not timings:
        return {
            "status": "OBSERVED_NO_ESTIMATE",
            "job_count": 0,
            "jobs": [],
        }

    total = sum(row["job_wall_seconds"] for row in timings)
    mean = total / len(timings)
    estimates = {}
    for target in [
        "recreated_smoke_4",
        "recreated_atlas",
        "recreated_full",
    ]:
        units = recreated_generation_unit_count(target)
        estimates[target] = {
            "generation_units": units,
            "linear_job_only_seconds": mean * units,
            "linear_job_only_minutes": mean * units / 60.0,
        }

    return {
        "status": "OBSERVED_WITH_LINEAR_ESTIMATE",
        "job_count": len(timings),
        "observed_job_wall_seconds": total,
        "mean_job_wall_seconds": mean,
        "jobs": timings,
        "estimates": estimates,
        "estimate_scope": (
            "naive linear client-observed ComfyUI job projection; excludes "
            "review, QA, split/stitch, I/O variability, warm-up, queueing "
            "changes and GPU contention"
        ),
    }


def build_summary(preset: str, run_root: Path) -> dict:
    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_root / preset
    evidence = evidence_snapshot(preset, run_root)
    godot_review_profile = run_dir / "godot_review_profile.json"
    review_handoff = run_dir / "review_handoff.html"

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
    performance = (
        restored_performance_summary(run_dir)
        if mode == "restored"
        else recreated_performance_summary(run_dir)
    )
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
        "review_handoff": (
            str(review_handoff)
            if review_handoff.is_file()
            else None
        ),
        "performance": performance,
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
    if summary.get("review_handoff"):
        lines.extend(
            [
                f"Local HTML review handoff: {summary['review_handoff']}",
                "",
            ]
        )

    performance = summary.get("performance")
    if isinstance(performance, dict):
        if summary.get("mode") == "restored":
            observed = performance.get("performance", {})
            lines.extend(
                [
                    "## Observed Restored runtime",
                    "",
                    "- Run wall time: "
                    + _fmt(observed.get("run_wall_seconds"), 3)
                    + " s",
                    "- Measured inference wall time: "
                    + _fmt(
                        observed.get("measured_inference_wall_seconds"),
                        3,
                    )
                    + " s",
                    "- Mean inference wall time / texture: "
                    + _fmt(
                        observed.get("mean_inference_wall_seconds_per_texture"),
                        3,
                    )
                    + " s",
                ]
            )
            for target, estimate in performance.get("estimates", {}).items():
                lines.append(
                    f"- Naive {target} inference-only projection: "
                    f"{_fmt(estimate.get('linear_inference_only_minutes'), 2)} min "
                    f"for {estimate.get('texture_count')} textures"
                )
        else:
            lines.extend(
                [
                    "## Observed Recreated runtime",
                    "",
                    "- Completed Qwen generation jobs: "
                    + str(performance.get("job_count", 0)),
                    "- Observed job wall time: "
                    + _fmt(
                        performance.get("observed_job_wall_seconds"),
                        3,
                    )
                    + " s",
                    "- Mean job wall time: "
                    + _fmt(performance.get("mean_job_wall_seconds"), 3)
                    + " s",
                ]
            )
            for target, estimate in performance.get("estimates", {}).items():
                lines.append(
                    f"- Naive {target} Qwen-job projection: "
                    f"{_fmt(estimate.get('linear_job_only_minutes'), 2)} min "
                    f"for {estimate.get('generation_units')} generation units"
                )
        if performance.get("estimate_scope"):
            lines.extend(
                [
                    "- Estimate scope: " + str(performance["estimate_scope"]),
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
