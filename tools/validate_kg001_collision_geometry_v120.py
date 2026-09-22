#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data/tests/kg001_collision_role_contract_v120.json"
ROOM_MANAGER_PATH = ROOT / "scripts/room_manager.gd"
ROOM_PATHS = {
    "R1": ROOT / "assets/rooms/R1.glb",
    "R7": ROOT / "assets/rooms/R7.glb",
    "R8": ROOT / "assets/rooms/R8.glb",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _glb_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != b"glTF":
        raise ValueError(f"{path}: not a GLB")
    version, declared_length = struct.unpack_from("<II", raw, 4)
    if version != 2:
        raise ValueError(f"{path}: unsupported GLB version {version}")
    if declared_length != len(raw):
        raise ValueError(
            f"{path}: declared length {declared_length} != {len(raw)}"
        )

    offset = 12
    while offset + 8 <= len(raw):
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        payload = raw[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            return json.loads(payload.rstrip(b" \t\r\n\x00"))
    raise ValueError(f"{path}: JSON chunk missing")


def _mesh_record(document: dict[str, Any], object_name: str) -> dict[str, Any]:
    nodes = document.get("nodes", [])
    meshes = document.get("meshes", [])
    accessors = document.get("accessors", [])

    object_node = next(
        (
            node
            for node in nodes
            if isinstance(node, dict) and node.get("name") == object_name
        ),
        None,
    )
    if not isinstance(object_node, dict):
        raise ValueError(f"node {object_name!r} missing")

    mesh_index = object_node.get("mesh")
    if mesh_index is None:
        for child_index in object_node.get("children", []):
            if not isinstance(child_index, int) or child_index >= len(nodes):
                continue
            child = nodes[child_index]
            if isinstance(child, dict) and child.get("mesh") is not None:
                mesh_index = child["mesh"]
                break
    if not isinstance(mesh_index, int) or mesh_index >= len(meshes):
        raise ValueError(f"mesh for {object_name!r} missing")

    mesh = meshes[mesh_index]
    if not isinstance(mesh, dict):
        raise ValueError(f"mesh for {object_name!r} invalid")

    triangle_count = 0
    for primitive in mesh.get("primitives", []):
        if not isinstance(primitive, dict):
            continue
        indices = primitive.get("indices")
        mode = int(primitive.get("mode", 4))
        if mode != 4 or not isinstance(indices, int) or indices >= len(accessors):
            continue
        count = int(accessors[indices].get("count", 0))
        triangle_count += count // 3

    extras = mesh.get("extras", {})
    if not isinstance(extras, dict):
        extras = {}
    return {
        "mesh_name": str(mesh.get("name", "")),
        "xaf_object": str(extras.get("xaf_object", "")),
        "xaf_material": str(extras.get("xaf_material", "")),
        "xaf_texture": extras.get("xaf_texture"),
        "triangle_count": triangle_count,
    }


def build_report() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks: dict[str, bool] = {}

    checks["contract_schema"] = (
        contract.get("schema") == "openazrael.kg001.collision_role_contract"
        and contract.get("version") == 120
    )

    documents: dict[str, dict[str, Any]] = {}
    asset_hashes: dict[str, str] = {}
    for room, path in ROOM_PATHS.items():
        if not path.is_file():
            errors.append(f"missing room asset: {path.relative_to(ROOT)}")
            continue
        actual_hash = _sha256(path)
        asset_hashes[room] = actual_hash
        expected_hash = str(
            contract.get("source_assets", {})
            .get(room, {})
            .get("sha256", "")
        )
        if actual_hash != expected_hash:
            errors.append(
                f"{room} SHA-256 mismatch: {actual_hash} != {expected_hash}"
            )
        try:
            documents[room] = _glb_json(path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))

    role_results: list[dict[str, Any]] = []
    for role in contract.get("roles", []):
        if not isinstance(role, dict):
            errors.append("invalid role row")
            continue
        room = str(role.get("room", ""))
        object_name = str(role.get("object", ""))
        document = documents.get(room)
        if document is None:
            continue
        try:
            actual = _mesh_record(document, object_name)
        except ValueError as exc:
            errors.append(f"{room}/{object_name}: {exc}")
            continue

        role_errors: list[str] = []
        for field in ("xaf_material", "triangle_count"):
            if actual.get(field) != role.get(field):
                role_errors.append(
                    f"{field}: {actual.get(field)!r} != {role.get(field)!r}"
                )
        expected_texture = role.get("xaf_texture")
        if expected_texture is not None and actual.get("xaf_texture") != expected_texture:
            role_errors.append(
                f"xaf_texture: {actual.get('xaf_texture')!r} "
                f"!= {expected_texture!r}"
            )
        if actual.get("xaf_object") != object_name:
            role_errors.append(
                f"xaf_object: {actual.get('xaf_object')!r} != {object_name!r}"
            )

        role_results.append(
            {
                "room": room,
                "object": object_name,
                "collision_required": bool(role.get("collision_required")),
                "actual": actual,
                "status": "PASS" if not role_errors else "FAIL",
                "errors": role_errors,
            }
        )
        errors.extend(
            f"{room}/{object_name}: {message}"
            for message in role_errors
        )

    source = ROOM_MANAGER_PATH.read_text(encoding="utf-8")
    source_checks = {
        "room_specific_exclusions": (
            "NON_COLLIDING_OBJECTS_BY_ROOM" in source
            and '"R7": {' in source
            and '"Object02": true' in source
            and '"Object03": true' in source
        ),
        "r1_object02_not_global_blacklist": (
            'obj_name in ["Object02", "Object03"' not in source
        ),
        "portal_views_derived_per_room": (
            "func _portal_view_names(room_id: String)" in source
            and "portal_views.has(obj_name)" in source
        ),
        "two_sided_legacy_collision": "backface_collision = true" in source,
        "r1_support_diagnostic": (
            '"critical_collision_support_missing"' in source
            and 'collision_objects.has("Object02")' in source
        ),
    }
    checks.update(source_checks)

    for name, passed in checks.items():
        if not passed:
            errors.append(f"check failed: {name}")

    return {
        "schema": "openazrael.kg001.collision_geometry_validation",
        "version": 120,
        "status": "PASS" if not errors else "FAIL",
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "room_manager": str(ROOM_MANAGER_PATH.relative_to(ROOT)),
        "asset_sha256": asset_hashes,
        "checks": checks,
        "roles": role_results,
        "errors": errors,
        "boundary": (
            "Validates exact restored GLB identity, collision-role metadata and "
            "runtime source policy. Physical traversal remains the final oracle."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
