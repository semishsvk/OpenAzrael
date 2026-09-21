from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RUNTIME_DIR = Path("data/runtime")
KNOWN_ARTIFACTS = {
    "build_provenance": (
        "build_provenance.json",
        "remaster.build_provenance",
    ),
    "release_gate_summary": (
        "release_gate_summary.json",
        "remaster.release_gate_summary",
    ),
    "pppv_coverage": (
        "pppv_coverage.json",
        "remaster.validation_coverage",
    ),
}
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"metadata input missing: {path}")
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"metadata input exceeds size limit: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"metadata JSON root must be an object: {path}")
    return payload


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def stage_runtime_metadata(
    project_root: Path,
    *,
    build_provenance: Path | None = None,
    release_gate_summary: Path | None = None,
    pppv_coverage: Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    runtime_dir = root / RUNTIME_DIR
    runtime_dir.mkdir(parents=True, exist_ok=True)

    supplied = {
        "build_provenance": build_provenance,
        "release_gate_summary": release_gate_summary,
        "pppv_coverage": pppv_coverage,
    }
    staged = []
    for artifact_id, source in supplied.items():
        if source is None:
            continue
        filename, expected_schema = KNOWN_ARTIFACTS[artifact_id]
        payload = _load_json(source.resolve())
        actual_schema = str(payload.get("schema", ""))
        if actual_schema != expected_schema:
            raise ValueError(
                f"{artifact_id}: expected schema {expected_schema}, "
                f"got {actual_schema!r}"
            )
        destination = runtime_dir / filename
        destination.write_text(_canonical_json(payload), encoding="utf-8")
        staged.append({
            "id": artifact_id,
            "source": str(source.resolve()),
            "destination": destination.relative_to(root).as_posix(),
            "schema": expected_schema,
        })

    return {
        "schema": "remaster.runtime_metadata_stage",
        "version": 1,
        "staged_count": len(staged),
        "staged": staged,
    }


def clean_runtime_metadata(project_root: Path) -> list[str]:
    root = project_root.resolve()
    runtime_dir = root / RUNTIME_DIR
    removed: list[str] = []
    for filename, _schema in KNOWN_ARTIFACTS.values():
        path = runtime_dir / filename
        if path.is_file():
            path.unlink()
            removed.append(path.relative_to(root).as_posix())
    return sorted(removed, key=str.casefold)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage source-safe framework metadata into a Godot build tree."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    stage = sub.add_parser("stage")
    stage.add_argument("--project-root", type=Path, default=Path("."))
    stage.add_argument("--build-provenance", type=Path)
    stage.add_argument("--release-gate-summary", type=Path)
    stage.add_argument("--pppv-coverage", type=Path)
    stage.add_argument("--output", type=Path)

    clean = sub.add_parser("clean")
    clean.add_argument("--project-root", type=Path, default=Path("."))

    args = parser.parse_args()
    if args.command == "clean":
        removed = clean_runtime_metadata(args.project_root)
        print(json.dumps({"removed": removed}, indent=2))
        return 0

    result = stage_runtime_metadata(
        args.project_root,
        build_provenance=args.build_provenance,
        release_gate_summary=args.release_gate_summary,
        pppv_coverage=args.pppv_coverage,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
