#!/usr/bin/env python3
"""Run the complete AL-POC-01 source-safe inventory, validation and mapping audit."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.audio_lab.oa_audio_scan import main as scan_main
from tools.audio_lab.oa_audio_validate import validate
from tools.audio_lab.oa_audio_reference_audit import build_audit, load_json

ROOT = Path(__file__).resolve().parents[2]

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_root", type=Path)
    ap.add_argument("--output-dir", type=Path, default=ROOT / ".tmp/audio_lab/al_poc_01")
    ap.add_argument("--reference-root", type=Path, default=ROOT)
    ap.add_argument("--fingerprints", type=Path, default=ROOT / "data/backup/source_fingerprints.json")
    ap.add_argument("--legacy-ir", type=Path, default=ROOT / "data/audio/legacy_world_ir.json")
    ap.add_argument("--event-graph", type=Path, default=ROOT / "data/gameplay_event_graph_v87.json")
    args = ap.parse_args(argv)

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    scan_rc = scan_main([
        str(args.source_root),
        "--output-dir", str(out),
        "--reference-root", str(args.reference_root),
        "--fingerprints", str(args.fingerprints),
        "--legacy-ir", str(args.legacy_ir),
    ])

    manifest_path = out / "audio_manifest.json"
    if not manifest_path.is_file():
        summary = {
            "schema": "openazrael.audio_lab.al_poc_01_summary",
            "version": 1,
            "status": "FAIL",
            "scan_exit_code": scan_rc,
            "reason": "scanner did not produce audio_manifest.json",
        }
        (out / "al_poc_01_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 2

    manifest = load_json(manifest_path)
    validation_errors = validate(manifest, args.source_root)

    reference_report = build_audit(
        manifest,
        load_json(args.legacy_ir),
        load_json(args.event_graph),
    )
    reference_path = out / "audio_reference_report.json"
    reference_path.write_text(json.dumps(reference_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    qa = manifest.get("qa", {})
    gates = {
        "scan_pass": scan_rc == 0,
        "manifest_validation_pass": not validation_errors,
        "expected_corpus_complete": bool(qa.get("expected_corpus_complete")),
        "reference_integrity_pass": reference_report.get("status") == "PASS",
        "source_digest_present": bool(manifest.get("source_tree_sha256")),
        "inventory_count_matches": manifest.get("source_file_count") == len(manifest.get("assets", [])),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    summary = {
        "schema": "openazrael.audio_lab.al_poc_01_summary",
        "version": 1,
        "status": status,
        "gates": gates,
        "scan_exit_code": scan_rc,
        "validation_errors": validation_errors,
        "inventory": {
            "assets": len(manifest.get("assets", [])),
            "expected_corpus": qa.get("expected_corpus_count", 0),
            "runtime_mapped": reference_report.get("summary", {}).get("mapped_assets", 0),
            "runtime_unmapped": reference_report.get("summary", {}).get("unmapped_assets", 0),
            "broken_references": reference_report.get("summary", {}).get("broken_reference_count", 0),
        },
        "artifacts": {
            "manifest": "audio_manifest.json",
            "inventory_csv": "audio_inventory.csv",
            "qa_report": "audio_qa_report.json",
            "html_review": "audio_qa_report.html",
            "reference_report": "audio_reference_report.json",
        },
    }
    (out / "al_poc_01_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if status == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
