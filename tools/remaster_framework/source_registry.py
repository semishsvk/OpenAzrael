from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from tools.remaster_framework.inventory import build_inventory


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = ROOT / "data/source_corpora_contract_v1.json"


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path | None = None) -> dict[str, Any]:
    contract_path = (path or DEFAULT_CONTRACT).resolve()
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "openazrael.source_corpora_contract":
        raise ValueError("unsupported source corpus contract schema")
    if payload.get("version") != 1:
        raise ValueError("unsupported source corpus contract version")
    return payload


def source_home(
    contract: dict[str, Any] | None = None,
    explicit: Path | None = None,
) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    payload = contract or load_contract()
    local = payload.get("local_registry", {})
    env_name = str(local.get("env", "OPENAZRAEL_SOURCE_HOME"))
    if os.environ.get(env_name):
        return Path(os.environ[env_name]).expanduser().resolve()
    default = str(local.get("default", "~/.openazrael/sources"))
    return Path(default).expanduser().resolve()


def registry_path(
    contract: dict[str, Any] | None = None,
    home: Path | None = None,
) -> Path:
    payload = contract or load_contract()
    base = source_home(payload, home)
    name = str(payload.get("local_registry", {}).get("registry_file", "registry.json"))
    return base / name


def _empty_registry(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "openazrael.source_registry.local",
        "version": 1,
        "project_id": contract.get("project_id", "openazrael"),
        "sources": {},
    }


def load_registry(
    contract: dict[str, Any] | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    payload = contract or load_contract()
    path = registry_path(payload, home)
    if not path.is_file():
        return _empty_registry(payload)
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") != "openazrael.source_registry.local":
        raise ValueError("unsupported local source registry schema")
    if registry.get("version") != 1:
        raise ValueError("unsupported local source registry version")
    return registry


def save_registry(
    registry: dict[str, Any],
    contract: dict[str, Any] | None = None,
    home: Path | None = None,
) -> Path:
    payload = contract or load_contract()
    path = registry_path(payload, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _entry_for_kind(contract: dict[str, Any], kind: str) -> dict[str, Any]:
    corpora = contract.get("corpora", {})
    if kind not in corpora:
        raise KeyError(f"unknown corpus kind: {kind}")
    entry = corpora[kind]
    if not isinstance(entry, dict):
        raise ValueError(f"invalid corpus contract entry: {kind}")
    return entry


def _iter_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink()
        ),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )


def _match_name_or_relative(root: Path, path: Path, pattern: str) -> bool:
    folded = pattern.casefold()
    name = path.name.casefold()
    relative = path.relative_to(root).as_posix().casefold()
    return fnmatch.fnmatch(name, folded) or fnmatch.fnmatch(relative, folded)


