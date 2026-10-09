#!/usr/bin/env python3
from pathlib import Path
import argparse
import json

import numpy as np
import trimesh

ROOMS = ("R1", "R7", "R8")
PORTAL_TEXTURES = {"R12R7", "R72R1", "R82R1", "ORR2BAP"}
TRANSITIONS = (
    ("R1", "zxcoriR5", "R7", "spaview", "view"),
    ("R1", "zxcoriR2", "R8", "entcori", "Object14"),
    ("R7", "zxwell2R6", "R1", "view", "spaview"),
    ("R8", "zxorrery", "R1", "Object14", "entcori"),
)

def v3(value):
    return [round(float(x), 6) for x in value]

def load_room(input_dir: Path, room_id: str):
    glb_path = input_dir / f"{room_id}.textured.v4.glb"
    manifest_path = input_dir / f"{room_id}.textured.v4.manifest.json"
    if not glb_path.is_file():
        raise FileNotFoundError(glb_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    scene = trimesh.load(glb_path, force="scene")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    object_map = {obj["object"]: obj for obj in manifest["objects"]}
    triggers, views = [], []
    for name, geometry in scene.geometry.items():
        metadata = object_map.get(name, {})
        material = (metadata.get("material") or "").upper()
        texture = metadata.get("texture") or ""
        lower_name = name.lower()
        if material in {"TRANSPARANT", "CLEAR_OBJECT"} or lower_name.startswith(("zx", "zy")):
            triggers.append({
                "name": name, "material": material, "texture": texture or None,
                "centroid": v3(geometry.centroid),
                "bounds": [v3(geometry.bounds[0]), v3(geometry.bounds[1])],
            })
        if Path(texture).stem.upper() in PORTAL_TEXTURES:
            normal = np.asarray(geometry.face_normals, float).mean(axis=0)
            length = np.linalg.norm(normal)
            if length:
                normal /= length
            views.append({
                "name": name, "material": metadata.get("material"), "texture": texture,
                "centroid": v3(geometry.centroid), "normal": v3(normal),
                "bounds": [v3(geometry.bounds[0]), v3(geometry.bounds[1])],
            })
    return {"triggers": triggers, "portal_views": views}, scene

def by_name(items, name):
    try:
        return next(item for item in items if item["name"] == name)
    except StopIteration as exc:
        raise ValueError(f"required evidence object not found: {name}") from exc

def build(input_dir: Path):
    rooms, scenes = {}, {}
    for room_id in ROOMS:
        rooms[room_id], scenes[room_id] = load_room(input_dir, room_id)
    out = {"schema": 1, "source": "original demo XAF -> corrected v4 GLB", "rooms": rooms, "demo_transitions": []}
    for source_room, trigger_name, destination_room, source_view, destination_view in TRANSITIONS:
        trigger = by_name(rooms[source_room]["triggers"], trigger_name)
        source_portal = by_name(rooms[source_room]["portal_views"], source_view)
        by_name(rooms[destination_room]["portal_views"], destination_view)
        distance = float(np.linalg.norm(np.array(trigger["centroid"]) - np.array(source_portal["centroid"])))
        out["demo_transitions"].append({
            "source_room": source_room, "trigger": trigger_name, "destination_room": destination_room,
            "source_view": source_view, "destination_view": destination_view,
            "trigger_to_source_view_distance": round(distance, 3),
            "evidence": "invisible XAF trigger lies beside the matching portal-view quad; view texture encodes reciprocal room relation",
            "confidence": "high",
        })
    deep = []
    for name, geometry in scenes["R7"].geometry.items():
        if geometry.bounds[0, 1] < -1000:
            deep.append({"name": name, "centroid": v3(geometry.centroid), "bounds": [v3(geometry.bounds[0]), v3(geometry.bounds[1])]})
    out["r7_deep_shaft_evidence"] = deep
    return out

def main():
    parser = argparse.ArgumentParser(description="Extract source-safe R1/R7/R8 trigger and portal runtime IR from corrected demo GLBs.")
    parser.add_argument("--input-dir", required=True, type=Path, help="Directory containing R1/R7/R8.textured.v4.glb and matching manifest JSON files.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    output = build(args.input_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "trigger_counts": {room: len(output["rooms"][room]["triggers"]) for room in ROOMS},
        "portal_counts": {room: len(output["rooms"][room]["portal_views"]) for room in ROOMS},
        "transitions": len(output["demo_transitions"]),
        "r7_deep_objects": len(output["r7_deep_shaft_evidence"]),
        "out": str(args.out),
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
