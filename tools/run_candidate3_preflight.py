#!/usr/bin/env python3
"""Candidate 3 pre-build gate.

Runs the complete asset-backed KG-001 fresh-checkout suite and emits a local,
Git-ignored PASS receipt bound to the exact Git SHA, Godot version and restored
runtime asset fingerprints. A stale receipt is deleted before every attempt.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.remaster_framework.source_registry import resolve_source
from tools.kg001_gate_manifest import (
    CANDIDATE3_REQUIRED_RUNTIME,
    CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE,
    PPPV_EVIDENCE_FILES,
)
TMP = ROOT / ".tmp/kg001"
RECEIPT = TMP / "candidate3_preflight_receipt.json"
RESTORE_RECEIPT = TMP / "candidate_asset_restore_v177.json"
CANDIDATE_RESULT = TMP / "kg001_candidate_v112.json"
FRESH_RESULT = TMP / "kg001_fresh_checkout.json"
VISUAL_RESULT = TMP / "kg001_visual_v126_runtime.json"
FORENSIC_PREFLIGHT = TMP / "room_forensic_report_v131_preflight.json"
GENERATED_METADATA = {
    "fidelity_v124": ROOT / "data/runtime_generated/demo_room_fidelity_v124.json",
    "state_matrix_v127": ROOT / "data/runtime_generated/kg001_state_matrix_v127.json",
    "asset_manifest_v128": ROOT / "data/runtime_generated/runtime_asset_manifest_v128.json",
    "texture_orientation_v133": ROOT / "data/runtime_generated/demo_texture_orientation_v133.json",
}
PPPV_REQUIRED_EVIDENCE = {
    name: ROOT / rel_path
    for name, rel_path in PPPV_EVIDENCE_FILES.items()
}
REQUIRED_RUNTIME = CANDIDATE3_REQUIRED_RUNTIME

REQUIRED_SENTINELS = (
    ROOT / "assets/rooms/R1.glb",
    ROOT / "assets/rooms/R7.glb",
    ROOT / "assets/rooms/R8.glb",
    ROOT / "assets/audio/979TONGS.WAV",
    ROOT / "assets/ui/mice/POINTER.png",
    ROOT / "assets/ui/mice/TAKE.png",
    ROOT / "assets/ui/legacy_menu/HUD3.png",
    ROOT / "assets/ui/legacy_menu/SAVE13.png",
    ROOT / "assets/ui/legacy_menu/TITLE.png",
)
RUNTIME_ASSET_ROOTS = (
    ROOT / "assets/rooms",
    ROOT / "assets/audio",
    ROOT / "assets/textures/classic",
    ROOT / "assets/ui/mice",
    ROOT / "assets/ui/legacy_menu",
)

def runtime_asset_files() -> list[Path]:
    files: list[Path] = []
    for root in RUNTIME_ASSET_ROOTS:
        if root.is_dir():
            files.extend(p for p in root.rglob("*") if p.is_file())
    return sorted(set(files), key=lambda p: str(p.relative_to(ROOT)).lower())

def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

def parse_marker(output: str, marker: str) -> dict:
    for line in reversed(output.splitlines()):
        if marker in line:
            payload = line.split(marker, 1)[1].strip()
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return {"status": "FAIL", "parse_error": payload}
    return {"status": "FAIL", "error": "result marker missing"}


def engine_errors(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.lstrip().startswith(("ERROR:", "SCRIPT ERROR:"))]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git_head() -> str:
    p = run(["git", "rev-parse", "HEAD"])
    return p.stdout.strip() if p.returncode == 0 else ""

def git_clean() -> bool:
    p = run(["git", "status", "--porcelain", "--untracked-files=normal"])
    return p.returncode == 0 and p.stdout.strip() == ""

def find_godot(explicit: str | None) -> str | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("GODOT_BIN"):
        candidates.append(os.environ["GODOT_BIN"])
    candidates += ["godot4", "godot"]
    for candidate in candidates:
        p = Path(candidate)
        if p.is_file():
            return str(p.resolve())
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None

def fail(reason: str, details: dict | None = None) -> int:
    RECEIPT.unlink(missing_ok=True)
    payload = {
        "schema": "openazrael.kg001.candidate3_preflight",
        "version": 2,
        "status": "FAIL",
        "export_allowed": False,
        "reason": reason,
    }
    if details:
        payload["details"] = details
    print(json.dumps(payload, indent=2))
    return 1

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--godot", help="Godot executable; otherwise GODOT_BIN/godot4/godot are tried.")
    ap.add_argument(
        "--demo-dir",
        type=Path,
        help="Optional extracted official ATDEMO directory. If supplied, restore ignored Candidate assets first.",
    )
    args = ap.parse_args()

    TMP.mkdir(parents=True, exist_ok=True)
    RECEIPT.unlink(missing_ok=True)

    if not git_clean():
        return fail("DIRTY_GIT_BEFORE_PREFLIGHT")

    head_before = git_head()
    if not head_before:
        return fail("GIT_HEAD_UNAVAILABLE")

    restore_source = args.demo_dir.resolve() if args.demo_dir is not None else None
    sentinels_missing_before_restore = any(
        not path.is_file() for path in REQUIRED_SENTINELS
    )
    if restore_source is None and sentinels_missing_before_restore:
        try:
            restore_source = resolve_source("demo")
        except Exception as exc:
            return fail(
                "DEMO_SOURCE_NOT_REGISTERED_OR_INVALID",
                {
                    "error": str(exc),
                    "hint": (
                        "Run: python tools/bootstrap_openazrael_sources.py "
                        "register demo <atdemo.zip-or-extracted-dir>"
                    ),
                },
            )

    if restore_source is not None:
        restore = run([
            sys.executable,
            "tools/restore_candidate_assets.py",
            str(restore_source),
        ])
        if restore.returncode != 0:
            return fail(
                "ASSET_RESTORE_FAILED",
                {"returncode": restore.returncode, "output_tail": restore.stdout[-12000:]},
            )
        if not git_clean():
            return fail(
                "ASSET_RESTORE_CHANGED_TRACKED_SOURCE",
                {"note": "Restoration may create ignored runtime assets, but tracked source must remain byte-stable."},
            )

    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_SENTINELS if not p.is_file()]
    if missing:
        return fail("REQUIRED_RUNTIME_ASSETS_MISSING", {"missing": missing})

    if not RESTORE_RECEIPT.is_file():
        return fail("COMPLETE_ASSET_RESTORE_RECEIPT_MISSING", {
            "hint": "Run tools/restore_candidate_assets.py against the canonical demo corpus."
        })
    try:
        restore_receipt = json.loads(RESTORE_RECEIPT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail("COMPLETE_ASSET_RESTORE_RECEIPT_INVALID", {"error": str(exc)})
    if (
        restore_receipt.get("schema") != "openazrael.kg001.candidate_asset_restore"
        or restore_receipt.get("version") != 177
        or restore_receipt.get("status") != "PASS"
    ):
        return fail("COMPLETE_ASSET_RESTORE_NOT_PASS")

    asset_files = runtime_asset_files()
    classic_pngs = [
        p for p in asset_files
        if p.parent == ROOT / "assets/textures/classic" and p.suffix.lower() == ".png"
    ]
    room_glbs = [
        p for p in asset_files
        if p.parent == ROOT / "assets/rooms" and p.suffix.lower() == ".glb"
    ]
    audio_files = [
        p for p in asset_files
        if p.parent == ROOT / "assets/audio"
    ]
    cursor_pngs = [
        p for p in asset_files
        if p.parent == ROOT / "assets/ui/mice" and p.suffix.lower() == ".png"
    ]
    menu_pngs = [
        p for p in asset_files
        if p.parent == ROOT / "assets/ui/legacy_menu" and p.suffix.lower() == ".png"
    ]
    observed_restore_assets = {
        str(p.relative_to(ROOT)).replace("\\\\","/"): {
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        } for p in asset_files
    }
    observed_restore_digest = hashlib.sha256(
        json.dumps(observed_restore_assets, sort_keys=True, separators=(",",":")).encode("utf-8")
    ).hexdigest()
    if (
        restore_receipt.get("asset_file_count") != len(observed_restore_assets)
        or restore_receipt.get("asset_identity_sha256") != observed_restore_digest
        or restore_receipt.get("assets") != observed_restore_assets
    ):
        return fail("RUNTIME_ASSETS_CHANGED_OR_MIXED_SINCE_RESTORE")

    if len(classic_pngs) != 86 or len(room_glbs) < 3 or not audio_files or len(cursor_pngs) != 35 or len(menu_pngs) != 42:
        return fail(
            "RUNTIME_ASSET_CORPUS_INCOMPLETE",
            {
                "classic_png_count": len(classic_pngs),
                "room_glb_count": len(room_glbs),
                "audio_file_count": len(audio_files),
                "cursor_png_count": len(cursor_pngs),
                "menu_png_count": len(menu_pngs),
            },
        )

    godot = find_godot(args.godot)
    if not godot:
        return fail("GODOT_NOT_FOUND")

    cmd = [
        sys.executable,
        "tools/run_kg001_candidate_v112.py",
        "--fresh-checkout",
        "--godot",
        godot,
    ]
    suite = run(cmd)
    if suite.returncode != 0:
        return fail(
            "KG001_FRESH_CHECKOUT_FAILED",
            {"returncode": suite.returncode, "output_tail": suite.stdout[-20000:]},
        )

    if not CANDIDATE_RESULT.is_file() or not FRESH_RESULT.is_file():
        return fail("PREFLIGHT_EVIDENCE_MISSING")

    missing_generated = [
        str(path.relative_to(ROOT))
        for path in GENERATED_METADATA.values()
        if not path.is_file()
    ]
    if missing_generated:
        return fail("GENERATED_FIDELITY_METADATA_MISSING", {"missing": missing_generated})

    visual_run = run([
        godot,
        "--path",
        str(ROOT),
        "--script",
        "res://scripts/kg001_visual_census_runner_v126.gd",
    ])
    visual_result = parse_marker(
        visual_run.stdout,
        "OPENAZRAEL_KG001_VISUAL_CENSUS_V126",
    )
    visual_errors = engine_errors(visual_run.stdout)
    if visual_run.returncode != 0 or visual_errors or visual_result.get("status") != "PASS":
        return fail(
            "GRAPHICAL_VISUAL_CENSUS_V126_FAILED",
            {
                "returncode": visual_run.returncode,
                "status": visual_result.get("status"),
                "engine_errors": visual_errors,
                "output_tail": visual_run.stdout[-20000:],
            },
        )
    VISUAL_RESULT.write_text(
        json.dumps(visual_result, indent=2) + "\n",
        encoding="utf-8",
    )

    forensic_run = run([
        sys.executable,
        "tools/build_room_forensic_report_v131.py",
        "--phase",
        "preflight",
        "--out",
        str(FORENSIC_PREFLIGHT),
    ])
    if forensic_run.returncode != 0 or not FORENSIC_PREFLIGHT.is_file():
        return fail(
            "ROOM_FORENSIC_REPORT_V131_FAILED",
            {"output_tail": forensic_run.stdout[-20000:]},
        )
    try:
        forensic_payload = json.loads(FORENSIC_PREFLIGHT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail("ROOM_FORENSIC_REPORT_V131_INVALID", {"error": str(exc)})
    if (
        forensic_payload.get("status") != "PASS"
        or any(
            forensic_payload.get("rooms", {}).get(room, {}).get("status") != "PASS"
            for room in ("R1", "R7", "R8")
        )
    ):
        return fail("ROOM_FORENSIC_REPORT_V131_NOT_PASS", forensic_payload)

    pppv_cmd = [
        sys.executable,
        "tools/run_candidate3_pppv_v2.py",
        "--fresh-checkout",
        "--godot",
        godot,
    ]
    pppv_run = run(pppv_cmd)
    if pppv_run.returncode != 0:
        return fail(
            "PPPV_V2_RUNTIME_FAILED",
            {"returncode": pppv_run.returncode, "output_tail": pppv_run.stdout[-20000:]},
        )

    missing_pppv = [
        str(p.relative_to(ROOT))
        for p in PPPV_REQUIRED_EVIDENCE.values()
        if not p.is_file()
    ]
    if missing_pppv:
        return fail("PPPV_V2_EVIDENCE_MISSING", {"missing": missing_pppv})

    pppv_evidence = {
        name: json.loads(p.read_text(encoding="utf-8"))
        for name, p in PPPV_REQUIRED_EVIDENCE.items()
    }
    pppv_status = {
        name: str(payload.get("status", "UNKNOWN"))
        for name, payload in pppv_evidence.items()
    }
    if not all(status == "PASS" for status in pppv_status.values()):
        return fail("PPPV_V2_INVARIANT_FAILED", {"status": pppv_status})

    candidate = json.loads(CANDIDATE_RESULT.read_text(encoding="utf-8"))
    fresh = json.loads(FRESH_RESULT.read_text(encoding="utf-8"))
    head_after = git_head()

    runtime_status = fresh.get("runtime_status", {})
    runtime_ok = (
        isinstance(runtime_status, dict)
        and all(runtime_status.get(name) == "PASS" for name in REQUIRED_RUNTIME)
    )
    if not (
        head_after == head_before
        and git_clean()
        and candidate.get("status") == "PASS"
        and candidate.get("commit_sha") == head_before
        and fresh.get("status") == "PASS"
        and fresh.get("commit_sha") == head_before
        and fresh.get("source_validators_pass") is True
        and fresh.get("godot_import_status") == "PASS"
        and runtime_ok
    ):
        return fail(
            "PREFLIGHT_INVARIANT_FAILED",
            {
                "head_before": head_before,
                "head_after": head_after,
                "git_clean": git_clean(),
                "candidate_status": candidate.get("status"),
                "fresh_status": fresh.get("status"),
                "source_validators_pass": fresh.get("source_validators_pass"),
                "godot_import_status": fresh.get("godot_import_status"),
                "runtime_status": runtime_status,
            },
        )

    asset_files_after = runtime_asset_files()
    observed_assets_after = {
        str(p.relative_to(ROOT)).replace("\\\\","/"): {
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        } for p in asset_files_after
    }
    observed_digest_after = hashlib.sha256(
        json.dumps(observed_assets_after, sort_keys=True, separators=(",",":")).encode("utf-8")
    ).hexdigest()
    if (
        observed_assets_after != observed_restore_assets
        or observed_digest_after != observed_restore_digest
    ):
        return fail("RUNTIME_ASSETS_CHANGED_DURING_PREFLIGHT", {
            "before_file_count": len(observed_restore_assets),
            "after_file_count": len(observed_assets_after),
            "before_sha256": observed_restore_digest,
            "after_sha256": observed_digest_after,
            "added": sorted(set(observed_assets_after)-set(observed_restore_assets)),
            "removed": sorted(set(observed_restore_assets)-set(observed_assets_after)),
            "changed": sorted(
                key for key in set(observed_assets_after)&set(observed_restore_assets)
                if observed_assets_after[key] != observed_restore_assets[key]
            ),
        })

    ver = run([godot, "--version"])
    godot_version = ver.stdout.strip()
    if ver.returncode != 0 or not godot_version:
        return fail("GODOT_VERSION_UNAVAILABLE")

    receipt = {
        "schema": "openazrael.kg001.candidate3_preflight",
        "version": 2,
        "status": "PASS",
        "candidate": "KG-001 Candidate 3",
        "export_allowed": True,
        "commit_sha": head_before,
        "git_clean_after": True,
        "godot_executable": godot,
        "godot_version": godot_version,
        "source_validators": "PASS",
        "godot_import": "PASS",
        "runtime_status": {name: runtime_status[name] for name in REQUIRED_RUNTIME},
        "visual_v126": "PASS",
        "additional_runtime_evidence": {
            name: "PASS" for name in CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE
        },
        "pppv_v2_status": pppv_status,
        "evidence": {
            "candidate_result": str(CANDIDATE_RESULT.relative_to(ROOT)),
            "candidate_result_sha256": sha256(CANDIDATE_RESULT),
            "fresh_checkout": str(FRESH_RESULT.relative_to(ROOT)),
            "fresh_checkout_sha256": sha256(FRESH_RESULT),
            "visual_v126": {
                "path": str(VISUAL_RESULT.relative_to(ROOT)),
                "sha256": sha256(VISUAL_RESULT),
            },
            "room_forensic_v131": {
                "path": str(FORENSIC_PREFLIGHT.relative_to(ROOT)),
                "sha256": sha256(FORENSIC_PREFLIGHT),
            },
            "generated_metadata": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                }
                for name, path in GENERATED_METADATA.items()
            },
            "pppv_v2": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                }
                for name, path in PPPV_REQUIRED_EVIDENCE.items()
            },
        },
        "runtime_asset_identity_sha256": observed_digest_after,
        "runtime_asset_summary": {
            "total_files": len(asset_files_after),
            "classic_png_count": len(classic_pngs),
            "room_glb_count": len(room_glbs),
            "audio_file_count": len(audio_files),
            "cursor_png_count": len(cursor_pngs),
            "menu_png_count": len(menu_pngs),
        },
        "runtime_assets": {
            str(p.relative_to(ROOT)): {
                "bytes": p.stat().st_size,
                "sha256": sha256(p),
            }
            for p in asset_files_after
        },
        "build_rule": (
            "Export is permitted only while Git HEAD, clean worktree, Godot version, "
            "candidate/fresh evidence, v126 graphical evidence, generated fidelity metadata, PPPV v2 evidence and restored runtime asset hashes still match this receipt."
        ),
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
