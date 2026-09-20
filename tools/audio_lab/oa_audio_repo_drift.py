#!/usr/bin/env python3
"""Compare current repository-only audio mapping evidence against the AL-POC-01 baseline."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.audio_lab.oa_audio_repo_evidence import build_repo_evidence
from tools.audio_lab.oa_audio_reference_audit import load_json

ROOT = Path(__file__).resolve().parents[2]

BASELINE_FIELDS = (
    "asset_count",
    "mapped_assets",
    "expected_unmapped_assets",
    "unexpected_orphan_assets",
    "broken_reference_count",
    "mapped_asset_names",
    "mapped_asset_names_by_type",
)

def compare_baseline(baseline: dict, report: dict) -> list[dict]:
    summary = report.get("summary", {})
    diffs: list[dict] = []
    for field in BASELINE_FIELDS:
        expected = baseline.get(field)
        actual = summary.get(field)
        if expected != actual:
            diffs.append({
                "field": field,
                "expected": expected,
                "actual": actual,
            })
    return diffs

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference-root", type=Path, default=ROOT)
    ap.add_argument("--legacy-ir", type=Path, default=ROOT / "data/audio/legacy_world_ir.json")
    ap.add_argument("--event-graph", type=Path, default=ROOT / "data/gameplay_event_graph_v87.json")
    ap.add_argument("--baseline", type=Path, default=ROOT / "data/audio_lab/al_poc_01_repo_mapping_baseline.json")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    baseline = load_json(args.baseline)
    report = build_repo_evidence(
        args.reference_root,
        load_json(args.legacy_ir),
        load_json(args.event_graph),
    )
    diffs = compare_baseline(baseline, report)
    result = {
        "schema": "openazrael.audio_lab.repo_mapping_drift",
        "version": 1,
        "evidence_mode": "REPOSITORY_ONLY_NO_SOURCE_BYTES",
        "status": "PASS" if report.get("status") == "PASS" and not diffs else "FAIL",
        "reference_integrity_status": report.get("status"),
        "diffs": diffs,
        "baseline": str(args.baseline),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
