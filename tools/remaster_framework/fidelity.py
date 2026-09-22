from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FIDELITY_SCHEMA = "remaster.room_fidelity_manifest"
FIDELITY_VERSION = 1
REPORT_SCHEMA = "remaster.room_forensic_report"
REPORT_VERSION = 1

@dataclass(frozen=True)
class FidelityLayer:
    layer_id: str
    status: str
    fingerprint: str
    details: dict[str, Any]

def canonical_json_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def validate_room_fidelity_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != FIDELITY_SCHEMA:
        errors.append("unsupported room fidelity schema")
    if payload.get("version") != FIDELITY_VERSION:
        errors.append("unsupported room fidelity version")
    if float(payload.get("quantization", 0)) <= 0:
        errors.append("quantization must be positive")
    rooms = payload.get("rooms")
    if not isinstance(rooms, dict) or not rooms:
        errors.append("rooms must be a non-empty object")
        return errors
    for room_id, room in rooms.items():
        if not isinstance(room, dict):
            errors.append(f"{room_id}: room record must be an object")
            continue
        sha = str(room.get("asset_sha256", ""))
        if len(sha) != 64:
            errors.append(f"{room_id}: invalid asset_sha256")
        meshes = room.get("meshes")
        if not isinstance(meshes, list):
            errors.append(f"{room_id}: meshes must be a list")
            continue
        if int(room.get("mesh_count", -1)) != len(meshes):
            errors.append(f"{room_id}: mesh_count mismatch")
        names: set[str] = set()
        triangles = 0
        for mesh in meshes:
            name = str(mesh.get("node", ""))
            if not name:
                errors.append(f"{room_id}: empty mesh node")
            if name in names:
                errors.append(f"{room_id}: duplicate mesh node {name}")
            names.add(name)
            triangles += int(mesh.get("triangles", 0))
            if len(str(mesh.get("uv_sha256", ""))) not in (0, 64):
                errors.append(f"{room_id}/{name}: invalid uv_sha256")
            if len(mesh.get("transform", [])) != 16:
                errors.append(f"{room_id}/{name}: transform must contain 16 values")
            if len(mesh.get("bounds", [])) != 6:
                errors.append(f"{room_id}/{name}: bounds must contain 6 values")
        if int(room.get("triangle_count", -1)) != triangles:
            errors.append(f"{room_id}: triangle_count mismatch")
    return errors

def build_forensic_report(
    room_id: str,
    layers: list[FidelityLayer],
    required_layers: tuple[str, ...],
) -> dict[str, Any]:
    by_id = {layer.layer_id: layer for layer in layers}
    missing = [layer_id for layer_id in required_layers if layer_id not in by_id]
    failed = [
        layer.layer_id
        for layer in layers
        if layer.layer_id in required_layers and layer.status != "PASS"
    ]
    transitions = []
    ordered = [by_id[layer_id] for layer_id in required_layers if layer_id in by_id]
    for before, after in zip(ordered, ordered[1:]):
        transitions.append({
            "from": before.layer_id,
            "to": after.layer_id,
            "fingerprint_equal": before.fingerprint == after.fingerprint,
        })
    return {
        "schema": REPORT_SCHEMA,
        "version": REPORT_VERSION,
        "room_id": room_id,
        "status": "PASS" if not missing and not failed else "FAIL",
        "missing_layers": missing,
        "failed_layers": failed,
        "layers": [
            {
                "layer_id": layer.layer_id,
                "status": layer.status,
                "fingerprint": layer.fingerprint,
                "details": layer.details,
            }
            for layer in layers
        ],
        "transitions": transitions,
    }
