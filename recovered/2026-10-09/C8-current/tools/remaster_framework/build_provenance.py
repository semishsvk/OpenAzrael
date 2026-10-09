from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "remaster.build_provenance"
VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_provenance(
    *,
    project: str,
    commit_sha: str,
    project_version: str,
    engine: dict[str, Any],
    inputs: dict[str, str],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not GIT_SHA_RE.fullmatch(commit_sha):
        errors.append("commit_sha must be a 40-char lowercase Git SHA")
    for key, digest in inputs.items():
        if not SHA256_RE.fullmatch(str(digest)):
            errors.append(f"invalid SHA-256 for input {key}")
    if errors:
        raise ValueError("; ".join(errors))

    payload = {
        "schema": SCHEMA,
        "version": VERSION,
        "project": project,
        "commit_sha": commit_sha,
        "project_version": project_version,
        "engine": engine,
        "inputs": dict(sorted(inputs.items())),
        "metadata": metadata or {},
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["provenance_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a deterministic build provenance manifest."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--project-version", required=True)
    parser.add_argument("--engine-name", default="Godot")
    parser.add_argument("--engine-version", required=True)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="name=/path/to/file; may be repeated",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inputs: dict[str, str] = {}
    for item in args.input:
        if "=" not in item:
            parser.error("--input must use name=path syntax")
        name, raw_path = item.split("=", 1)
        if not name or not raw_path:
            parser.error("--input must use non-empty name=path")
        path = Path(raw_path)
        if not path.is_file():
            parser.error(f"input file missing: {path}")
        inputs[name] = sha256_file(path)

    payload = build_provenance(
        project=args.project,
        commit_sha=args.commit_sha,
        project_version=args.project_version,
        engine={
            "name": args.engine_name,
            "version": args.engine_version,
        },
        inputs=inputs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(payload["provenance_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
