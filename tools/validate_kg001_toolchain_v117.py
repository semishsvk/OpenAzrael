#!/usr/bin/env python3
"""Validate the pinned KG-001 Candidate 2 source-safe toolchain."""
from __future__ import annotations

from pathlib import Path
import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/tests/kg001_toolchain_contract_v117.json"
REQUIREMENTS=ROOT/"tools/requirements-kg001-source-safe.txt"


def version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--godot",default=None)
    ap.add_argument(
        "--require-godot",
        action="store_true",
        help="Fail unless the exact pinned Godot runtime is executable.",
    )
    args=ap.parse_args()

    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    required=contract["packages"]
    checks={
        "contract_schema":contract.get("schema")=="openazrael.kg001.toolchain_contract",
        "contract_status":contract.get("status")=="PINNED",
        "python":platform.python_version()==contract["python"],
        "numpy":version("numpy")==required["numpy"],
        "Pillow":version("Pillow")==required["Pillow"],
        "trimesh":version("trimesh")==required["trimesh"],
        "requirements_exact":REQUIREMENTS.read_text(encoding="utf-8").splitlines()==[
            f"numpy=={required['numpy']}",
            f"Pillow=={required['Pillow']}",
            f"trimesh=={required['trimesh']}",
        ],
    }

    godot_result={
        "requested":bool(args.godot),
        "required":bool(args.require_godot),
        "version":"",
        "expected":contract["godot"]["version"],
        "status":"NOT_PROBED",
    }
    if args.godot:
        proc=subprocess.run(
            [args.godot,"--version"],
            cwd=ROOT,text=True,capture_output=True,check=False,
        )
        observed=(proc.stdout or proc.stderr).strip()
        godot_result.update({
            "version":observed,
            "status":"PASS" if proc.returncode==0 and observed==contract["godot"]["version"] else "FAIL",
        })
        checks["godot"]=godot_result["status"]=="PASS"
    elif args.require_godot:
        checks["godot"]=False

    failed=[name for name,value in checks.items() if not value]
    result={
        "schema":"openazrael.kg001.toolchain_validation",
        "version":117,
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "observed":{
            "python":platform.python_version(),
            "numpy":version("numpy"),
            "Pillow":version("Pillow"),
            "trimesh":version("trimesh"),
            "godot":godot_result,
        },
        "failed":failed,
    }
    print(json.dumps(result,indent=2))
    return 0 if not failed else 1


if __name__=="__main__":
    raise SystemExit(main())
