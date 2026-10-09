from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .ir import IRDescriptor, describe_json_ir


ARTIFACT_MANIFEST_SCHEMA = "remaster.artifact_manifest"
ARTIFACT_MANIFEST_VERSION = 1


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ProvenanceRecord:
    source_id: str
    kind: str
    sha256: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    path: str
    media_type: str
    size: int
    sha256: str
    ir: IRDescriptor | None = None
    provenance: tuple[ProvenanceRecord, ...] = field(default_factory=tuple)
    declared_sources: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "media_type": self.media_type,
            "size": self.size,
            "sha256": self.sha256,
            "provenance": [record.to_dict() for record in self.provenance],
            "declared_sources": list(self.declared_sources),
        }
        if self.ir is not None:
            payload["ir"] = self.ir.to_dict()
        return payload


def _artifact_id(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    return "artifact:" + normalized


def _declared_sources(payload: dict[str, Any]) -> tuple[str, ...]:
    values: set[str] = set()

    source = payload.get("source")
    if isinstance(source, str):
        values.add(source)
    elif isinstance(source, dict):
        for key in ("path", "file", "name"):
            value = source.get(key)
            if isinstance(value, str) and value:
                values.add(value)

    sources = payload.get("sources")
    if isinstance(sources, dict):
        for key, value in sources.items():
            if isinstance(value, str):
                values.add(f"{key}={value}")
            else:
                values.add(str(key))
    elif isinstance(sources, list):
        values.update(str(value) for value in sources if value)

    return tuple(sorted(values, key=str.casefold))


def inspect_artifact(root: Path, path: Path) -> ArtifactRecord:
    root = root.resolve()
    path = path.resolve()
    relative = path.relative_to(root).as_posix()
    media_type = "application/octet-stream"
    ir: IRDescriptor | None = None
    declared: tuple[str, ...] = ()

    if path.suffix.lower() == ".json":
        media_type = "application/json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"JSON artifact root must be an object: {relative}")
        ir = describe_json_ir(path, payload)
        declared = _declared_sources(payload)

    digest = sha256_file(path)
    provenance = (
        ProvenanceRecord(
            source_id=relative,
            kind="repository_artifact",
            sha256=digest,
        ),
    )

    return ArtifactRecord(
        artifact_id=_artifact_id(relative),
        path=relative,
        media_type=media_type,
        size=path.stat().st_size,
        sha256=digest,
        ir=ir,
        provenance=provenance,
        declared_sources=declared,
    )


def iter_artifact_paths(
    root: Path,
    *,
    include_suffixes: Iterable[str] = (".json",),
    excluded_paths: Iterable[Path] = (),
) -> list[Path]:
    root = root.resolve()
    suffixes = {value.lower() for value in include_suffixes}
    excluded = {value.resolve() for value in excluded_paths}
    paths = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.suffix.lower() in suffixes
        and path.resolve() not in excluded
    ]
    return sorted(paths, key=lambda value: value.relative_to(root).as_posix().casefold())


def build_artifact_manifest(
    root: Path,
    *,
    project: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    excluded = (output_path.resolve(),) if output_path is not None else ()
    records = [
        inspect_artifact(root, path)
        for path in iter_artifact_paths(root, excluded_paths=excluded)
    ]

    return {
        "schema": ARTIFACT_MANIFEST_SCHEMA,
        "version": ARTIFACT_MANIFEST_VERSION,
        "project": project,
        "artifact_count": len(records),
        "artifacts": [record.to_dict() for record in records],
    }


def write_artifact_manifest(
    root: Path,
    output_path: Path,
    *,
    project: str,
) -> dict[str, Any]:
    payload = build_artifact_manifest(
        root,
        project=project,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def verify_artifact_manifest(root: Path, manifest_path: Path) -> list[str]:
    root = root.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if payload.get("schema") != ARTIFACT_MANIFEST_SCHEMA:
        errors.append("artifact manifest schema mismatch")
    if payload.get("version") != ARTIFACT_MANIFEST_VERSION:
        errors.append("artifact manifest version mismatch")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        return errors + ["artifacts must be a list"]

    if payload.get("artifact_count") != len(artifacts):
        errors.append("artifact_count does not match artifacts length")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            errors.append(f"artifact[{index}] must be an object")
            continue

        artifact_id = str(record.get("artifact_id", ""))
        relative = str(record.get("path", ""))

        if artifact_id in seen_ids:
            errors.append(f"duplicate artifact_id: {artifact_id}")
        seen_ids.add(artifact_id)

        if relative in seen_paths:
            errors.append(f"duplicate artifact path: {relative}")
        seen_paths.add(relative)

        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"artifact path escapes root: {relative}")
            continue

        if not candidate.is_file():
            errors.append(f"artifact missing: {relative}")
            continue

        actual_size = candidate.stat().st_size
        if record.get("size") != actual_size:
            errors.append(f"artifact size drift: {relative}")

        actual_hash = sha256_file(candidate)
        if record.get("sha256") != actual_hash:
            errors.append(f"artifact hash drift: {relative}")

    return errors
