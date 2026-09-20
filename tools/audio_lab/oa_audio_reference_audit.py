#!/usr/bin/env python3
"""Classify OpenAzrael audio runtime mappings and detect broken audio references."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[2]

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _production_direct_ref(ref: str) -> bool:
    folded = ref.casefold()
    if folded.startswith("data/gameplay_event_graph"):
        return False
    if not folded.startswith(("scripts/", "main.tscn")):
        return False
    diagnostic_tokens = (
        "kg001_", "_runner", "candidate_diagnostics", "headless",
        "validate_", "test_", "diagnostic",
    )
    return not any(token in folded for token in diagnostic_tokens)

def _diagnostic_ref(ref: str) -> bool:
    folded = ref.casefold()
    if folded.startswith(("tests/", "tools/")):
        return True
    if folded.startswith("scripts/"):
        diagnostic_tokens = (
            "kg001_", "_runner", "candidate_diagnostics", "headless",
            "validate_", "test_", "diagnostic",
        )
        return any(token in folded for token in diagnostic_tokens)
    return False

def _documentation_ref(ref: str) -> bool:
    folded = ref.casefold()
    return folded.startswith("docs/") or folded.endswith(".md") or folded.startswith("readme")

def _mapping_disposition(expected_known: bool, mappings: list[dict]) -> tuple[str, str]:
    if mappings:
        return "MAPPED", "OK"
    if expected_known:
        return "EXPECTED_UNMAPPED", "REVIEW"
    return "UNEXPECTED_ORPHAN", "HIGH_REVIEW"

def build_audit(manifest: dict, legacy_ir: dict, event_graph: dict) -> dict:
    assets = manifest.get("assets", [])
    discovered = {str(a.get("filename", "")).casefold(): str(a.get("filename", "")) for a in assets}
    mappings: dict[str, list[dict]] = defaultdict(list)
    broken: list[dict] = []

    ir_sounds = {
        str(s.get("filename", "")).casefold(): s
        for s in legacy_ir.get("audio", {}).get("sounds", [])
        if str(s.get("filename", ""))
    }

    for emitter in legacy_ir.get("audio", {}).get("ambient_emitters", []):
        name = str(emitter.get("sample", "")).strip()
        if not name:
            continue
        key = name.casefold()
        detail = {
            "type": "POSITIONAL_AMBIENT",
            "id": str(emitter.get("emitter_id", "")),
            "room_id": emitter.get("room_id"),
            "source": str(emitter.get("source", {}).get("file", "")),
        }
        mappings[key].append(detail)
        if key not in discovered:
            broken.append({
                "code": "AUDREF001_MISSING_AMBIENT_ASSET",
                "asset": name,
                "mapping": detail,
            })
        if key not in ir_sounds:
            broken.append({
                "code": "AUDREF002_AMBIENT_NOT_IN_SOUND_CORPUS",
                "asset": name,
                "mapping": detail,
            })

    for graph_id, graph in sorted(event_graph.get("graphs", {}).items()):
        for index, action in enumerate(graph.get("actions", [])):
            if str(action.get("op", "")) != "play_sound":
                continue
            name = str(action.get("asset", "")).strip()
            if not name:
                broken.append({
                    "code": "AUDREF003_EMPTY_EVENT_ASSET",
                    "graph": graph_id,
                    "action_index": index,
                })
                continue
            key = name.casefold()
            detail = {
                "type": "EVENT_GRAPH",
                "graph": graph_id,
                "action_index": index,
            }
            mappings[key].append(detail)
            if key not in discovered:
                broken.append({
                    "code": "AUDREF004_MISSING_EVENT_ASSET",
                    "asset": name,
                    "mapping": detail,
                })

    for asset in assets:
        name = str(asset.get("filename", ""))
        key = name.casefold()
        for ref in asset.get("references", []):
            if _production_direct_ref(str(ref)):
                mappings[key].append({
                    "type": "DIRECT_RUNTIME_LITERAL",
                    "path": str(ref),
                })

    rows = []
    for asset in sorted(assets, key=lambda a: str(a.get("path", "")).casefold()):
        name = str(asset.get("filename", ""))
        key = name.casefold()
        asset_mappings = mappings.get(key, [])
        unique: list[dict] = []
        seen = set()
        for item in asset_mappings:
            marker = json.dumps(item, sort_keys=True)
            if marker not in seen:
                seen.add(marker)
                unique.append(item)

        refs = [str(r) for r in asset.get("references", [])]
        diagnostic_refs = sorted({r for r in refs if _diagnostic_ref(r)}, key=str.casefold)
        documentation_refs = sorted({r for r in refs if _documentation_ref(r)}, key=str.casefold)
        other_refs = sorted({
            r for r in refs
            if r not in diagnostic_refs
            and r not in documentation_refs
            and not _production_direct_ref(r)
        }, key=str.casefold)

        expected_known = bool(asset.get("expected", {}).get("known"))
        disposition, review_priority = _mapping_disposition(expected_known, unique)
        rows.append({
            "path": asset.get("path"),
            "filename": name,
            "sha256": asset.get("sha256"),
            "expected_source": expected_known,
            "mapping_status": disposition,
            "review_priority": review_priority,
            "mapping_types": sorted({m["type"] for m in unique}),
            "mappings": unique,
            "diagnostic_references": diagnostic_refs,
            "documentation_references": documentation_refs,
            "other_references": other_refs,
        })

    mapped = [r for r in rows if r["mapping_status"] == "MAPPED"]
    expected_unmapped = [r for r in rows if r["mapping_status"] == "EXPECTED_UNMAPPED"]
    unexpected_orphans = [r for r in rows if r["mapping_status"] == "UNEXPECTED_ORPHAN"]
    by_type: dict[str, int] = defaultdict(int)
    names_by_type: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for mapping_type in row["mapping_types"]:
            by_type[mapping_type] += 1
            names_by_type[mapping_type].append(row["filename"])

    return {
        "schema": "openazrael.audio_lab.reference_audit",
        "version": 2,
        "status": "PASS" if not broken else "FAIL",
        "policy": {
            "expected_unmapped": "review item, not automatically an orphan or a failure",
            "unexpected_orphan": "high-priority review item; do not delete or alter automatically",
            "diagnostic_reference": "does not count as production runtime mapping",
        },
        "summary": {
            "asset_count": len(rows),
            "mapped_assets": len(mapped),
            "unmapped_assets": len(expected_unmapped) + len(unexpected_orphans),
            "expected_unmapped_assets": len(expected_unmapped),
            "unexpected_orphan_assets": len(unexpected_orphans),
            "unmapped_asset_names": [r["filename"] for r in expected_unmapped + unexpected_orphans],
            "expected_unmapped_asset_names": [r["filename"] for r in expected_unmapped],
            "unexpected_orphan_asset_names": [r["filename"] for r in unexpected_orphans],
            "mapped_asset_names": [r["filename"] for r in mapped],
            "mapped_assets_by_type": dict(sorted(by_type.items())),
            "mapped_asset_names_by_type": {
                key: sorted(values, key=str.casefold)
                for key, values in sorted(names_by_type.items())
            },
            "broken_reference_count": len(broken),
        },
        "broken_references": broken,
        "assets": rows,
    }

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--legacy-ir", type=Path, default=ROOT / "data/audio/legacy_world_ir.json")
    ap.add_argument("--event-graph", type=Path, default=ROOT / "data/gameplay_event_graph_v87.json")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    manifest = load_json(args.manifest)
    report = build_audit(manifest, load_json(args.legacy_ir), load_json(args.event_graph))
    output = args.output or args.manifest.with_name("audio_reference_report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        **report["summary"],
        "output": str(output),
    }, indent=2))
    return 0 if report["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
