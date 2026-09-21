#!/usr/bin/env python3
"""Export KG-001 Candidate 3 only from a current PASS preflight receipt."""
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
RECEIPT = TMP / "candidate3_preflight_receipt.json"
EXPORT_RECEIPT = TMP / "candidate3_export_receipt.json"
DEFAULT_OUT = ROOT / "exports/OpenAzrael-KG001-Candidate3.exe"
RUNTIME_BUILD_IDENTITY = ROOT / "data/runtime_build_identity.json"
RUNTIME_ASSET_ROOTS = (
    ROOT / "assets/rooms",
    ROOT / "assets/audio",
    ROOT / "assets/textures/classic",
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
    EXPORT_RECEIPT.unlink(missing_ok=True)
    RUNTIME_BUILD_IDENTITY.unlink(missing_ok=True)
    out = {
        "schema": "openazrael.kg001.candidate3_export",
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
    ap.add_argument("--preset", default="Windows Candidate 3")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    EXPORT_RECEIPT.unlink(missing_ok=True)
    RUNTIME_BUILD_IDENTITY.unlink(missing_ok=True)
    if not RECEIPT.is_file():
        return fail("PREFLIGHT_RECEIPT_MISSING")

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or receipt.get("export_allowed") is not True:
        return fail("PREFLIGHT_NOT_PASS")

    head = git_head()
    if head != receipt.get("commit_sha"):
        return fail("HEAD_CHANGED_SINCE_PREFLIGHT", {"receipt": receipt.get("commit_sha"), "current": head})
    if not git_clean():
        return fail("DIRTY_GIT_AFTER_PREFLIGHT")

    for key in ("candidate_result", "fresh_checkout"):
        rel = receipt.get("evidence", {}).get(key)
        expected = receipt.get("evidence", {}).get(key + "_sha256")
        p = ROOT / str(rel)
        if not p.is_file() or sha256(p) != expected:
            return fail("PREFLIGHT_EVIDENCE_CHANGED", {"evidence": key})

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

    for rel, meta in receipt_assets.items():
        p = ROOT / rel
        if not p.is_file() or p.stat().st_size != int(meta.get("bytes", -1)) or sha256(p) != meta.get("sha256"):
            return fail("RUNTIME_ASSET_CHANGED_SINCE_PREFLIGHT", {"asset": rel})

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
        "candidate": "KG-001 Candidate 3",
        "commit_sha": head,
        "godot_version": godot_version,
        "preset": args.preset,
        "preflight_receipt_sha256": sha256(RECEIPT),
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
                "note": "Windows Candidate 3 uses binary_format/embed_pck=false; EXE and PCK must ship together.",
                "exe": str(out.relative_to(ROOT)),
                "expected_pck": str(pck.relative_to(ROOT)),
            },
        )

    smoke = run([
        str(out),
        "--headless",
        "--quit-after",
        "120",
    ])
    smoke_errors = [
        line for line in smoke.stdout.splitlines()
        if line.lstrip().startswith(("ERROR:", "SCRIPT ERROR:"))
    ]
    if smoke.returncode != 0 or smoke_errors:
        return fail(
            "EXPORTED_STARTUP_SMOKE_FAILED",
            {
                "returncode": smoke.returncode,
                "engine_errors": smoke_errors,
                "output_tail": smoke.stdout[-20000:],
            },
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
        "schema": "openazrael.kg001.candidate3_export",
        "version": 1,
        "status": "PASS",
        "candidate": "KG-001 Candidate 3",
        "commit_sha": head,
        "godot_version": godot_version,
        "preflight_receipt_sha256": sha256(RECEIPT),
        "runtime_build_identity_embedded": true,
        "runtime_build_identity": runtime_identity,
        "preset": args.preset,
        "artifacts": artifacts,
        "export_smoke": {
            "status": "PASS",
            "mode": "headless",
            "quit_after": 120,
            "returncode": smoke.returncode,
            "engine_errors": smoke_errors,
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