def evaluate_shape(root: Path, shape: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    files = _iter_files(root)
    missing_exact: list[str] = []
    for expected in shape.get("required_exact", []):
        folded = str(expected).casefold()
        if not any(
            path.name.casefold() == folded
            or path.relative_to(root).as_posix().casefold() == folded
            for path in files
        ):
            missing_exact.append(str(expected))

    pattern_results: list[dict[str, Any]] = []
    pattern_failures: list[str] = []
    for rule in shape.get("required_patterns", []):
        pattern = str(rule["pattern"])
        minimum = int(rule.get("min_count", 1))
        actual = sum(
            1 for path in files if _match_name_or_relative(root, path, pattern)
        )
        passed = actual >= minimum
        pattern_results.append(
            {
                "pattern": pattern,
                "min_count": minimum,
                "actual_count": actual,
                "pass": passed,
            }
        )
        if not passed:
            pattern_failures.append(pattern)

    count_results: list[dict[str, Any]] = []
    count_failures: list[str] = []
    for rule in shape.get("expected_counts", []):
        pattern = str(rule["pattern"])
        expected = int(rule["count"])
        actual = sum(
            1 for path in files if _match_name_or_relative(root, path, pattern)
        )
        passed = actual == expected
        count_results.append(
            {
                "pattern": pattern,
                "expected_count": expected,
                "actual_count": actual,
                "pass": passed,
            }
        )
        if not passed:
            count_failures.append(pattern)

    evidence_patterns: list[dict[str, Any]] = []
    for pattern in shape.get("evidence_patterns", []):
        actual = sum(
            1
            for path in files
            if _match_name_or_relative(root, path, str(pattern))
        )
        evidence_patterns.append(
            {
                "pattern": str(pattern),
                "actual_count": actual,
                "observed": actual > 0,
            }
        )

    passed = not missing_exact and not pattern_failures and not count_failures
    return {
        "status": "PASS" if passed else "FAIL",
        "file_count": len(files),
        "missing_exact": missing_exact,
        "required_patterns": pattern_results,
        "expected_counts": count_results,
        "evidence_patterns": evidence_patterns,
    }


def _find_extracted_root(base: Path, shape: dict[str, Any]) -> Path:
    candidates = [base]
    candidates.extend(
        path
        for path in base.iterdir()
        if path.is_dir() and not path.is_symlink()
    )
    matches = [
        candidate
        for candidate in candidates
        if evaluate_shape(candidate, shape).get("status") == "PASS"
    ]
    if not matches:
        raise ValueError("materialized archive does not match corpus shape")
    matches.sort(key=lambda path: (len(path.parts), path.name.casefold()))
    return matches[0]


def _safe_extract_zip(source: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(source, "r") as archive:
        for info in archive.infolist():
            member = (destination / info.filename).resolve()
            try:
                member.relative_to(destination)
            except ValueError as exc:
                raise ValueError(
                    f"unsafe archive member outside destination: {info.filename}"
                ) from exc
        archive.extractall(destination)


def _extract_until_shape(
    source: Path,
    destination: Path,
    shape: dict[str, Any],
    *,
    max_nested_archives: int = 3,
) -> Path:
    current_archive=source
    for depth in range(max_nested_archives+1):
        layer=destination/f"layer{depth}"
        layer.mkdir(parents=True,exist_ok=True)
        _safe_extract_zip(current_archive,layer)
        try:
            return _find_extracted_root(layer,shape)
        except ValueError:
            pass
        nested=[path for path in _iter_files(layer) if zipfile.is_zipfile(path)]
        if len(nested)!=1:
            raise ValueError(
                "materialized archive does not match corpus shape and "
                f"nested ZIP candidate count is {len(nested)} at depth {depth}"
            )
        current_archive=nested[0]
    raise ValueError(
        "materialized archive does not match corpus shape after nested ZIP materialization"
    )


def _mirror_directory(
    source: Path,
    home: Path,
    corpus_id: str,
    fingerprint: str,
) -> Path:
    destination = home / "mirrors" / corpus_id / fingerprint[:16]
    if destination.is_dir():
        return destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return destination.resolve()


def _mirror_archive(
    source: Path,
    home: Path,
    corpus_id: str,
    fingerprint: str,
) -> Path:
    destination = (
        home
        / "bundles"
        / corpus_id
        / fingerprint[:16]
        / source.name
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file():
        shutil.copy2(source, destination)
    return destination.resolve()


def register_source(
    kind: str,
    source: Path,
    *,
    mirror: bool = False,
    contract_path: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    spec = _entry_for_kind(contract, kind)
    registry = load_registry(contract, home)
    base = source_home(contract, home)
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    accepted = set(str(x) for x in spec.get("accepted_source_types", []))
    if source.is_file():
        source_type = "zip" if zipfile.is_zipfile(source) else "file"
    elif source.is_dir():
        source_type = "directory"
    else:
        raise ValueError("source must be a regular file or directory")
    if source_type not in accepted:
        raise ValueError(
            f"{kind} corpus does not accept source type {source_type!r}; "
            f"accepted={sorted(accepted)}"
        )

    row: dict[str, Any] = {
        "corpus_id": spec["corpus_id"],
        "kind": kind,
        "source_type": source_type,
        "contract_status": spec.get("status"),
    }

    if source_type == "zip":
        archive = spec.get("canonical_archive")
        if not isinstance(archive, dict):
            raise ValueError(f"{kind} has no canonical archive contract")
        actual_size = source.stat().st_size
        actual_sha = _sha256(source)
        expected_size = int(archive["bytes"])
        expected_sha = str(archive["sha256"])
        if actual_size != expected_size or actual_sha != expected_sha:
            raise ValueError(
                f"{kind} archive identity mismatch: "
                f"bytes={actual_size}/{expected_size}, sha256={actual_sha}/{expected_sha}"
            )
        registered = (
            _mirror_archive(source, base, str(spec["corpus_id"]), actual_sha)
            if mirror
            else source
        )
        row.update(
            {
                "identity_status": "EXACT_CANONICAL_ARCHIVE",
                "source_path": str(registered),
                "archive_bytes": actual_size,
                "archive_sha256": actual_sha,
                "mirrored": bool(mirror),
            }
        )
    else:
        shape = evaluate_shape(source, spec.get("extracted_shape", {}))
        if shape["status"] != "PASS":
            raise ValueError(
                f"{kind} directory failed corpus shape: "
                + json.dumps(shape, sort_keys=True)
            )
        inventory = build_inventory(source)
        fingerprint = str(inventory["corpus_sha256"])
        registered = (
            _mirror_directory(source, base, str(spec["corpus_id"]), fingerprint)
            if mirror
            else source
        )
        manifest_dir = base / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"{spec['corpus_id']}-{fingerprint[:16]}.json"
        manifest_path.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        row.update(
            {
                "identity_status": (
                    "LOCAL_FULL_INVENTORY_PIN"
                    if kind == "retail"
                    else "EXTRACTED_FULL_INVENTORY_PIN"
                ),
                "source_path": str(registered),
                "inventory_sha256": fingerprint,
                "file_count": int(inventory["file_count"]),
                "total_size": int(inventory["total_size"]),
                "inventory_manifest": str(manifest_path),
                "shape": shape,
                "mirrored": bool(mirror),
            }
        )

    registry.setdefault("sources", {})[kind] = row
    save_registry(registry, contract, home)
    return row


def _registered_row(
    kind: str,
    *,
    contract_path: Path | None = None,
    home: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    contract = load_contract(contract_path)
    registry = load_registry(contract, home)
    row = registry.get("sources", {}).get(kind)
    if not isinstance(row, dict):
        raise FileNotFoundError(
            f"{kind} source is not registered; run bootstrap_openazrael_sources.py register"
        )
    path = Path(str(row.get("source_path", ""))).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"registered {kind} source is missing: {path}"
        )
    return contract, row, path.resolve()


def verify_registered_source(
    kind: str,
    *,
    contract_path: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    contract, row, path = _registered_row(
        kind,
        contract_path=contract_path,
        home=home,
    )
    spec = _entry_for_kind(contract, kind)
    failures: list[str] = []

    if row.get("source_type") == "zip":
        archive = spec.get("canonical_archive", {})
        actual_size = path.stat().st_size
        actual_sha = _sha256(path)
        if actual_size != int(archive.get("bytes", -1)):
            failures.append("archive_size_changed")
        if actual_sha != str(archive.get("sha256", "")):
            failures.append("archive_sha256_changed")
    elif row.get("source_type") == "directory":
        shape = evaluate_shape(path, spec.get("extracted_shape", {}))
        if shape.get("status") != "PASS":
            failures.append("corpus_shape_changed")
        inventory = build_inventory(path)
        if inventory.get("corpus_sha256") != row.get("inventory_sha256"):
            failures.append("inventory_sha256_changed")
        if int(inventory.get("file_count", -1)) != int(row.get("file_count", -2)):
            failures.append("file_count_changed")
        if int(inventory.get("total_size", -1)) != int(row.get("total_size", -2)):
            failures.append("total_size_changed")
    else:
        failures.append("unsupported_registered_source_type")

    return {
        "schema": "openazrael.source_registry_verification",
        "version": 1,
        "kind": kind,
        "corpus_id": row.get("corpus_id"),
        "status": "PASS" if not failures else "FAIL",
        "source_path": str(path),
        "identity_status": row.get("identity_status"),
        "failures": failures,
    }


def resolve_source(
    kind: str,
    *,
    verify: bool = True,
    materialize_archive: bool = True,
    contract_path: Path | None = None,
    home: Path | None = None,
) -> Path:
    contract, row, path = _registered_row(
        kind,
        contract_path=contract_path,
        home=home,
    )
    if verify:
        result = verify_registered_source(
            kind,
            contract_path=contract_path,
            home=home,
        )
        if result["status"] != "PASS":
            raise ValueError(
                f"registered {kind} source failed verification: "
                + json.dumps(result["failures"])
            )

    if row.get("source_type") == "directory":
        return path
    if row.get("source_type") != "zip" or not materialize_archive:
        return path

    spec = _entry_for_kind(contract, kind)
    fingerprint = str(row.get("archive_sha256", ""))
    base = source_home(contract, home)
    destination = (
        base / "materialized" / str(spec["corpus_id"]) / fingerprint[:16]
    )
    marker = destination / ".openazrael_materialized.json"
    if marker.is_file():
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        candidate = Path(str(payload.get("root", "")))
        if (
            payload.get("archive_sha256") == fingerprint
            and candidate.is_dir()
        ):
            return candidate.resolve()

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = _extract_until_shape(
        path,
        destination,
        spec.get("extracted_shape", {}),
    )
    marker.write_text(
        json.dumps(
            {
                "schema": "openazrael.source_materialization",
                "version": 1,
                "kind": kind,
                "archive_sha256": fingerprint,
                "root": str(root.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return root.resolve()


def registry_status(
    *,
    contract_path: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    registry = load_registry(contract, home)
    rows: dict[str, Any] = {}
    for kind in contract.get("corpora", {}):
        row = registry.get("sources", {}).get(kind)
        if not isinstance(row, dict):
            rows[kind] = {
                "status": "UNREGISTERED",
                "corpus_id": contract["corpora"][kind].get("corpus_id"),
            }
            continue
        path = Path(str(row.get("source_path", ""))).expanduser()
        rows[kind] = {
            "status": "AVAILABLE" if path.exists() else "MISSING",
            "corpus_id": row.get("corpus_id"),
            "source_type": row.get("source_type"),
            "source_path": str(path),
            "identity_status": row.get("identity_status"),
            "mirrored": bool(row.get("mirrored")),
        }
    return {
        "schema": "openazrael.source_registry_status",
        "version": 1,
        "source_home": str(source_home(contract, home)),
        "registry": str(registry_path(contract, home)),
        "sources": rows,
    }


def write_runtime_binding(
    output: Path,
    *,
    contract_path: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    registry = load_registry(contract, home)
    bindings: dict[str, Any] = {}
    for kind, row in registry.get("sources", {}).items():
        if not isinstance(row, dict):
            continue
        try:
            root = resolve_source(
                kind,
                verify=True,
                materialize_archive=True,
                contract_path=contract_path,
                home=home,
            )
        except Exception as exc:
            bindings[kind] = {"status": "FAIL", "error": str(exc)}
            continue
        bindings[kind] = {
            "status": "PASS",
            "corpus_id": row.get("corpus_id"),
            "root": str(root),
            "identity_status": row.get("identity_status"),
            "archive_sha256": row.get("archive_sha256"),
            "inventory_sha256": row.get("inventory_sha256"),
        }
    payload = {
        "schema": "openazrael.source_runtime_binding",
        "version": 1,
        "sources": bindings,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload
