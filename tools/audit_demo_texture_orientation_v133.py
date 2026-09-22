#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, math, sys
import numpy as np
import trimesh
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ROOM_IDS=("R1","R7","R8")
ROOM_DIR=ROOT/"assets/rooms"
TEX_DIR=ROOT/"assets/textures/classic"
CANONICAL_GRAPHICS=ROOT/"data/graphics_pipeline_validation_v44.json"
CONTRACT=ROOT/"data/tests/kg001_texture_orientation_contract_v133.json"
DEFAULT_OUT=ROOT/"data/runtime_generated/demo_texture_orientation_v133.json"

def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def rgba_hash(image)->str:
    arr=np.asarray(image.convert("RGBA"))
    return hashlib.sha256(arr.tobytes()).hexdigest()

def corr(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    if len(a)<2 or np.std(a)<1e-8 or np.std(b)<1e-8:return None
    return float(np.corrcoef(a,b)[0,1])

def resolve_png(tex_name:str,index:dict[str,Path]):
    return index.get(Path(tex_name).stem.upper())

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    args=ap.parse_args()
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    canonical=json.loads(CANONICAL_GRAPHICS.read_text(encoding="utf-8"))
    failures=[]
    warnings=[]

    pngs=sorted(TEX_DIR.glob("*.png"))
    if len(pngs)!=int(contract["expected_classic_texture_count"]):
        failures.append(f"classic_texture_count:{len(pngs)}")
    tex_index={p.stem.upper():p for p in pngs}

    canonical_rows={row["file"]:row for row in canonical.get("textures",[])}
    if int(canonical.get("classic_texture_count",0))!=86 or len(canonical_rows)!=86:
        failures.append("canonical_graphics_inventory_invalid")
    texture_inventory=[]
    for p in pngs:
        row=canonical_rows.get(p.name)
        ok=row is not None and file_sha(p)==str(row.get("sha256",""))
        if not ok: failures.append("canonical_png_hash:"+p.name)
        texture_inventory.append({"file":p.name,"sha256":file_sha(p),"canonical_hash_match":ok})

    used=set()
    textured_primitive_count=0
    primitive_rows=[]
    strong_vertical=[]
    allowed={(x["room"],x["node"],x["texture"].upper()) for x in contract.get("allowed_source_authored_orientation_variants",[])}

    for room in ROOM_IDS:
        glb=ROOM_DIR/f"{room}.glb"
        manifest=ROOT/"data"/f"{room}.textured.v44.manifest.json"
        if not glb.is_file():
            failures.append("missing_glb:"+room);continue
        if not manifest.is_file():
            failures.append("missing_room_manifest:"+room);continue
        m=json.loads(manifest.read_text(encoding="utf-8"))
        corrections={str(x.get("uv_correction","NONE")) for x in m.get("primitives",[]) if str(x.get("uv_correction","NONE"))!="NONE"}
        expected_corr=set(contract.get("required_uv_corrections",{}).values())
        unexpected=corrections-expected_corr
        if unexpected: failures.append(room+":unexpected_uv_corrections:"+",".join(sorted(unexpected)))

        scene=trimesh.load(glb,force="scene")
        for node in scene.graph.nodes_geometry:
            T,gname=scene.graph[node]
            geom=scene.geometry[gname]
            md=geom.metadata or {}
            tex_name=md.get("xaf_texture")
            if not tex_name: continue
            textured_primitive_count+=1
            used.add(Path(str(tex_name)).stem.upper())
            png=resolve_png(str(tex_name),tex_index)
            if png is None:
                failures.append(f"{room}/{node}:missing_texture:{tex_name}")
                continue
            mat=getattr(geom.visual,"material",None)
            embedded=getattr(mat,"baseColorTexture",None) if mat is not None else None
            if embedded is None:
                failures.append(f"{room}/{node}:missing_embedded_texture")
                continue
            embedded_equal=rgba_hash(embedded)==rgba_hash(Image.open(png))
            if not embedded_equal:
                failures.append(f"{room}/{node}:embedded_texture_mismatch:{png.name}")

            V=np.asarray(geom.vertices,float)
            uv=np.asarray(getattr(geom.visual,"uv",np.zeros((0,2))),float)
            uv_count_ok=len(uv)==len(V)
            uv_finite=bool(np.isfinite(uv).all()) if len(uv) else False
            if not uv_count_ok: failures.append(f"{room}/{node}:uv_count")
            if not uv_finite: failures.append(f"{room}/{node}:uv_nonfinite")
            if not (uv_count_ok and uv_finite): continue

            Vw=(np.c_[V,np.ones(len(V))]@np.asarray(T,float).T)[:,:3]
            cyu=corr(Vw[:,1],uv[:,0]); cyv=corr(Vw[:,1],uv[:,1])
            yspan=float(np.ptp(Vw[:,1])); uspan=float(np.ptp(uv[:,0])); vspan=float(np.ptp(uv[:,1]))
            row={
                "room":room,"node":str(node),"texture":Path(str(tex_name)).stem.upper(),
                "png":png.name,"vertices":len(V),"triangles":len(geom.faces),
                "y_span":yspan,"u_span":uspan,"v_span":vspan,
                "corr_world_y_u":cyu,"corr_world_y_v":cyv,
                "embedded_texture_match":embedded_equal,"uv_count_ok":uv_count_ok,"uv_finite":uv_finite,
            }
            primitive_rows.append(row)

            is_strong=(yspan>=10.0 and vspan>=0.25 and cyv is not None and abs(cyv)>=0.75 and (cyu is None or abs(cyv)>=abs(cyu)))
            if is_strong:
                state="UPRIGHT" if cyv<0 else "VERTICALLY_INVERTED"
                key=(room,str(node),Path(str(tex_name)).stem.upper())
                accepted=(state=="UPRIGHT" or key in allowed)
                strong_vertical.append({**row,"orientation":state,"accepted":accepted})
                if not accepted:
                    failures.append(f"{room}/{node}:vertical_orientation:{state}")

    if len(used)!=int(contract["expected_used_texture_count"]):
        failures.append(f"used_texture_count:{len(used)}")
    if textured_primitive_count!=int(contract["expected_textured_primitive_count"]):
        failures.append(f"textured_primitive_count:{textured_primitive_count}")

    unused=sorted(p.name for p in pngs if p.stem.upper() not in used)
    if unused!=sorted(contract.get("expected_unused_textures",[])):
        failures.append("unused_texture_inventory_changed")

    # Explicit semantic orientation sentinels.
    bykey={(r["room"],r["node"]):r for r in primitive_rows}
    sentinels=[
        ("R1","doorcor2__1KEYHOLE","KEYHOLE#"),
        ("R8","tapestry2a__mesh","BAPMSG"),
    ]
    for room,node,tex in sentinels:
        r=bykey.get((room,node))
        if r is None:
            failures.append(f"{room}/{node}:sentinel_missing");continue
        if r["texture"]!=tex:
            failures.append(f"{room}/{node}:sentinel_texture:{r['texture']}")
        cv=r["corr_world_y_v"]
        if cv is None or cv>=-0.75:
            failures.append(f"{room}/{node}:semantic_upright_failed:{cv}")

    # Window wall textures: all must map image top to world top.
    window_textures={"BAPBACK1","BAPFRNT1","BAPLEFT1","BAPRGHT1"}
    window_rows=[r for r in strong_vertical if r["texture"] in window_textures]
    if not window_rows:
        failures.append("r8_window_orientation_rows_missing")
    for r in window_rows:
        if r["orientation"]!="UPRIGHT":
            failures.append(f"{r['room']}/{r['node']}:window_upside_down")

    result={
        "schema":"openazrael.kg001.texture_orientation_audit",
        "version":133,
        "status":"PASS" if not failures else "FAIL",
        "gltf_texture_origin":"upper_left",
        "classic_texture_count":len(pngs),
        "used_texture_count":len(used),
        "unused_texture_count":len(unused),
        "unused_textures":unused,
        "textured_primitive_count":textured_primitive_count,
        "strong_vertical_count":len(strong_vertical),
        "strong_vertical_upright_count":sum(r["orientation"]=="UPRIGHT" for r in strong_vertical),
        "strong_vertical_source_variant_count":sum(r["orientation"]!="UPRIGHT" and r["accepted"] for r in strong_vertical),
        "failures":failures,
        "warnings":warnings,
        "texture_inventory":texture_inventory,
        "strong_vertical":strong_vertical,
        "primitives":primitive_rows,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in (
        "status","classic_texture_count","used_texture_count","unused_texture_count",
        "textured_primitive_count","strong_vertical_count","strong_vertical_upright_count",
        "strong_vertical_source_variant_count","failures"
    )},indent=2))
    return 0 if not failures else 1

if __name__=="__main__":
    raise SystemExit(main())
