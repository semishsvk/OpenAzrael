#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import trimesh

from tools.remaster_framework.gltf_raw import accessor_array, read_glb
from tools.remaster_framework.fidelity import (
    FIDELITY_SCHEMA,
    FIDELITY_VERSION,
    canonical_json_sha256,
    validate_room_fidelity_manifest,
)

DEFAULT_OUT=ROOT/"data/runtime_generated/demo_room_fidelity_v124.json"
QUANTIZATION=1e-5
EXPECTED={
    "R1":{"path":ROOT/"assets/rooms/R1.glb","meshes":69,"triangles":593},
    "R7":{"path":ROOT/"assets/rooms/R7.glb","meshes":48,"triangles":689},
    "R8":{"path":ROOT/"assets/rooms/R8.glb","meshes":87,"triangles":1050},
}

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def quantized_text_sha(values:np.ndarray)->str:
    flat=np.asarray(values,dtype=float).reshape(-1)
    text=",".join(str(int(round(float(v)/QUANTIZATION))) for v in flat)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def room_record(room_id:str,spec:dict)->dict:
    path=Path(spec["path"])
    if not path.is_file():
        raise FileNotFoundError(path)
    gltf,binary=read_glb(path)
    raw_uv={}
    for node in gltf.get("nodes",[]):
        mesh_index=node.get("mesh")
        if mesh_index is None:
            continue
        primitives=gltf["meshes"][mesh_index].get("primitives",[])
        if len(primitives)!=1:
            continue
        uv_index=primitives[0].get("attributes",{}).get("TEXCOORD_0")
        if uv_index is not None:
            raw_uv[str(node.get("name",""))]=accessor_array(gltf,binary,uv_index)
    scene=trimesh.load(path,force="scene")
    meshes=[]
    for node in sorted(scene.graph.nodes_geometry):
        transform,geom_name=scene.graph[node]
        geom=scene.geometry[geom_name]
        md=geom.metadata or {}
        # Fidelity references must use raw glTF TEXCOORD_0.  Trimesh converts
        # V to its own internal convention when loading, which would invert the
        # reference and hide exactly the class of bug v133 is intended to catch.
        uv=np.asarray(raw_uv.get(str(node),np.empty((0,2))),dtype=float)
        if uv.ndim!=2: uv=np.empty((0,2))
        bounds=np.asarray(geom.bounds,dtype=float).reshape(-1)
        meshes.append({
            "node":str(node),
            "object":md.get("xaf_object"),
            "material":md.get("xaf_material"),
            "texture":md.get("xaf_texture"),
            "vertices":int(len(geom.vertices)),
            "triangles":int(len(geom.faces)),
            "uv_count":int(len(uv)),
            "uv_sha256":quantized_text_sha(uv),
            "uv_convention":"RAW_GLTF_UPPER_LEFT",
            "transform":[round(float(v),6) for v in np.asarray(transform,dtype=float).reshape(-1)],
            "bounds":[round(float(v),6) for v in bounds],
            "source_hidden_material":str(md.get("xaf_material") or "") in {"TRANSPARANT","CLEAR_OBJECT"},
            "legacy_colorkey":bool(md.get("xaf_texture") and "#" in Path(str(md.get("xaf_texture"))).stem),
        })
    result={
        "asset_path":str(path.relative_to(ROOT)).replace("\\","/"),
        "asset_bytes":path.stat().st_size,
        "asset_sha256":sha256_file(path),
        "mesh_count":len(meshes),
        "triangle_count":sum(m["triangles"] for m in meshes),
        "meshes":meshes,
    }
    if result["mesh_count"]!=spec["meshes"] or result["triangle_count"]!=spec["triangles"]:
        raise ValueError(f"{room_id}: canonical mesh/triangle count mismatch")
    result["room_fingerprint"]=canonical_json_sha256(result)
    return result

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    args=ap.parse_args()
    try:
        rooms={rid:room_record(rid,spec) for rid,spec in EXPECTED.items()}
        payload={
            "schema":FIDELITY_SCHEMA,
            "version":FIDELITY_VERSION,
            "producer":"OpenAzrael v124 source-derived GLB fidelity census with raw glTF UV reference",
            "quantization":QUANTIZATION,
            "rooms":rooms,
        }
        errors=validate_room_fidelity_manifest(payload)
        if errors: raise ValueError("; ".join(errors))
        payload["manifest_sha256"]=canonical_json_sha256(payload)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":"PASS","out":str(args.out),"rooms":{k:{"meshes":v["mesh_count"],"triangles":v["triangle_count"]} for k,v in rooms.items()}},indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"FAIL","error":str(exc)},indent=2))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
