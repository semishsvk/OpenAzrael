#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json
from oa_tex_stage_gate import DEFAULT_RUN_ROOT, evidence_snapshot, preset_record

DEFAULT_SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
DEFAULT_OUT = ROOT / ".local/texture_lab/runtime_manifests/review_current.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def res_path(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"review candidate must remain inside project tree: {path}") from exc
    return "res://" + str(rel).replace("\\", "/")


def file_fields(path: Path) -> dict:
    present = path.is_file()
    return {
        "file_present": present,
        "sha256": sha256_file(path) if present else None,
        "size_bytes": path.stat().st_size if present else None,
        "integrity_ok": present,
    }


def build_review_profile(
    preset: str,
    run_root: Path,
    selection: dict,
) -> dict:
    evidence = evidence_snapshot(preset, run_root)
    if evidence.get("status") != "PASS":
        raise SystemExit(
            "review profile requires complete current stage evidence; "
            f"status={evidence.get('status')}"
        )

    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_root / preset
    pack_path = run_dir / f"ai_{mode}_review_pack.json"
    pack = load_json(pack_path)
    reviewed = {
        str(row["id"]): row
        for row in pack.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    }
    stage_ids = [str(v) for v in spec.get("textures", [])]

    rows = []
    missing = []
    for entry in selection.get("textures", []):
        texture_id = str(entry["id"])
        base = {
            "id": texture_id,
            "room": entry.get("room"),
            "content_class": entry.get("content_class"),
            "expected_size": entry.get("expected_size"),
            "profile": f"review:{preset}",
            "automatic_promotion": False,
        }
        if texture_id in stage_ids:
            pack_row = reviewed.get(texture_id)
            candidate = pack_row.get("candidate") if isinstance(pack_row, dict) else None
            if not isinstance(candidate, dict):
                raise SystemExit(f"{texture_id}: candidate missing from review pack")
            candidate_path = Path(str(candidate.get("path", "")))
            current = file_fields(candidate_path)
            current["integrity_ok"] = (
                current["file_present"]
                and current["sha256"] == candidate.get("sha256")
                and current["size_bytes"] == candidate.get("size_bytes")
            )
            row = {
                **base,
                "resolved_tier": "ai_restored" if mode == "restored" else "ai_recreated",
                "path": res_path(candidate_path),
                "resolution_reason": "current_stage_review_candidate",
                **current,
            }
        else:
            classic = ROOT / "assets/textures/classic" / f"{texture_id}.png"
            row = {
                **base,
                "resolved_tier": "classic",
                "path": f"res://assets/textures/classic/{texture_id}.png",
                "resolution_reason": "review_profile_classic_fallback",
                **file_fields(classic),
            }

        if not row["file_present"] or not row["integrity_ok"]:
            missing.append(texture_id)
        rows.append(row)

    runtime_ready = not missing
    return {
        "schema": "openazrael.texture_lab.review_texture_manifest.v1",
        "profile": f"review:{preset}",
        "preset": preset,
        "mode": mode,
        "status": "READY_FOR_MANUAL_REVIEW" if runtime_ready else "HOLD",
        "runtime_ready": runtime_ready,
        "automatic_promotion": False,
        "export_allowed": False,
        "stage_evidence_status": evidence.get("status"),
        "stage_texture_ids": stage_ids,
        "texture_count": len(rows),
        "missing_or_stale_ids": missing,
        "textures": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an editor-only Godot review profile from an immutable named "
            "Texture Lab stage. This manifest is never valid for export."
        )
    )
    parser.add_argument("preset")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    manifest = build_review_profile(
        args.preset,
        args.run_root,
        load_json(args.selection),
    )
    write_json(args.out, manifest)
    print(
        f"{'PASS' if manifest['runtime_ready'] else 'HOLD'} review_profile "
        f"preset={args.preset} out={args.out}"
    )
    return 0 if manifest["runtime_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
