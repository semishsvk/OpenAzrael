#!/usr/bin/env python3
"""Freeze an exact Candidate 4 preflight into a source-safe local handoff receipt.

The freeze contains only source/evidence/asset identities and hashes.  It never
copies commercial or commercial-derived payload bytes.  Export must consume the
same Git tree, preflight receipt and runtime asset set that were frozen here.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TMP=ROOT/".tmp/kg001"
PREFLIGHT=TMP/"candidate4_preflight_receipt.json"
OUT=TMP/"candidate4_frozen_release_receipt.json"

RUNTIME_ASSET_ROOTS=(
    ROOT/"assets/rooms",
    ROOT/"assets/audio",
    ROOT/"assets/textures/classic",
    ROOT/"assets/ui/mice",
    ROOT/"assets/ui/legacy_menu",
)

def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,cwd=ROOT,text=True,encoding="utf-8",errors="replace",
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
    )

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def git_value(*args: str) -> str:
    p=run(["git",*args])
    return p.stdout.strip() if p.returncode==0 else ""

def git_clean() -> bool:
    p=run(["git","status","--porcelain","--untracked-files=normal"])
    return p.returncode==0 and p.stdout.strip()==""

def runtime_asset_files() -> list[Path]:
    files=[]
    for root in RUNTIME_ASSET_ROOTS:
        if root.is_dir():
            files.extend(p for p in root.rglob("*") if p.is_file())
    return sorted(set(files),key=lambda p:str(p.relative_to(ROOT)).lower())

def observed_asset_identity() -> dict:
    return {
        str(p.relative_to(ROOT)):{"bytes":p.stat().st_size,"sha256":sha256(p)}
        for p in runtime_asset_files()
    }

def identity_digest(identity: dict) -> str:
    canonical=json.dumps(identity,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def fail(reason: str, details=None) -> int:
    OUT.unlink(missing_ok=True)
    payload={
        "schema":"openazrael.kg001.candidate4_frozen_release",
        "version":1,
        "status":"FAIL",
        "reason":reason,
    }
    if details is not None:
        payload["details"]=details
    print(json.dumps(payload,indent=2))
    return 1

def main() -> int:
    OUT.unlink(missing_ok=True)
    if not PREFLIGHT.is_file():
        return fail("PREFLIGHT_RECEIPT_MISSING")
    try:
        preflight=json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:
        return fail("PREFLIGHT_RECEIPT_INVALID",{"error":str(exc)})
    if preflight.get("status")!="PASS" or preflight.get("export_allowed") is not True:
        return fail("PREFLIGHT_NOT_PASS")

    head=git_value("rev-parse","HEAD")
    tree=git_value("rev-parse","HEAD^{tree}")
    if not head or not tree:
        return fail("GIT_IDENTITY_UNAVAILABLE")
    if head!=preflight.get("commit_sha"):
        return fail("HEAD_CHANGED_SINCE_PREFLIGHT",{"preflight":preflight.get("commit_sha"),"current":head})
    if not git_clean():
        return fail("DIRTY_GIT_AT_FREEZE")

    expected_assets=preflight.get("runtime_assets",{})
    if not isinstance(expected_assets,dict) or not expected_assets:
        return fail("PREFLIGHT_RUNTIME_ASSET_IDENTITY_MISSING")
    observed_assets=observed_asset_identity()
    if set(observed_assets)!=set(expected_assets):
        return fail("RUNTIME_ASSET_SET_CHANGED_SINCE_PREFLIGHT",{
            "added":sorted(set(observed_assets)-set(expected_assets)),
            "removed":sorted(set(expected_assets)-set(observed_assets)),
        })
    changed=[
        path for path in sorted(observed_assets)
        if observed_assets[path]!=expected_assets.get(path)
    ]
    if changed:
        return fail("RUNTIME_ASSET_CHANGED_SINCE_PREFLIGHT",{"changed":changed})

    preflight_sha=sha256(PREFLIGHT)
    asset_digest=identity_digest(observed_assets)
    payload={
        "schema":"openazrael.kg001.candidate4_frozen_release",
        "version":1,
        "status":"PASS",
        "candidate":"KG-001 Candidate 4",
        "commit_sha":head,
        "source_tree_sha":tree,
        "preflight_receipt":{
            "path":str(PREFLIGHT.relative_to(ROOT)).replace("\\","/"),
            "sha256":preflight_sha,
        },
        "runtime_asset_identity":{
            "file_count":len(observed_assets),
            "canonical_sha256":asset_digest,
        },
        "source_safe":True,
        "commercial_payload_bytes_embedded":False,
        "export_rule":"Export is allowed only while Git HEAD/tree, preflight receipt SHA-256 and complete runtime asset identity still match this frozen receipt.",
    }
    OUT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    if not git_clean():
        return fail("TRACKED_SOURCE_CHANGED_DURING_FREEZE")
    print(json.dumps(payload,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
