#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.remaster_framework.source_registry import (
    register_source,
    registry_status,
    resolve_source,
    source_home,
    verify_registered_source,
    write_runtime_binding,
)


BINDING = ROOT / ".tmp/openazrael_sources.json"


def _print(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _register(args: argparse.Namespace) -> int:
    row = register_source(
        args.kind,
        args.source,
        mirror=args.mirror,
        home=args.source_home,
    )
    _print(
        {
            "status": "PASS",
            "action": "register",
            "kind": args.kind,
            "source_home": str(source_home(explicit=args.source_home)),
            "registration": row,
        }
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    kinds = ("demo", "retail") if args.kind == "all" else (args.kind,)
    results = {
        kind: verify_registered_source(kind, home=args.source_home)
        for kind in kinds
    }
    status = "PASS" if all(
        row.get("status") == "PASS" for row in results.values()
    ) else "FAIL"
    _print({"status": status, "action": "verify", "sources": results})
    return 0 if status == "PASS" else 1


def _status(args: argparse.Namespace) -> int:
    _print(registry_status(home=args.source_home))
    return 0


def _prepare(args: argparse.Namespace) -> int:
    kinds = ("demo", "retail") if args.kind == "all" else (args.kind,)
    prepared: dict[str, dict] = {}
    for kind in kinds:
        root = resolve_source(kind, verify=True, home=args.source_home)
        prepared[kind] = {
            "status": "PASS",
            "root": str(root),
        }

    binding = write_runtime_binding(BINDING, home=args.source_home)
    if args.restore_demo_runtime and "demo" in kinds:
        demo_root = Path(prepared["demo"]["root"])
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/restore_candidate_assets.py"),
                str(demo_root),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            _print(
                {
                    "status": "FAIL",
                    "action": "prepare",
                    "reason": "DEMO_RUNTIME_RESTORE_FAILED",
                    "returncode": proc.returncode,
                }
            )
            return proc.returncode
        prepared["demo"]["runtime_assets_restored"] = True

    _print(
        {
            "status": "PASS",
            "action": "prepare",
            "binding": str(BINDING),
            "binding_payload": binding,
            "sources": prepared,
        }
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Persistent source-corpus bootstrap for OpenAzrael demo and retail "
            "commercial binaries. Raw payloads remain outside Git."
        )
    )
    parser.add_argument(
        "--source-home",
        type=Path,
        help=(
            "Override persistent private source home. Otherwise "
            "OPENAZRAEL_SOURCE_HOME or ~/.openazrael/sources is used."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser(
        "register",
        help="Register and fingerprint a canonical local source corpus.",
    )
    register.add_argument("kind", choices=("demo", "retail"))
    register.add_argument("source", type=Path)
    register.add_argument(
        "--mirror",
        action="store_true",
        help=(
            "Copy the source into OPENAZRAEL_SOURCE_HOME for maximum local "
            "persistence. Retail mirrors may be large."
        ),
    )
    register.set_defaults(func=_register)

    verify = sub.add_parser(
        "verify",
        help="Re-hash a registered source and require exact identity.",
    )
    verify.add_argument("kind", choices=("demo", "retail", "all"))
    verify.set_defaults(func=_verify)

    status = sub.add_parser(
        "status",
        help="Show registered paths without expensive full re-hashing.",
    )
    status.set_defaults(func=_status)

    prepare = sub.add_parser(
        "prepare",
        help="Resolve verified source roots and write a local runtime binding.",
    )
    prepare.add_argument("kind", choices=("demo", "retail", "all"))
    prepare.add_argument(
        "--restore-demo-runtime",
        action="store_true",
        help="Also rebuild ignored Candidate runtime assets from the demo corpus.",
    )
    prepare.set_defaults(func=_prepare)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
