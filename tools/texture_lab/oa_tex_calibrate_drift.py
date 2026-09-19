#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

from common import ROOT, write_json
from oa_tex_structural_drift import analyze_pair


METRICS = [
    "roundtrip_rgba_mae_0_255",
    "low_frequency_luma_mae_0_255",
    "edge_map_mae_0_255",
]


def metric_stats(values: list[float]) -> dict:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return {"count": 0}
    p95_index = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 6),
        "mean": round(statistics.mean(ordered), 6),
        "median": round(statistics.median(ordered), 6),
        "p95": round(ordered[p95_index], 6),
        "max": round(ordered[-1], 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate structural-drift reference envelope from deterministic Enhanced variants."
    )
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--candidate-dir", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument("--methods", nargs="+", default=["nearest", "bicubic", "lanczos"])
    parser.add_argument("--factor", type=int, default=4)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/texture_lab/rt_poc_01_drift_baseline.json",
    )
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    all_rows = []
    texture_rows = []

    for entry in selection["textures"]:
        texture_id = str(entry["id"])
        source = args.source_dir / f"{texture_id}.png"
        if not source.is_file():
            raise SystemExit(f"missing Classic source: {source}")
        per_method = {}
        for method in args.methods:
            candidate = args.candidate_dir / texture_id / f"{method}_x{args.factor}.png"
            if not candidate.is_file():
                raise SystemExit(f"missing calibration candidate: {candidate}")
            metrics = analyze_pair(source, candidate)
            compact = {
                key: metrics[key]
                for key in METRICS + ["alpha_silhouette_mismatch_fraction"]
            }
            per_method[method] = compact
            all_rows.append({"method": method, **compact})

        texture_rows.append(
            {
                "id": texture_id,
                "room": entry.get("room"),
                "content_class": entry.get("content_class"),
                "methods": per_method,
            }
        )

    by_method = {}
    for method in args.methods:
        rows = [row for row in all_rows if row["method"] == method]
        by_method[method] = {
            metric: metric_stats([float(row[metric]) for row in rows])
            for metric in METRICS
        }

    global_envelope = {
        metric: metric_stats([float(row[metric]) for row in all_rows])
        for metric in METRICS
    }

    write_json(
        args.out,
        {
            "schema": "openazrael.texture_lab.rt_poc_01_drift_baseline.v1",
            "status": "OBSERVATIONAL_MATHEMATICAL_BASELINE",
            "source": (
                "Canonical RT-POC-01 Classic textures versus alpha-safe deterministic "
                f"{args.factor}x mathematical candidates."
            ),
            "interpretation": (
                "Reference envelope for layout-preserving mathematical reconstruction. "
                "It is not an AI acceptance threshold and must not automatically reject "
                "or promote a generative candidate."
            ),
            "factor": args.factor,
            "methods": args.methods,
            "metrics": by_method,
            "global_envelope": global_envelope,
            "textures": texture_rows,
        },
    )
    print(f"PASS drift_baseline textures={len(texture_rows)} samples={len(all_rows)} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
