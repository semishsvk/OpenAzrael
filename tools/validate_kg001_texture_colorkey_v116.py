#!/usr/bin/env python3
"""KG-001 Issue #11 indexed legacy color-key source + optional asset regression."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PIPE=ROOT/"tools/texture_pipeline"
sys.path.insert(0,str(PIPE))

from legacy_colorkey import (
    analyze_indexed_colorkey,
    legacy_magenta_mask,
    render_indexed_colorkey,
)
from export_xaf_glb_v8 import parse

EXPECTED_HASH_TEXTURES = [
    "BAPBROK#.png",
    "BAPFLOR#.png",
    "BLOOD2#.png",
    "BLOOD5#.png",
    "BLOOD6#.png",
    "BLOOS3#.png",
    "BLOOS4#.png",
    "BUBBLE#.png",
    "KEYHOLE#.png",
    "MINETON#.png",
]

errors=[]

def check(name, condition):
    if not condition:
        errors.append(name)

# Source-safe indexed semantics: only one exact used palette index may become
# transparent. A nearby non-key colour and an unused magenta entry stay safe.
palette=np.array([
    [252,0,252],   # index 0: exact used key
    [120,40,80],   # index 1: ordinary opaque colour
    [244,0,244],   # index 2: visually close but outside recovered threshold
    [248,4,248],   # index 3: qualifying magenta but unused in the valid sample
],dtype=np.uint8)
indices=np.array([[0,1],[2,1]],dtype=np.uint8)
keyed,meta=render_indexed_colorkey(indices,palette,"MASK#.AZF")
plain,plain_meta=render_indexed_colorkey(indices,palette,"MASK.AZF")

check("synthetic_candidate",meta["candidate"])
check("synthetic_applied",meta["applied"])
check("synthetic_exact_key_index",meta["key_index"]==0)
check("synthetic_exact_key_count",meta["key_pixels"]==1)
check("synthetic_single_used_magenta_index",meta["used_magenta_indices"]==[0])
check("synthetic_rgba",keyed.shape==(2,2,4))
check("synthetic_alpha_exact_index",bool(np.array_equal(keyed[...,3],np.array([[0,255],[255,255]],dtype=np.uint8))))
check("synthetic_nonkey_magenta_like_opaque",int(keyed[1,0,3])==255)
check("synthetic_transparent_rgb_zero",bool(np.all(keyed[0,0,:3]==0)))
check("non_hash_not_keyed",not plain_meta["applied"] and plain.shape==(2,2,3))

# Fail closed if a '#' texture has zero or multiple used qualifying indices.
try:
    render_indexed_colorkey(np.array([[1,2]],dtype=np.uint8),palette,"EMPTY#.AZF")
    check("hash_without_used_key_fails_closed",False)
except ValueError:
    pass
try:
    render_indexed_colorkey(np.array([[0,3]],dtype=np.uint8),palette,"AMBIG#.AZF")
    check("ambiguous_used_key_fails_closed",False)
except ValueError:
    pass

# Synthetic XAF -> GLB material path: indexed alpha must survive as MASK.
with tempfile.TemporaryDirectory(prefix="oa_colorkey_") as td:
    td=Path(td)
    texdir=td/"textures"; texdir.mkdir()
    Image.fromarray(keyed,"RGBA").save(texdir/"MASK#.png")
    xaf=td/"TEST.XAF"
    xaf.write_text(
        '''material "CUTOUT" {
 texture "mask#.gif"
 colour { 1 1 1 1 }
}
object "quad" {
 matrix { 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 }
 mesh {
  vertices { 0 0 0  1 0 0  1 1 0  0 1 0 }
  normals { 0 0 1  0 0 1  0 0 1  0 0 1 }
  texture_coordinates { 0 0  1 0  1 1  0 1 }
  faces {
   4 0 0 1 1 2 2 3 3
  }
  material "CUTOUT"
 }
}
''',
        encoding="latin1",
    )
    scene,objs,prims,mats,resolved,missing=parse(xaf,texdir)
    check("synthetic_export_no_missing",not missing)
    check("synthetic_export_one_primitive",len(prims)==1)
    if prims:
        check("synthetic_export_mask_metadata",prims[0].get("alpha_mode")=="MASK")
        check("synthetic_export_colorkey_metadata",prims[0].get("legacy_colorkey") is True)
    material=list(scene.geometry.values())[0].visual.material if scene.geometry else None
    check("synthetic_export_pbr_material",material is not None and material.__class__.__name__=="PBRMaterial")
    check("synthetic_export_alpha_mode",getattr(material,"alphaMode",None)=="MASK")
    check("synthetic_export_alpha_cutoff",float(getattr(material,"alphaCutoff",0.0))==0.5)

# Asset-backed checks run automatically after local Candidate restore.
texture_dir=ROOT/"assets/textures/classic"
room_dir=ROOT/"assets/rooms"
restore_evidence=ROOT/".tmp/kg001/legacy_colorkey_restore.json"
restored_rooms_present=all((room_dir/name).is_file() for name in ("R1.glb","R7.glb","R8.glb"))
asset_backed=texture_dir.is_dir() and any(texture_dir.glob("*.png"))
asset_rows=[]
if restored_rooms_present:
    check("asset_texture_corpus_present_with_rooms",asset_backed)
if asset_backed:
    pngs=sorted(texture_dir.glob("*.png"))
    check("asset_texture_count_86",len(pngs)==86)
    actual_hash_names=sorted(p.name for p in pngs if "#" in p.stem)
    check("asset_hash_texture_set",actual_hash_names==sorted(EXPECTED_HASH_TEXTURES))

    restore_rows={}
    check("asset_restore_evidence_present",restore_evidence.is_file())
    if restore_evidence.is_file():
        restored=json.loads(restore_evidence.read_text(encoding="utf-8"))
        restore_rows={str(x.get("texture")):x for x in restored.get("textures",[])}
        check("asset_restore_exact_hash_count",len(restore_rows)==len(EXPECTED_HASH_TEXTURES))

    for name in EXPECTED_HASH_TEXTURES:
        path=texture_dir/name
        check("asset_exists_"+name,path.is_file())
        row=restore_rows.get(name,{})
        check("asset_restore_row_"+name,bool(row))
        if row:
            check("asset_single_index_"+name,isinstance(row.get("key_index"),int))
            check("asset_single_used_magenta_"+name,len(row.get("used_magenta_indices",[]))==1)
            check("asset_index_identity_"+name,row.get("used_magenta_indices")==[row.get("key_index")])
            check("asset_rule_"+name,row.get("rule")=="indexed_hash_exact_single_used_magenta_v1")
        if not path.is_file():
            continue
        with Image.open(path) as im:
            im.load()
            rgba=np.array(im.convert("RGBA"),dtype=np.uint8)
            alpha=rgba[...,3]
            transparent=int((alpha==0).sum())
            opaque=int((alpha==255).sum())
            residual=int(legacy_magenta_mask(rgba[...,:3]).sum())
            mode=im.mode
        check("asset_rgba_"+name,mode=="RGBA")
        check("asset_has_transparency_"+name,transparent>0)
        check("asset_has_opaque_pixels_"+name,opaque>0)
        check("asset_no_opaque_key_magenta_"+name,residual==0)
        if row:
            check("asset_transparent_count_matches_index_"+name,transparent==int(row.get("transparent_pixels",-1)))
        asset_rows.append({
            "texture":name,
            "mode":mode,
            "key_index":row.get("key_index"),
            "transparent_pixels":transparent,
            "opaque_pixels":opaque,
            "residual_magenta_pixels":residual,
        })

    manifest=ROOT/"data/R1.textured.v44.manifest.json"
    check("asset_r1_manifest_present",manifest.is_file())
    if manifest.is_file():
        r1=json.loads(manifest.read_text(encoding="utf-8"))
        by_object={str(x.get("object")):x for x in r1.get("primitives",[])}
        key_rows=[x for x in r1.get("primitives",[]) if str(x.get("resolved_png"))=="KEYHOLE#.png"]
        tong=by_object.get("TONG6")
        check("asset_r1_keyhole_mask",bool(key_rows) and all(x.get("alpha_mode")=="MASK" for x in key_rows))
        check("asset_r1_tongs_present",tong is not None)
        if tong is not None:
            check("asset_r1_tongs_texture",tong.get("resolved_png")=="MINETON#.png")
            check("asset_r1_tongs_mask",tong.get("alpha_mode")=="MASK" and tong.get("legacy_colorkey") is True)

    r1_glb=room_dir/"R1.glb"
    check("asset_r1_glb_present",r1_glb.is_file())
    if r1_glb.is_file():
        loaded=__import__("trimesh").load(r1_glb,force="scene")
        materials={}
        for geom in loaded.geometry.values():
            mat=getattr(getattr(geom,"visual",None),"material",None)
            if mat is not None:
                materials.setdefault(str(getattr(mat,"name","")),[]).append(mat)
        for material_name in ("1KEYHOLE","1TONGS"):
            rows=materials.get(material_name,[])
            check("asset_glb_material_"+material_name,bool(rows))
            if rows:
                check(
                    "asset_glb_mask_"+material_name,
                    all(getattr(mat,"alphaMode",None)=="MASK" for mat in rows),
                )

result={
    "schema":"openazrael.kg001.texture_colorkey_validation",
    "version":116,
    "issue":"#11",
    "status":"PASS" if not errors else "FAIL",
    "source_safe_checks":"FAIL" if any(
        e.startswith(("synthetic_","non_hash_","hash_without_","ambiguous_")) for e in errors
    ) else "PASS",
    "selection_space":"ORIGINAL_INDEXED_AZF",
    "selection_policy":"exactly one used qualifying palette index per # texture",
    "expected_hash_texture_count":len(EXPECTED_HASH_TEXTURES),
    "expected_hash_textures":EXPECTED_HASH_TEXTURES,
    "asset_backed":asset_backed,
    "asset_rows":asset_rows,
    "failed":errors,
    "boundary":"Indexed binary legacy color-key compatibility only; complete original renderer transparency/blending semantics remain HOLD.",
}
print("OPENAZRAEL_KG001_TEXTURE_COLORKEY_V116 "+json.dumps(result,separators=(",",":")))
if errors:
    print("OpenAzrael KG-001 indexed color-key validation: FAIL")
    for e in errors:
        print(" -",e)
    sys.exit(1)
print("OpenAzrael KG-001 indexed color-key validation: PASS")
print(" expected keyed class:",len(EXPECTED_HASH_TEXTURES))
print(" asset-backed:",asset_backed)
