#!/usr/bin/env python3
"""Compare an AL-POC-02 spectral manifest against the canonical spectral evidence baseline."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[2]

def compare_spectral_baseline(manifest: dict, evidence: dict) -> list[dict]:
    diffs = []
    checks = (
        ("source_tree_sha256", manifest.get("source_tree_sha256"), evidence.get("source_tree_sha256")),
        ("asset_count", len(manifest.get("assets", [])), evidence.get("asset_count")),
        ("analysis_fingerprint_sha256", manifest.get("analysis_fingerprint_sha256"), evidence.get("analysis_fingerprint_sha256")),
    )
    for field, actual, expected in checks:
        if actual != expected:
            diffs.append({"field": field, "expected": expected, "actual": actual})
    if manifest.get("status") != "PASS":
        diffs.append({"field": "status", "expected": "PASS", "actual": manifest.get("status")})
    if manifest.get("errors"):
        diffs.append({"field": "errors", "expected": [], "actual": manifest.get("errors")})
    if not manifest.get("source_unchanged"):
        diffs.append({"field": "source_unchanged", "expected": True, "actual": manifest.get("source_unchanged")})
    return diffs

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--evidence", type=Path, default=ROOT / "data/audio_lab/al_poc_02_canonical_spectral_evidence.json")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    diffs = compare_spectral_baseline(manifest, evidence)
    result = {
        "schema": "openazrael.audio_lab.al_poc_02_spectral_drift",
        "version": 1,
        "status": "PASS" if not diffs else "FAIL",
        "diffs": diffs,
        "manifest": str(args.manifest),
        "evidence": str(args.evidence)
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
