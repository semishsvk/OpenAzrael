#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json


def _import_trimesh():
    try:
        import trimesh
    except Exception as exc:
        raise SystemExit(
            "oa_tex_sampling_audit requires the optional local dependency 'trimesh'"
        ) from exc
    return trimesh


def aggregate_uv_bounds(scene, primitive_rows: list[dict]) -> dict:
    mins = []
    maxs = []
    primitive_evidence = []
    for row in primitive_rows:
        node = str(row["node"])
        geometry = scene.geometry.get(node)
        if geometry is None:
            raise KeyError(f"GLB geometry missing for manifest node: {node}")
        uv = getattr(geometry.visual, "uv", None)
        if uv is None or len(uv) == 0:
            raise ValueError(f"UV set missing for GLB geometry: {node}")
        mn = uv.min(axis=0)
        mx = uv.max(axis=0)
        mins.append(mn)
        maxs.append(mx)
        primitive_evidence.append(
            {
                "object": row.get("object"),
                "node": node,
                "triangles": row.get("triangles"),
                "uv_min": [round(float(mn[0]), 6), round(float(mn[1]), 6)],
                "uv_max": [round(float(mx[0]), 6), round(float(mx[1]), 6)],
            }
        )

    import numpy as np

    uv_min = np.vstack(mins).min(axis=0)
    uv_max = np.vstack(maxs).max(axis=0)
    eps = 0.01
    return {
        "primitive_uses": len(primitive_rows),
        "uv_min": [round(float(uv_min[0]), 6), round(float(uv_min[1]), 6)],
        "uv_max": [round(float(uv_max[0]), 6), round(float(uv_max[1]), 6)],
        "significant_outside_unit_square": bool(
            (uv_min < -eps).any() or (uv_max > 1.0 + eps).any()
        ),
        "spans_near_full_u": bool(uv_min[0] <= 0.02 and uv_max[0] >= 0.98),
        "spans_near_full_v": bool(uv_min[1] <= 0.02 and uv_max[1] >= 0.98),
        "primitives": primitive_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit real GLB UV usage for the canonical Texture Lab POC selection."
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument("--manifest-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--room-dir", type=Path, default=ROOT / "assets/rooms")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/texture_lab/rt_poc_01_sampling_audit.json",
    )
    args = parser.parse_args()

    trimesh = _import_trimesh()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    room_cache = {}
    rows = []

    for entry in selection["textures"]:
        texture_id = str(entry["id"])
        room = str(entry["room"])
        if room not in room_cache:
            manifest_path = args.manifest_dir / f"{room}.textured.v44.manifest.json"
            room_path = args.room_dir / f"{room}.glb"
            if not manifest_path.is_file():
                raise SystemExit(f"missing v44 manifest: {manifest_path}")
            if not room_path.is_file():
                raise SystemExit(f"missing room GLB: {room_path}")
            room_cache[room] = (
                json.loads(manifest_path.read_text(encoding="utf-8")),
                trimesh.load(room_path, force="scene"),
            )

        manifest, scene = room_cache[room]
        expected_png = texture_id.upper() + ".PNG"
        primitive_rows = [
            row
            for row in manifest["primitives"]
            if str(row.get("resolved_png") or "").upper() == expected_png
        ]
        if not primitive_rows:
            raise SystemExit(f"{texture_id}: no primitive usage found in {room}")

        audit = aggregate_uv_bounds(scene, primitive_rows)
        rows.append(
            {
                "id": texture_id,
                "room": room,
                "content_class": entry.get("content_class"),
                **audit,
            }
        )

    write_json(
        args.out,
        {
            "schema": "openazrael.texture_lab.rt_poc_01_sampling_audit.v1",
            "status": "OBSERVATIONAL",
            "interpretation_policy": (
                "UV bounds are measured evidence. Out-of-range UV implies repeat sampling "
                "under the v44 GLB default sampler; near-full 0..1 coverage alone does not "
                "prove that opposite texture edges are a physical seam."
            ),
            "textures": rows,
        },
    )
    print(f"PASS sampling_audit textures={len(rows)} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
