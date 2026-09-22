#!/usr/bin/env python3
"""KG-001 Issue #11 indexed source-palette color-key regression."""
from __future__ import annotations
from pathlib import Path
import json, sys, tempfile
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PIPE=ROOT/"tools/texture_pipeline"
sys.path.insert(0,str(PIPE))
from legacy_colorkey import render_indexed_colorkey
from export_xaf_glb_v8 import parse

EXPECTED_HASH_TEXTURES=[
"BAPBROK#.png","BAPFLOR#.png","BLOOD2#.png","BLOOD5#.png","BLOOD6#.png",
"BLOOS3#.png","BLOOS4#.png","BUBBLE#.png","KEYHOLE#.png","MINETON#.png"]
AUDIT=ROOT/"data/tests/kg001_colorkey_corpus_audit_v116.json"
errors=[]
def check(name,ok):
    if not ok: errors.append(name)

# Synthetic proof: a one-pixel near-magenta entry may be broadly magenta after
# quantization but it is NOT the source sentinel and must stay opaque.
source=np.array([
 [255,0,255,0],
 [120,40,80,0],
 [248,0,255,0],
 [255,8,255,0],
],dtype=np.uint8)
output=(source[:,:3]//4)*4
indices=np.array([[0,1],[2,1]],dtype=np.uint8)
keyed,meta=render_indexed_colorkey(indices,source,output,"MASK#.AZF")
plain,plain_meta=render_indexed_colorkey(indices,source,output,"MASK.AZF")
check("synthetic_key_index",meta["key_index"]==0)
check("synthetic_key_count",meta["key_pixels"]==1)
check("synthetic_near_magenta_stays_opaque",int(keyed[1,0,3])==255)
check("synthetic_exact_alpha",bool(np.array_equal(keyed[...,3],np.array([[0,255],[255,255]],dtype=np.uint8))))
check("non_hash_not_keyed",not plain_meta["applied"] and plain.shape==(2,2,3))
try:
    render_indexed_colorkey(np.array([[1,2]],dtype=np.uint8),source,output,"EMPTY#.AZF")
    check("zero_sentinel_fails_closed",False)
except ValueError: pass
try:
    render_indexed_colorkey(np.array([[0,3]],dtype=np.uint8),source,output,"AMBIG#.AZF")
    check("multi_sentinel_fails_closed",False)
except ValueError: pass

# Bound metadata audit from the actual 86-AZF ATDEMO corpus.
try:
    audit=json.loads(AUDIT.read_text(encoding="utf-8"))
    check("audit_status",audit.get("result",{}).get("status")=="PASS")
    check("audit_86",audit.get("azf_count")==86)
    check("audit_10_hash",audit.get("hash_texture_count")==10)
    check("audit_no_nonhash_sentinel",audit.get("result",{}).get("non_hash_used_sentinel_count")==0)
    rows=audit.get("entries",[])
    check("audit_names",sorted(x.get("texture","").replace(".AZF",".png") for x in rows)==sorted(EXPECTED_HASH_TEXTURES))
    check("audit_each_single_key",all(isinstance(x.get("selected_key_index"),int) and x.get("selected_key_pixels",0)>0 for x in rows))
    bloos4=next((x for x in rows if x.get("texture")=="BLOOS4#.AZF"),{})
    check("audit_bloos4_noise_control",bloos4.get("used_broad_magenta_indices")==[5,9] and bloos4.get("selected_key_index")==5)
except Exception as e:
    errors.append("audit_parse:"+str(e))

# Synthetic XAF -> GLB alpha preservation.
with tempfile.TemporaryDirectory(prefix="oa_colorkey_") as td:
    td=Path(td); texdir=td/"textures"; texdir.mkdir()
    Image.fromarray(keyed,"RGBA").save(texdir/"MASK#.png")
    xaf=td/"TEST.XAF"
    xaf.write_text('''material "CUTOUT" {\n texture "mask#.gif"\n colour { 1 1 1 1 }\n}\nobject "quad" {\n matrix { 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 }\n mesh {\n  vertices { 0 0 0  1 0 0  1 1 0  0 1 0 }\n  normals { 0 0 1  0 0 1  0 0 1  0 0 1 }\n  texture_coordinates { 0 0  1 0  1 1  0 1 }\n  faces {\n   4 0 0 1 1 2 2 3 3\n  }\n  material "CUTOUT"\n }\n}\n''',encoding="latin1")
    scene,objs,prims,mats,resolved,missing=parse(xaf,texdir)
    check("synthetic_export_no_missing",not missing)
    check("synthetic_export_mask",len(prims)==1 and prims[0].get("alpha_mode")=="MASK")
    mat=list(scene.geometry.values())[0].visual.material if scene.geometry else None
    check("synthetic_pbr_mask",mat is not None and getattr(mat,"alphaMode",None)=="MASK" and float(getattr(mat,"alphaCutoff",0))==0.5)

# Asset-backed validation after restore.
texture_dir=ROOT/"assets/textures/classic"; room_dir=ROOT/"assets/rooms"
restore_evidence=ROOT/".tmp/kg001/legacy_colorkey_restore.json"
asset_backed=texture_dir.is_dir() and any(texture_dir.glob("*.png"))
asset_rows=[]
if all((room_dir/n).is_file() for n in ("R1.glb","R7.glb","R8.glb")):
    check("asset_texture_corpus_present",asset_backed)
if asset_backed:
    pngs=sorted(texture_dir.glob("*.png"))
    check("asset_texture_count_86",len(pngs)==86)
    check("asset_hash_set",sorted(p.name for p in pngs if "#" in p.stem)==sorted(EXPECTED_HASH_TEXTURES))
    check("asset_restore_evidence",restore_evidence.is_file())
    restored=json.loads(restore_evidence.read_text(encoding="utf-8")) if restore_evidence.is_file() else {}
    by_name={str(x.get("texture")):x for x in restored.get("textures",[])}
    check("asset_restore_10",len(by_name)==10)
    for name in EXPECTED_HASH_TEXTURES:
        row=by_name.get(name,{})
        check("asset_row_"+name,bool(row))
        if row:
            check("asset_rule_"+name,row.get("rule")=="indexed_hash_source_sentinel_v2")
            check("asset_single_sentinel_"+name,row.get("used_sentinel_indices")==[row.get("key_index")])
            check("asset_source_sentinel_"+name,(row.get("key_source_rgba") or [0,99,0])[:3][0]==255 and (row.get("key_source_rgba") or [0,99,0])[:3][2]==255 and (row.get("key_source_rgba") or [0,99,0])[1]<=8)
        path=texture_dir/name
        check("asset_exists_"+name,path.is_file())
        if path.is_file():
            with Image.open(path) as im:
                im.load(); rgba=np.array(im.convert("RGBA"),dtype=np.uint8); mode=im.mode
            alpha=rgba[...,3]; transparent=int((alpha==0).sum()); opaque=int((alpha==255).sum())
            check("asset_rgba_"+name,mode=="RGBA")
            check("asset_binary_alpha_"+name,bool(np.all((alpha==0)|(alpha==255))))
            check("asset_has_both_alpha_states_"+name,transparent>0 and opaque>0)
            if row: check("asset_alpha_count_"+name,transparent==int(row.get("transparent_pixels",-1)))
            asset_rows.append({"texture":name,"key_index":row.get("key_index"),"transparent_pixels":transparent})
    manifest=ROOT/"data/R1.textured.v44.manifest.json"
    check("asset_r1_manifest",manifest.is_file())
    if manifest.is_file():
        r1=json.loads(manifest.read_text(encoding="utf-8"))
        by_obj={str(x.get("object")):x for x in r1.get("primitives",[])}
        keys=[x for x in r1.get("primitives",[]) if str(x.get("resolved_png"))=="KEYHOLE#.png"]
        tong=by_obj.get("TONG6")
        check("asset_r1_keyhole_mask",bool(keys) and all(x.get("alpha_mode")=="MASK" for x in keys))
        check("asset_r1_tongs_mask",tong is not None and tong.get("resolved_png")=="MINETON#.png" and tong.get("alpha_mode")=="MASK")
result={"schema":"openazrael.kg001.texture_colorkey_validation","version":116,"issue":"#11",
"status":"PASS" if not errors else "FAIL","source_safe_checks":"PASS" if not errors else "FAIL",
"selection_space":"ORIGINAL_INDEXED_AZF","selection_policy":"exactly one used source-palette sentinel R==255,B==255,G<=8 per # texture",
"corpus_audit":"data/tests/kg001_colorkey_corpus_audit_v116.json","asset_backed":asset_backed,"asset_rows":asset_rows,"failed":errors,
"boundary":"Indexed binary legacy color-key compatibility only; complete original renderer transparency/blending semantics remain HOLD."}
print("OPENAZRAEL_KG001_TEXTURE_COLORKEY_V116 "+json.dumps(result,separators=(",",":")))
if errors:
    print("OpenAzrael KG-001 indexed color-key validation: FAIL")
    for e in errors: print(" -",e)
    sys.exit(1)
print("OpenAzrael KG-001 indexed color-key validation: PASS")
print(" actual ATDEMO metadata audit: PASS")
print(" asset-backed:",asset_backed)
