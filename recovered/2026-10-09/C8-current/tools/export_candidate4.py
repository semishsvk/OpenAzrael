#!/usr/bin/env python3
"""Export KG-001 Candidate 4 only from a current PASS preflight receipt."""
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
TMP = ROOT / ".tmp/kg001"
RECEIPT = TMP / "candidate4_preflight_receipt.json"
EXPORT_RECEIPT = TMP / "candidate4_export_receipt.json"
FROZEN_RECEIPT = TMP / "candidate4_frozen_release_receipt.json"
DEFAULT_OUT = ROOT / "exports/OpenAzrael-KG001-Candidate4.exe"
RUNTIME_BUILD_IDENTITY = ROOT / "data/runtime_build_identity.json"
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
    return [
        line for line in output.splitlines()
        if line.lstrip().startswith(("ERROR:", "SCRIPT ERROR:"))
    ]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git_head() -> str:
    p = run(["git", "rev-parse", "HEAD"])
    return p.stdout.strip() if p.returncode == 0 else ""

def git_tree() -> str:
    p = run(["git", "rev-parse", "HEAD^{tree}"])
    return p.stdout.strip() if p.returncode == 0 else ""

def identity_digest(identity: dict) -> str:
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

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
    EXPORT_RECEIPT.unlink(missing_ok=True)
    RUNTIME_BUILD_IDENTITY.unlink(missing_ok=True)
    out = {
        "schema": "openazrael.kg001.candidate4_export",
        "version": 1,
        "status": "FAIL",
        "reason": reason,
    }
    if details:
        out["details"] = details
    print(json.dumps(out, indent=2))
    return 1

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--godot", help="Godot executable; otherwise GODOT_BIN/godot4/godot are tried.")
    ap.add_argument("--preset", default="Windows Candidate 4")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    EXPORT_RECEIPT.unlink(missing_ok=True)
    RUNTIME_BUILD_IDENTITY.unlink(missing_ok=True)
    if not RECEIPT.is_file():
        return fail("PREFLIGHT_RECEIPT_MISSING")
    if not FROZEN_RECEIPT.is_file():
        return fail("FROZEN_RELEASE_RECEIPT_MISSING", {
            "hint": "Run python tools/freeze_candidate4_release.py after a PASS Candidate 4 preflight."
        })

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    frozen = json.loads(FROZEN_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or receipt.get("export_allowed") is not True:
        return fail("PREFLIGHT_NOT_PASS")

    head = git_head()
    if head != receipt.get("commit_sha"):
        return fail("HEAD_CHANGED_SINCE_PREFLIGHT", {"receipt": receipt.get("commit_sha"), "current": head})
    if frozen.get("status") != "PASS" or frozen.get("commit_sha") != head:
        return fail("FROZEN_RELEASE_NOT_CURRENT", {"frozen_commit": frozen.get("commit_sha"), "current": head})
    if frozen.get("source_tree_sha") != git_tree():
        return fail("SOURCE_TREE_CHANGED_SINCE_FREEZE", {
            "frozen": frozen.get("source_tree_sha"), "current": git_tree()
        })
    if frozen.get("preflight_receipt", {}).get("sha256") != sha256(RECEIPT):
        return fail("PREFLIGHT_RECEIPT_CHANGED_SINCE_FREEZE")
    if not git_clean():
        return fail("DIRTY_GIT_AFTER_PREFLIGHT")

    semantic_gate = run([
        sys.executable,
        "tools/validate_release_runtime_evidence_v176.py",
        str(RECEIPT),
        head,
    ])
    if semantic_gate.returncode != 0:
        return fail(
            "RELEASE_RUNTIME_EVIDENCE_NOT_CURRENT_PASS",
            {"output_tail": semantic_gate.stdout[-16000:]},
        )

    for key in ("candidate_result", "fresh_checkout"):
        rel = receipt.get("evidence", {}).get(key)
        expected = receipt.get("evidence", {}).get(key + "_sha256")
        p = ROOT / str(rel)
        if not p.is_file() or sha256(p) != expected:
            return fail("PREFLIGHT_EVIDENCE_CHANGED", {"evidence": key})

    visual_meta = receipt.get("evidence", {}).get("visual_v126", {})
    visual_path = ROOT / str(visual_meta.get("path", ""))
    if (
        receipt.get("visual_v126") != "PASS"
        or not visual_path.is_file()
        or sha256(visual_path) != visual_meta.get("sha256")
    ):
        return fail("VISUAL_V126_EVIDENCE_CHANGED_OR_MISSING")

    generated_meta = receipt.get("evidence", {}).get("generated_metadata", {})
    if not isinstance(generated_meta, dict) or not generated_meta:
        return fail("GENERATED_FIDELITY_METADATA_MISSING")
    for key, meta in generated_meta.items():
        p = ROOT / str(meta.get("path", ""))
        if not p.is_file() or sha256(p) != meta.get("sha256"):
            return fail("GENERATED_FIDELITY_METADATA_CHANGED", {"evidence": key})

    pppv_receipt = receipt.get("evidence", {}).get("pppv_v2", {})
    if not isinstance(pppv_receipt, dict) or not pppv_receipt:
        return fail("PPPV_PREFLIGHT_EVIDENCE_MISSING")
    for key, meta in pppv_receipt.items():
        if not isinstance(meta, dict):
            return fail("PPPV_PREFLIGHT_EVIDENCE_INVALID", {"evidence": key})
        rel = meta.get("path")
        expected = meta.get("sha256")
        p = ROOT / str(rel)
        if not p.is_file() or not expected or sha256(p) != expected:
            return fail(
                "PPPV_EVIDENCE_CHANGED_SINCE_PREFLIGHT",
                {"evidence": key, "path": str(rel)},
            )

    candidate4_evidence = receipt.get("evidence", {})
    for key in (
        "candidate4_audio_v132",
        "candidate4_music_route_v133",
        "candidate4_music_runtime_v135",
        "candidate4_music_godot_v136",
        "candidate4_music_manifest_v135",
    ):
        meta = candidate4_evidence.get(key, {})
        if not isinstance(meta, dict):
            return fail("CANDIDATE4_EVIDENCE_MISSING", {"evidence": key})
        path = ROOT / str(meta.get("path", ""))
        expected = meta.get("sha256")
        if not path.is_file() or not expected or sha256(path) != expected:
            return fail("CANDIDATE4_EVIDENCE_CHANGED", {"evidence": key, "path": str(meta.get("path", ""))})

    music_runtime_path = ROOT / str(candidate4_evidence["candidate4_music_runtime_v135"]["path"])
    music_runtime = json.loads(music_runtime_path.read_text(encoding="utf-8"))
    if (
        music_runtime.get("status") != "PASS"
        or music_runtime.get("runtime_playback_test") != "PASS"
        or music_runtime.get("all_canonical_rendered") is not True
    ):
        return fail("CANDIDATE4_MUSIC_RUNTIME_NOT_RELEASE_READY", music_runtime)

    receipt_assets = receipt.get("runtime_assets", {})
    current_asset_paths = {
        str(p.relative_to(ROOT)) for p in runtime_asset_files()
    }
    receipt_asset_paths = set(receipt_assets)
    if current_asset_paths != receipt_asset_paths:
        return fail(
            "RUNTIME_ASSET_SET_CHANGED_SINCE_PREFLIGHT",
            {
                "added": sorted(current_asset_paths - receipt_asset_paths),
                "removed": sorted(receipt_asset_paths - current_asset_paths),
            },
        )

    observed_asset_identity = {}
    for rel, meta in receipt_assets.items():
        p = ROOT / rel
        if not p.is_file() or p.stat().st_size != int(meta.get("bytes", -1)) or sha256(p) != meta.get("sha256"):
            return fail("RUNTIME_ASSET_CHANGED_SINCE_PREFLIGHT", {"asset": rel})
        observed_asset_identity[rel] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    frozen_asset_digest = frozen.get("runtime_asset_identity", {}).get("canonical_sha256")
    if not frozen_asset_digest or identity_digest(observed_asset_identity) != frozen_asset_digest:
        return fail("RUNTIME_ASSET_IDENTITY_CHANGED_SINCE_FREEZE")

    godot = find_godot(args.godot)
    if not godot:
        return fail("GODOT_NOT_FOUND")
    ver = run([godot, "--version"])
    godot_version = ver.stdout.strip()
    if ver.returncode != 0 or godot_version != receipt.get("godot_version"):
        return fail(
            "GODOT_VERSION_CHANGED_SINCE_PREFLIGHT",
            {"receipt": receipt.get("godot_version"), "current": godot_version},
        )

    presets = (ROOT / "export_presets.cfg").read_text(encoding="utf-8")
    if f'name="{args.preset}"' not in presets:
        return fail("EXPORT_PRESET_MISSING", {"preset": args.preset})

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    pck = out.with_suffix(".pck")
    out.unlink(missing_ok=True)
    pck.unlink(missing_ok=True)

    runtime_identity = {
        "schema": "openazrael.runtime_build_identity",
        "version": 1,
        "candidate": "KG-001 Candidate 4",
        "commit_sha": head,
        "godot_version": godot_version,
        "preset": args.preset,
        "preflight_receipt_sha256": sha256(RECEIPT),
        "frozen_release_receipt_sha256": sha256(FROZEN_RECEIPT),
        "pppv_v2_evidence": receipt.get("evidence", {}).get("pppv_v2", {}),
    }
    RUNTIME_BUILD_IDENTITY.write_text(
        json.dumps(runtime_identity, indent=2) + "\n",
        encoding="utf-8",
    )

    proc = run([
        godot,
        "--headless",
        "--path",
        str(ROOT),
        "--export-release",
        args.preset,
        str(out),
    ])
    errors = [
        line for line in proc.stdout.splitlines()
        if line.lstrip().startswith(("ERROR:", "SCRIPT ERROR:"))
    ]
    if proc.returncode != 0 or errors or not out.is_file():
        return fail(
            "EXPORT_FAILED",
            {
                "returncode": proc.returncode,
                "engine_errors": errors,
                "output_tail": proc.stdout[-20000:],
            },
        )
    if not pck.is_file():
        return fail(
            "PCK_MISSING",
            {
                "note": "Windows Candidate 4 uses binary_format/embed_pck=false; EXE and PCK must ship together.",
                "exe": str(out.relative_to(ROOT)),
                "expected_pck": str(pck.relative_to(ROOT)),
            },
        )

    packaged_origin_run = run([
        str(out),
        "--headless",
        "--script",
        "res://scripts/kg001_packaged_origin_runner_v178.gd",
    ])
    packaged_origin_errors = engine_errors(packaged_origin_run.stdout)
    packaged_origin = parse_marker(
        packaged_origin_run.stdout,
        "OPENAZRAEL_KG001_PACKAGED_ORIGIN_V178",
    )
    if (
        packaged_origin_run.returncode != 0
        or packaged_origin_errors
        or packaged_origin.get("status") != "PASS"
        or packaged_origin.get("identity", {}).get("commit_sha") != head
        or packaged_origin.get("identity", {}).get("preset") != args.preset
    ):
        return fail("PACKAGED_EXECUTION_BOUNDARY_NOT_PROVEN", {
            "returncode": packaged_origin_run.returncode,
            "result": packaged_origin,
            "engine_errors": packaged_origin_errors,
            "output_tail": packaged_origin_run.stdout[-12000:],
        })

    smoke = run([
        str(out),
        "--headless",
        "--quit-after",
        "120",
    ])
    smoke_errors = engine_errors(smoke.stdout)
    if smoke.returncode != 0 or smoke_errors:
        return fail(
            "EXPORTED_STARTUP_SMOKE_FAILED",
            {
                "returncode": smoke.returncode,
                "engine_errors": smoke_errors,
                "output_tail": smoke.stdout[-20000:],
            },
        )

    packaged = run([
        str(out),
        "--headless",
        "--script",
        "res://scripts/kg001_packaged_parity_runner_v128.gd",
    ])
    packaged_errors = engine_errors(packaged.stdout)
    packaged_result = parse_marker(
        packaged.stdout,
        "OPENAZRAEL_KG001_PACKAGED_PARITY_V128",
    )
    if (
        packaged.returncode != 0
        or packaged_errors
        or packaged_result.get("status") != "PASS"
    ):
        return fail(
            "PACKAGED_PARITY_V128_FAILED",
            {
                "returncode": packaged.returncode,
                "status": packaged_result.get("status"),
                "engine_errors": packaged_errors,
                "output_tail": packaged.stdout[-20000:],
            },
        )

    packaged_music = run([
        str(out),
        "--headless",
        "--script",
        "res://scripts/kg001_music_runtime_runner_v136.gd",
    ])
    packaged_music_errors = engine_errors(packaged_music.stdout)
    packaged_music_result = parse_marker(
        packaged_music.stdout,
        "OPENAZRAEL_KG001_MUSIC_V136",
    )
    if (
        packaged_music.returncode != 0
        or packaged_music_errors
        or packaged_music_result.get("status") != "PASS"
    ):
        return fail(
            "PACKAGED_MUSIC_V136_FAILED",
            {
                "returncode": packaged_music.returncode,
                "status": packaged_music_result.get("status"),
                "engine_errors": packaged_music_errors,
                "output_tail": packaged_music.stdout[-20000:],
            },
        )

    packaged_critical_specs = [
        ("all_transitions_v141", "res://scripts/kg001_all_transition_runner_v141.gd", "OPENAZRAEL_KG001_ALL_TRANSITIONS_V141"),
        ("cursor_v143", "res://scripts/kg001_interaction_cursor_runner_v143.gd", "OPENAZRAEL_KG001_CURSOR_V143"),
        ("menu_v145", "res://scripts/kg001_legacy_menu_runner_v145.gd", "OPENAZRAEL_KG001_MENU_V145"),
        ("menu_cursor_v146", "res://scripts/kg001_menu_cursor_context_runner_v146.gd", "OPENAZRAEL_KG001_MENU_CURSOR_V146"),
        ("menu_toggle_v149", "res://scripts/kg001_legacy_menu_toggle_runner_v149.gd", "OPENAZRAEL_KG001_MENU_TOGGLE_V149"),
        ("inventory_hud_v157", "res://scripts/kg001_inventory_hud_runner_v157.gd", "OPENAZRAEL_KG001_INVENTORY_HUD_V157"),
    ]
    packaged_critical = {}
    for name, script, marker in packaged_critical_specs:
        critical_run = run([str(out), "--headless", "--script", script])
        critical_errors = engine_errors(critical_run.stdout)
        critical_result = parse_marker(critical_run.stdout, marker)
        packaged_critical[name] = critical_result
        if (
            critical_run.returncode != 0
            or critical_errors
            or critical_result.get("status") != "PASS"
        ):
            return fail(
                "PACKAGED_CRITICAL_GAMEPLAY_FAILED",
                {
                    "test": name,
                    "returncode": critical_run.returncode,
                    "status": critical_result.get("status"),
                    "engine_errors": critical_errors,
                    "output_tail": critical_run.stdout[-20000:],
                },
            )

    packaged_evidence = TMP / "kg001_packaged_v128_runtime.json"
    packaged_evidence.write_text(
        json.dumps(packaged_result, indent=2) + "\n",
        encoding="utf-8",
    )
    forensic_package = TMP / "room_forensic_report_v131_package.json"
    forensic_run = run([
        sys.executable,
        "tools/build_room_forensic_report_v131.py",
        "--phase",
        "package",
        "--out",
        str(forensic_package),
    ])
    if forensic_run.returncode != 0 or not forensic_package.is_file():
        return fail(
            "ROOM_FORENSIC_PACKAGE_V131_FAILED",
            {"output_tail": forensic_run.stdout[-20000:]},
        )

    RUNTIME_BUILD_IDENTITY.unlink(missing_ok=True)

    artifacts = {
        str(out.relative_to(ROOT)): {
            "bytes": out.stat().st_size,
            "sha256": sha256(out),
        }
    }
    if pck.is_file():
        artifacts[str(pck.relative_to(ROOT))] = {
            "bytes": pck.stat().st_size,
            "sha256": sha256(pck),
        }

    export_receipt = {
        "schema": "openazrael.kg001.candidate4_export",
        "version": 1,
        "status": "PASS",
        "candidate": "KG-001 Candidate 4",
        "commit_sha": head,
        "godot_version": godot_version,
        "preflight_receipt_sha256": sha256(RECEIPT),
        "runtime_build_identity_embedded": true,
        "runtime_build_identity": runtime_identity,
        "packaged_execution_origin_v178": packaged_origin,
        "preset": args.preset,
        "artifacts": artifacts,
        "export_smoke": {
            "status": "PASS",
            "mode": "headless",
            "quit_after": 120,
            "returncode": smoke.returncode,
            "engine_errors": smoke_errors,
        },
        "packaged_parity_v128": packaged_result,
        "packaged_music_v136": packaged_music_result,
        "packaged_critical_gameplay": packaged_critical,
        "room_forensic_v131": {
            "path": str(forensic_package.relative_to(ROOT)),
            "sha256": sha256(forensic_package),
            "status": "PASS",
        },
        "manual_gate": "G10_PENDING_USER",
    }
    EXPORT_RECEIPT.write_text(
        json.dumps(export_receipt, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(export_receipt, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
