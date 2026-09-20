#!/usr/bin/env python3
"""Run the complete AL-POC-02 canonical spectral/temporal QA and drift gates."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.audio_lab.common import ensure_output_outside_source, iter_audio_files, tree_digest
from tools.audio_lab.oa_audio_canonical_verify import verify_corpus
from tools.audio_lab.oa_audio_spectral import main as spectral_main
from tools.audio_lab.oa_audio_spectral_baseline import compare_spectral_baseline

ROOT = Path(__file__).resolve().parents[2]

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_root", type=Path)
    ap.add_argument("--output-dir", type=Path, default=ROOT / ".tmp/audio_lab/al_poc_02")
    ap.add_argument("--legacy-ir", type=Path, default=ROOT / "data/audio/legacy_world_ir.json")
    ap.add_argument("--evidence", type=Path, default=ROOT / "data/audio_lab/al_poc_02_canonical_spectral_evidence.json")
    args = ap.parse_args(argv)

    source = args.source_root.resolve()
    if not source.is_dir():
        ap.error(f"source_root is not a directory: {source}")
    try:
        out = ensure_output_outside_source(source, args.output_dir)
    except ValueError as exc:
        ap.error(str(exc))
    out.mkdir(parents=True, exist_ok=True)

    source_files = iter_audio_files(source, {".wav", ".wave"})
    digest_before = tree_digest(source, source_files)

    canonical = verify_corpus(source, load_json(args.legacy_ir))
    canonical["source_unchanged_before_spectral"] = canonical.get("source_tree_sha256") == digest_before
    canonical_path = out / "canonical_source_report.json"
    canonical_path.write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    spectral_rc = spectral_main([str(source), "--output-dir", str(out)])
    manifest_path = out / "spectral_manifest.json"
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
    else:
        manifest = {
            "status": "FAIL",
            "errors": [{"code": "POC02_SPECTRAL_MANIFEST_MISSING"}],
            "assets": [],
            "source_unchanged": False,
        }

    evidence = load_json(args.evidence)
    baseline_diffs = compare_spectral_baseline(manifest, evidence)
    baseline_result = {
        "schema": "openazrael.audio_lab.al_poc_02_spectral_drift",
        "version": 1,
        "status": "PASS" if not baseline_diffs else "FAIL",
        "diffs": baseline_diffs,
        "manifest": str(manifest_path),
        "evidence": str(args.evidence),
    }
    baseline_path = out / "spectral_baseline_check.json"
    baseline_path.write_text(json.dumps(baseline_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    digest_after = tree_digest(source, iter_audio_files(source, {".wav", ".wave"}))
    source_unchanged = digest_before == digest_after == canonical.get("source_tree_sha256")

    gates = {
        "canonical_source_pass": canonical.get("status") == "PASS",
        "canonical_source_unchanged": bool(canonical.get("source_unchanged_before_spectral")),
        "spectral_analysis_pass": spectral_rc == 0 and manifest.get("status") == "PASS",
        "all_metrics_finite": not any(e.get("code") == "SPEC_NONFINITE_METRIC" for e in manifest.get("errors", [])),
        "source_unchanged_through_pipeline": source_unchanged and bool(manifest.get("source_unchanged")),
        "canonical_spectral_baseline_match": not baseline_diffs,
    }
    status = "PASS" if all(gates.values()) else "FAIL"

    summary = {
        "schema": "openazrael.audio_lab.al_poc_02_summary",
        "version": 1,
        "milestone": "AL-POC-02",
        "status": status,
        "gates": gates,
        "source_tree_sha256": digest_before,
        "analysis_fingerprint_sha256": manifest.get("analysis_fingerprint_sha256"),
        "asset_count": len(manifest.get("assets", [])),
        "analysis_errors": len(manifest.get("errors", [])),
        "review_only_outliers": manifest.get("outlier_review", {}),
        "baseline_diffs": baseline_diffs,
        "artifacts": {
            "canonical_source_report": "canonical_source_report.json",
            "spectral_manifest": "spectral_manifest.json",
            "spectral_review": "spectral_review.html",
            "spectrograms": "spectrograms/",
            "spectral_baseline_check": "spectral_baseline_check.json",
        },
    }
    summary_path = out / "al_poc_02_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if status == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
