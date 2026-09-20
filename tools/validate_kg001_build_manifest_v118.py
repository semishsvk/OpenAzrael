#!/usr/bin/env python3
"""Validate the generated Candidate 2 build-manifest v2 contract."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"data/generated/kg001_candidate_build_manifest.json"

def git_head() -> str:
    proc=subprocess.run(
        ["git","rev-parse","HEAD"],
        cwd=ROOT,text=True,capture_output=True,check=False,
    )
    return proc.stdout.strip() if proc.returncode==0 else ""

if not MANIFEST.is_file():
    print("OpenAzrael build-manifest v118 validation: FAIL")
    print(" - generated build manifest missing")
    sys.exit(1)

m=json.loads(MANIFEST.read_text(encoding="utf-8"))
assets=m.get("assets",{})
rooms=assets.get("rooms",{})
audio=assets.get("audio",{})
textures=assets.get("classic_textures",{})
source=m.get("source_contracts",{})
runtime=m.get("runtime_source_identity",{})
runtime_paths={
    str(row.get("path"))
    for row in runtime.get("rows",[])
    if isinstance(row,dict)
}
required_runtime_paths={
    "project.godot",
    "main.tscn",
    "export_presets.cfg",
    "scripts/player.gd",
    "scripts/room_manager.gd",
    "scripts/candidate_diagnostics_v116.gd",
    "scripts/kg001_room_trigger_runner_v110.gd",
    "scripts/kg001_audio_runtime_runner_v116.gd",
    "scripts/kg001_full_demo_runner_v111.gd",
    "scripts/kg001_visual_capture_v117.gd",
    "tools/restore_candidate_assets.py",
    "tools/run_kg001_candidate_v112.py",
    "tools/validate_kg001_candidate2_asset_set_v118.py",
}
checks={
    "schema":m.get("schema")=="openazrael.kg001.candidate_build_manifest",
    "version":m.get("version")==2,
    "build_id":m.get("build_id")=="KG-001 Candidate 2",
    "checkpoint":m.get("checkpoint")=="v116-context-v31",
    "commit_matches_head":m.get("commit_sha")==git_head() and bool(git_head()),
    "room_expected_count":rooms.get("expected_count")==3,
    "audio_expected_count":audio.get("expected_count")==8,
    "classic_texture_expected_count":textures.get("expected_count")==86,
    "source_contracts_complete":source.get("complete") is True
        and source.get("present_count")==source.get("expected_count"),
    "runtime_source_complete":runtime.get("complete") is True
        and runtime.get("present_count")==runtime.get("expected_count"),
    "runtime_paths_present":required_runtime_paths.issubset(runtime_paths),
    "runtime_aggregate_sha256":isinstance(
        runtime.get("aggregate_sha256"),str
    ) and len(runtime.get("aggregate_sha256",""))==64,
    "source_aggregate_sha256":isinstance(
        source.get("aggregate_sha256"),str
    ) and len(source.get("aggregate_sha256",""))==64,
    "source_identity_complete":m.get("source_identity_complete") is True,
    "asset_counts_complete_consistent":m.get("asset_counts_complete") is (
        rooms.get("present_count")==3
        and audio.get("present_count")==8
        and textures.get("present_count")==86
    ),
    "source_safe":m.get("source_safe") is True,
    "no_commercial_bytes":m.get("commercial_asset_bytes_embedded") is False,
}
godot=m.get("godot",{})
if godot.get("status")=="PASS":
    checks["godot_exact"]=(
        godot.get("version")=="4.7.2.stable.official.ed1daf0bf"
        and godot.get("matches_expected") is True
    )

failed=[name for name,value in checks.items() if not value]
result={
    "schema":"openazrael.kg001.candidate_build_manifest_validation",
    "version":118,
    "status":"PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
    "asset_counts_complete":m.get("asset_counts_complete"),
    "source_identity_complete":m.get("source_identity_complete"),
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
