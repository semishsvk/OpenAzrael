from __future__ import annotations

import argparse
import hashlib
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
    "pppv_playthrough_evaluation": (
        "pppv_playthrough_evaluation.json",
        "remaster.playthrough_evaluation",
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


def _canonical_compact(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_without(payload: dict[str, Any], field: str) -> str:
    reduced = dict(payload)
    reduced.pop(field, None)
    return hashlib.sha256(_canonical_compact(reduced)).hexdigest()


def _verify_internal_integrity(
    artifact_id: str,
    payload: dict[str, Any],
) -> None:
    if artifact_id == "build_provenance":
        expected = str(payload.get("provenance_sha256", ""))
        actual = _sha256_without(payload, "provenance_sha256")
        if expected != actual:
            raise ValueError(
                "build_provenance: provenance_sha256 integrity mismatch"
            )
    elif artifact_id == "release_gate_summary":
        expected = str(payload.get("summary_sha256", ""))
        actual = _sha256_without(payload, "summary_sha256")
        if expected != actual:
            raise ValueError(
                "release_gate_summary: summary_sha256 integrity mismatch"
            )


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _artifact_sources_from_bundle(bundle_path: Path) -> dict[str, Path]:
    bundle = _load_json(bundle_path)
    if bundle.get("schema") != "openazrael.kg001.framework_bundle":
        raise ValueError("unsupported KG framework bundle schema")
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("KG framework bundle artifacts must be an object")

    base = bundle_path.resolve().parent
    mapping = {
        "build_provenance": "build_provenance",
        "release_gate_summary": "release_gate_summary",
        "pppv_coverage": "pppv_coverage",
    }
    resolved: dict[str, Path] = {}
    for artifact_id, bundle_key in mapping.items():
        raw = artifacts.get(bundle_key)
        if not isinstance(raw, str) or not raw:
            raise ValueError(
                f"KG framework bundle missing artifact {bundle_key}"
            )
        candidate = (base / raw).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise ValueError(
                f"KG framework artifact escapes bundle directory: {raw}"
            ) from exc
        resolved[artifact_id] = candidate

    optional_name = artifacts.get("pppv_playthrough_evaluation")
    if isinstance(optional_name, str) and optional_name:
        optional_path = (base / optional_name).resolve()
        try:
            optional_path.relative_to(base)
        except ValueError as exc:
            raise ValueError(
                "KG framework artifact escapes bundle directory: "
                f"{optional_name}"
            ) from exc
        resolved["pppv_playthrough_evaluation"] = optional_path

    return resolved


def stage_runtime_metadata(
    project_root: Path,
    *,
    build_provenance: Path | None = None,
    release_gate_summary: Path | None = None,
    pppv_coverage: Path | None = None,
    pppv_playthrough_evaluation: Path | None = None,
    framework_bundle: Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    runtime_dir = root / RUNTIME_DIR
    runtime_dir.mkdir(parents=True, exist_ok=True)

    supplied = {
        "build_provenance": build_provenance,
        "release_gate_summary": release_gate_summary,
        "pppv_coverage": pppv_coverage,
        "pppv_playthrough_evaluation": pppv_playthrough_evaluation,
    }
    if framework_bundle is not None:
        explicit = [key for key, value in supplied.items() if value is not None]
        if explicit:
            raise ValueError(
                "framework_bundle cannot be combined with explicit artifact inputs"
            )
        supplied = _artifact_sources_from_bundle(framework_bundle)

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
        _verify_internal_integrity(artifact_id, payload)
        destination = runtime_dir / filename
        rendered = _canonical_json(payload)
        destination.write_text(rendered, encoding="utf-8")
        staged.append({
            "id": artifact_id,
            "source": str(source.resolve()),
            "destination": destination.relative_to(root).as_posix(),
            "schema": expected_schema,
            "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        })

    return {
        "schema": "remaster.runtime_metadata_stage",
        "version": 1,
        "staged_count": len(staged),
        "staged": staged,
        "source_safe": True,
        "commercial_assets_included": False,
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
    stage.add_argument("--pppv-playthrough-evaluation", type=Path)
    stage.add_argument("--framework-bundle", type=Path)
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
        pppv_playthrough_evaluation=args.pppv_playthrough_evaluation,
        framework_bundle=args.framework_bundle,
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
