#!/usr/bin/env python3
"""Audit recovered audio mapping evidence using repository metadata only, without source audio bytes."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.audio_lab.common import scan_references
from tools.audio_lab.oa_audio_reference_audit import build_audit, load_json

ROOT = Path(__file__).resolve().parents[2]

def build_virtual_manifest(legacy_ir: dict, reference_root: Path) -> dict:
    sounds = sorted(
        legacy_ir.get("audio", {}).get("sounds", []),
        key=lambda s: str(s.get("filename", "")).casefold(),
    )
    names = [str(s.get("filename", "")) for s in sounds if str(s.get("filename", ""))]
    refs = scan_references(reference_root.resolve(), names)
    assets = []
    for sound in sounds:
        name = str(sound.get("filename", "")).strip()
        if not name:
            continue
        assets.append({
            "path": name,
            "filename": name,
            "sha256": sound.get("sha256"),
            "references": refs.get(name, []),
            "expected": {
                "known": True,
                "sha256": sound.get("sha256"),
                "evidence": ["legacy_world_ir"],
            },
            "analysis": {
                "channels": sound.get("channels"),
                "sample_rate": sound.get("sample_rate"),
                "sample_width_bits": sound.get("sample_width_bits"),
                "duration_seconds": sound.get("duration_seconds"),
            },
            "issues": [],
        })
    return {
        "schema": "openazrael.audio_lab.virtual_repository_manifest",
        "version": 1,
        "evidence_mode": "REPOSITORY_ONLY_NO_SOURCE_BYTES",
        "assets": assets,
    }

def build_repo_evidence(reference_root: Path, legacy_ir: dict, event_graph: dict) -> dict:
    virtual = build_virtual_manifest(legacy_ir, reference_root)
    audit = build_audit(virtual, legacy_ir, event_graph)
    return {
        "schema": "openazrael.audio_lab.repo_evidence",
        "version": 1,
        "evidence_mode": "REPOSITORY_ONLY_NO_SOURCE_BYTES",
        "limitations": [
            "does not prove source audio files are present",
            "does not hash or decode source audio bytes",
            "does not prove human audibility",
            "does not prove original Miles playback parity",
        ],
        "status": audit.get("status"),
        "summary": audit.get("summary", {}),
        "broken_references": audit.get("broken_references", []),
        "assets": audit.get("assets", []),
    }

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference-root", type=Path, default=ROOT)
    ap.add_argument("--legacy-ir", type=Path, default=ROOT / "data/audio/legacy_world_ir.json")
    ap.add_argument("--event-graph", type=Path, default=ROOT / "data/gameplay_event_graph_v87.json")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    report = build_repo_evidence(
        args.reference_root,
        load_json(args.legacy_ir),
        load_json(args.event_graph),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "evidence_mode": report["evidence_mode"],
        **report["summary"],
        "output": str(args.output) if args.output else None,
    }, indent=2))
    return 0 if report["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
