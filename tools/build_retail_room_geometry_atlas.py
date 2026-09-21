#!/usr/bin/env python3
"""Build source-safe top-down room geometry thumbnails and a coverage manifest.

Consumes locally restored/generated GLB room assets (commercial payloads stay local).
Outputs only derived preview PNGs plus compact geometry metadata.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOM_RE = re.compile(r"^R(\d+)\.glb$", re.I)
DEFAULT_SKIP = re.compile(r"^(zx|zy|zq)|(^object\d*)|view|spaview|entcori", re.I)


def room_sort_key(path: Path):
    m = ROOM_RE.match(path.name)
    return int(m.group(1)) if m else 10**9


def world_geometry(scene: trimesh.Scene, skip: re.Pattern[str]):
    records = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        search_name = f"{node} {geom_name}"
        if skip.search(search_name):
            continue
        geom = scene.geometry[geom_name]
        vertices = trimesh.transform_points(geom.vertices, transform)
        records.append((str(node), str(geom_name), vertices, np.asarray(geom.faces, dtype=np.int64)))
    return records


def render_topdown(records, out: Path, width=360, height=240, padding=10):
    points = [v[:, [0, 2]] for _, _, v, _ in records if len(v)]
    if not points:
        raise ValueError("room has no renderable geometry after filtering")
    points_all = np.vstack(points)
    mn = points_all.min(axis=0)
    mx = points_all.max(axis=0)
    span = np.maximum(mx - mn, 1e-9)
    scale = min((width - 2 * padding) / span[0], (height - 2 * padding) / span[1])
    center = (mn + mx) * 0.5

    def tx(p):
        q = (p - center) * scale
        return float(q[0] + width * 0.5), float(height * 0.5 - q[1])

    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    edge_count = 0
    for _, _, vertices3, faces in records:
        vertices = vertices3[:, [0, 2]]
        edges = set()
        for f in faces:
            for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                a, b = int(a), int(b)
                if a > b:
                    a, b = b, a
                edges.add((a, b))
        edge_count += len(edges)
        for a, b in edges:
            draw.line([tx(vertices[a]), tx(vertices[b])], fill=(20, 20, 20, 220), width=1)
    img.save(out)
    return {
        "xz_bounds": [mn.tolist(), mx.tolist()],
        "projected_edge_count": edge_count,
        "preview_png": out.name,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("room_dir", type=Path, help="Directory containing locally restored/generated R*.glb room files")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--inventory", type=Path, help="Optional OpenAzrael retail_room_inventory JSON; used only for coverage counts")
    ap.add_argument("--bindings", type=Path, help="Optional JSON mapping room asset stem (e.g. R43) to canonical location(s). Never inferred from runtime IDs.")
    ap.add_argument("--width", type=int, default=360)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--skip-regex", default=DEFAULT_SKIP.pattern)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    skip = re.compile(args.skip_regex, re.I)

    inventory_meta = json.loads(args.inventory.read_text(encoding="utf-8")) if args.inventory else None
    bindings = {}
    if args.bindings:
        raw_bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
        bindings = raw_bindings.get("bindings", raw_bindings)

    rooms = []
    for path in sorted(args.room_dir.glob("R*.glb"), key=room_sort_key):
        m = ROOM_RE.match(path.name)
        if not m:
            continue
        numeric_id = int(m.group(1))
        scene = trimesh.load(path, force="scene")
        records = world_geometry(scene, skip)
        if not records:
            continue
        combined = scene.to_geometry()
        preview = args.out_dir / f"R{numeric_id}_topdown.png"
        projected = render_topdown(records, preview, args.width, args.height)
        rooms.append({
            "room_asset": path.name,
            "numeric_room_id": numeric_id,
            "canonical_candidates": bindings.get(path.stem, []),
            "geometry_nodes_rendered": len(records),
            "vertices_total": int(len(combined.vertices)),
            "triangles_total": int(len(combined.faces)),
            "xyz_bounds": combined.bounds.tolist(),
            **projected,
            "source_status": "LOCAL_DERIVED_GLTF_GEOMETRY",
        })

    result = {
        "schema": "openazrael.retail_room_geometry_atlas",
        "version": 1,
        "source_policy": "Local room binaries/GLBs are inputs only and are not copied into this manifest.",
        "room_dir": str(args.room_dir),
        "room_assets_found": len(rooms),
        "inventory_canonical_room_count": inventory_meta.get("canonical_room_count") if inventory_meta else None,
        "rooms": rooms,
    }
    out_json = args.out_dir / "room_geometry_atlas.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "rooms": len(rooms), "manifest": str(out_json)}, indent=2))


if __name__ == "__main__":
    main()
