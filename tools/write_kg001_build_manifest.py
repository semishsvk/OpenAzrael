#!/usr/bin/env python3
"""Write the ignored KG-001 Candidate 2 build-identity manifest.

The manifest contains fingerprints/metadata only. It never embeds or copies
commercial game payloads. CandidateDiagnostics packages the manifest into each
run so bug reports and screenshots can be tied back to one checkout/build.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"data/generated/kg001_candidate_build_manifest.json"

ROOMS=[
    ROOT/"assets/rooms/R1.glb",
    ROOT/"assets/rooms/R7.glb",
    ROOT/"assets/rooms/R8.glb",
]
AUDIO_NAMES=[
    "797TAP.WAV","S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV",
    "S174ELP1.WAV","S174ELP2.WAV","S186.WAV",
]
RUNTIME_SOURCE=[
    ROOT/"project.godot",
    ROOT/"main.tscn",
    ROOT/"export_presets.cfg",
    ROOT/"scripts/player.gd",
    ROOT/"scripts/room_manager.gd",
    ROOT/"scripts/candidate_diagnostics_v116.gd",
    ROOT/"scripts/legacy_event_runner_v87.gd",
    ROOT/"scripts/legacy_ambient_audio.gd",
    ROOT/"scripts/kg001_room_trigger_runner_v110.gd",
    ROOT/"scripts/kg001_audio_runtime_runner_v116.gd",
    ROOT/"scripts/kg001_full_demo_runner_v111.gd",
    ROOT/"scripts/kg001_visual_capture_v117.gd",
    ROOT/"scripts/r8_tapestry_frame.gd",
    ROOT/"tools/restore_candidate_assets.py",
    ROOT/"tools/run_kg001_candidate_v112.py",
    ROOT/"tools/run_kg001_candidate2_windows_v117.ps1",
    ROOT/"tools/promote_kg001_candidate_results_v118.py",
    ROOT/"tools/validate_kg001_candidate2_asset_set_v118.py",
    ROOT/"tools/validate_kg001_test_build_contract_v118.py",
    ROOT/"tools/texture_pipeline/legacy_colorkey.py",
    ROOT/"tools/texture_pipeline/azf_decode_v14.py",
    ROOT/"tools/texture_pipeline/export_xaf_glb_v8.py",
]
SOURCE_CONTRACTS=[
    ROOT/"data/gameplay_event_graph_v87.json",
    ROOT/"data/xaf_trigger_evidence.json",
    ROOT/"data/audio/legacy_world_ir.json",
    ROOT/"data/tests/kg001_audio_runtime_contract_v116.json",
    ROOT/"data/tests/kg001_texture_colorkey_contract_v116.json",
    ROOT/"data/tests/kg001_room_trigger_contract_v110.json",
    ROOT/"data/tests/kg001_test_build_contract_v118.json",
]
EXPECTED_GODOT_VERSION="4.7.2.stable.official.ed1daf0bf"


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path) -> dict:
    return {
        "path":str(path.relative_to(ROOT)).replace("\\","/"),
        "size_bytes":path.stat().st_size,
        "sha256":sha256(path),
    }


def git_head() -> str:
    proc=subprocess.run(
        ["git","rev-parse","HEAD"],
        cwd=ROOT,text=True,capture_output=True,check=False,
    )
    return proc.stdout.strip() if proc.returncode==0 else ""


def godot_version(executable: str | None) -> dict:
    if not executable:
        return {
            "executable":"",
            "version":"",
            "expected":EXPECTED_GODOT_VERSION,
            "matches_expected":False,
            "status":"NOT_PROBED",
        }
    proc=subprocess.run(
        [executable,"--version"],
        cwd=ROOT,text=True,capture_output=True,check=False,
    )
    version=(proc.stdout or proc.stderr).strip()
    return {
        "executable":executable,
        "version":version,
        "expected":EXPECTED_GODOT_VERSION,
        "matches_expected":proc.returncode==0 and version==EXPECTED_GODOT_VERSION,
        "status":"PASS" if proc.returncode==0 and version==EXPECTED_GODOT_VERSION else "FAIL",
    }


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def aggregate(rows: list[dict]) -> str:
    canonical="".join(
        f"{row['path']}\0{row['size_bytes']}\0{row['sha256']}\n"
        for row in sorted(rows,key=lambda row:row["path"])
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def existing_records(paths) -> list[dict]:
    return [file_record(path) for path in paths if path.is_file()]


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--godot",default=None)
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    args=ap.parse_args()

    room_rows=existing_records(ROOMS)
    audio_rows=existing_records(
        [ROOT/"assets/audio"/name for name in AUDIO_NAMES]
    )
    texture_rows=existing_records(
        sorted((ROOT/"assets/textures/classic").glob("*.png"))
        if (ROOT/"assets/textures/classic").is_dir()
        else []
    )
    source_rows=existing_records(SOURCE_CONTRACTS)
    runtime_source_rows=existing_records(RUNTIME_SOURCE)
    colorkey_restore_evidence_path=ROOT/".tmp/kg001/legacy_colorkey_restore.json"
    colorkey_restore_evidence=(
        file_record(colorkey_restore_evidence_path)
        if colorkey_restore_evidence_path.is_file()
        else None
    )
    audio_restore_evidence_path=ROOT/".tmp/kg001/audio_restore_v118.json"
    audio_restore_evidence=(
        file_record(audio_restore_evidence_path)
        if audio_restore_evidence_path.is_file()
        else None
    )
    godot=godot_version(args.godot)
    source_identity_complete=(
        len(runtime_source_rows)==len(RUNTIME_SOURCE)
        and len(source_rows)==len(SOURCE_CONTRACTS)
    )
    asset_counts_complete=(
        len(room_rows)==3
        and len(audio_rows)==len(AUDIO_NAMES)
        and len(texture_rows)==86
    )

    payload={
        "schema":"openazrael.kg001.candidate_build_manifest",
        "version":2,
        "build_id":"KG-001 Candidate 2",
        "checkpoint":"v116-context-v31",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "repository":"semishsvk/OpenAzrael",
        "commit_sha":git_head(),
        "godot":godot,
        "toolchain":{
            "python":platform.python_version(),
            "numpy":package_version("numpy"),
            "Pillow":package_version("Pillow"),
            "trimesh":package_version("trimesh"),
        },
        "assets":{
            "rooms":{
                "expected_count":3,
                "present_count":len(room_rows),
                "rows":room_rows,
                "aggregate_sha256":aggregate(room_rows),
            },
            "audio":{
                "expected_count":len(AUDIO_NAMES),
                "present_count":len(audio_rows),
                "rows":audio_rows,
                "aggregate_sha256":aggregate(audio_rows),
            },
            "classic_textures":{
                "expected_count":86,
                "present_count":len(texture_rows),
                "rows":texture_rows,
                "aggregate_sha256":aggregate(texture_rows),
            },
        },
        "source_contracts":{
            "expected_count":len(SOURCE_CONTRACTS),
            "present_count":len(source_rows),
            "complete":len(source_rows)==len(SOURCE_CONTRACTS),
            "rows":source_rows,
            "aggregate_sha256":aggregate(source_rows),
        },
        "runtime_source_identity":{
            "expected_count":len(RUNTIME_SOURCE),
            "present_count":len(runtime_source_rows),
            "complete":len(runtime_source_rows)==len(RUNTIME_SOURCE),
            "rows":runtime_source_rows,
            "aggregate_sha256":aggregate(runtime_source_rows),
        },
        "restore_evidence":{
            "legacy_colorkey":colorkey_restore_evidence,
            "audio":audio_restore_evidence,
        },
        "asset_counts_complete":asset_counts_complete,
        "source_identity_complete":source_identity_complete,
        "source_safe":True,
        "commercial_asset_bytes_embedded":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    status=(
        "PASS"
        if source_identity_complete
        and (not args.godot or godot.get("status")=="PASS")
        else "FAIL"
    )
    print(json.dumps({
        "status":status,
        "out":str(args.out.relative_to(ROOT)),
        "commit_sha":payload["commit_sha"],
        "godot_status":payload["godot"]["status"],
        "rooms":len(room_rows),
        "audio":len(audio_rows),
        "textures":len(texture_rows),
        "asset_counts_complete":asset_counts_complete,
        "source_identity_complete":source_identity_complete,
        "runtime_source_aggregate_sha256":aggregate(runtime_source_rows),
        "colorkey_restore_evidence_present":colorkey_restore_evidence is not None,
        "audio_restore_evidence_present":audio_restore_evidence is not None,
    },indent=2))
    return 0 if status=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
