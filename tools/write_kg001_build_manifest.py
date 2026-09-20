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
    "S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV",
    "S174ELP1.WAV","S174ELP2.WAV","S186.WAV",
]
SOURCE_CONTRACTS=[
    ROOT/"data/gameplay_event_graph_v87.json",
    ROOT/"data/xaf_trigger_evidence.json",
    ROOT/"data/audio/legacy_world_ir.json",
    ROOT/"data/tests/kg001_audio_runtime_contract_v116.json",
    ROOT/"data/tests/kg001_texture_colorkey_contract_v116.json",
    ROOT/"data/tests/kg001_room_trigger_contract_v110.json",
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

    payload={
        "schema":"openazrael.kg001.candidate_build_manifest",
        "version":1,
        "build_id":"KG-001 Candidate 2",
        "checkpoint":"v116-context-v31",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "repository":"semishsvk/OpenAzrael",
        "commit_sha":git_head(),
        "godot":godot_version(args.godot),
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
            "rows":source_rows,
            "aggregate_sha256":aggregate(source_rows),
        },
        "source_safe":True,
        "commercial_asset_bytes_embedded":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"PASS",
        "out":str(args.out.relative_to(ROOT)),
        "commit_sha":payload["commit_sha"],
        "godot_status":payload["godot"]["status"],
        "rooms":len(room_rows),
        "audio":len(audio_rows),
        "textures":len(texture_rows),
    },indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
