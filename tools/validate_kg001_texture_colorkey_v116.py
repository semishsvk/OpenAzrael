#!/usr/bin/env python3
"""KG-001 Issue #11 legacy color-key source + optional asset regression."""
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
    apply_legacy_colorkey,
    apply_legacy_indexed_colorkey,
    bleed_hidden_rgb,
    image_alpha_mode,
    legacy_magenta_mask,
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

# Pure source-safe indexed-mask semantics.
palette=np.array([
    [120,40,80,0],
    [255,0,255,0],
    [248,16,248,0],
],dtype=np.uint8)
indices=np.array([
    [1,0],
    [1,2],
],dtype=np.uint8)
keyed,index_meta=apply_legacy_indexed_colorkey(
    palette,
    indices,
    "MASK#.AZF",
)
check("indexed_candidate",index_meta["candidate"])
check("indexed_applied",index_meta["applied"])
check("indexed_key_index",index_meta["key_index"]==1)
check("indexed_single_key_candidate",index_meta["used_magenta_key_indices"]==[1])
check("indexed_key_pixel_count",index_meta["key_pixels"]==2)
check("indexed_rgba",keyed.shape==(2,2,4))
check("indexed_alpha_zero",int((keyed[...,3]==0).sum())==2)
check("indexed_alpha_opaque",int((keyed[...,3]==255).sum())==2)
check("indexed_transparent_rgb_zero",bool(np.all(keyed[keyed[...,3]==0,:3]==0)))

ambiguous_palette=palette.copy()
ambiguous_palette[2,:3]=[248,12,248]
ambiguous_failed_closed=False
try:
    apply_legacy_indexed_colorkey(
        ambiguous_palette,
        np.array([[1,2]],dtype=np.uint8),
        "AMBIG#.AZF",
    )
except ValueError:
    ambiguous_failed_closed=True
check("indexed_ambiguous_fails_closed",ambiguous_failed_closed)

# RGB fallback remains available for non-indexed/synthetic callers only.
rgb=np.array([
    [[252,0,252],[120,40,80]],
    [[248,12,255],[248,16,248]],
],dtype=np.uint8)
rgb_keyed,meta=apply_legacy_colorkey(rgb,"MASK#.AZF")
plain,plain_meta=apply_legacy_colorkey(rgb,"MASK.AZF")
no_magenta,no_magenta_meta=apply_legacy_colorkey(
    np.full((2,2,3),[100,20,100],dtype=np.uint8),"EMPTY#.AZF"
)
check("synthetic_fallback_applied",meta["applied"])
check("non_hash_not_keyed",not plain_meta["applied"] and plain.shape==(2,2,3))
check("hash_without_magenta_not_keyed",not no_magenta_meta["applied"] and no_magenta.shape==(2,2,3))

# Runtime-only hidden RGB bleed must not alter binary alpha.
bleed_input=np.zeros((3,3,4),dtype=np.uint8)
bleed_input[1,1]=[200,100,50,255]
bled=bleed_hidden_rgb(bleed_input)
check("bleed_alpha_preserved",np.array_equal(bled[...,3],bleed_input[...,3]))
check("bleed_opaque_rgb_preserved",np.array_equal(bled[1,1,:3],[200,100,50]))
check("bleed_transparent_rgb_filled",bool(np.all(bled[bled[...,3]==0,:3]!=0)))

# Synthetic XAF -> GLB material path: alpha must survive and become MASK.
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
    if material is not None and getattr(material,"baseColorTexture",None) is not None:
        runtime_rgba=np.array(material.baseColorTexture.convert("RGBA"),dtype=np.uint8)
        check("synthetic_export_alpha_preserved",int((runtime_rgba[...,3]==0).sum())==2)
        check(
            "synthetic_export_hidden_rgb_bleed",
            bool(np.all(runtime_rgba[runtime_rgba[...,3]==0,:3]!=0)),
        )

# Optional asset-backed checks run automatically after local Candidate restore.
texture_dir=ROOT/"assets/textures/classic"
room_dir=ROOT/"assets/rooms"
restored_rooms_present=any((room_dir/name).is_file() for name in ("R1.glb","R7.glb","R8.glb"))
asset_backed=texture_dir.is_dir() and any(texture_dir.glob("*.png"))
asset_rows=[]
if restored_rooms_present:
    check("asset_texture_corpus_present_with_rooms",asset_backed)
if asset_backed:
    restore_evidence=ROOT/".tmp/kg001/legacy_colorkey_restore.json"
    if restore_evidence.is_file():
        restore_rows=json.loads(
            restore_evidence.read_text(encoding="utf-8")
        ).get("textures",[])
        by_restore={str(row.get("texture")):row for row in restore_rows}
        check("asset_restore_indexed_rows_10",len(by_restore)==len(EXPECTED_HASH_TEXTURES))
        for name in EXPECTED_HASH_TEXTURES:
            row=by_restore.get(name)
            check("asset_restore_index_row_"+name,row is not None)
            if row is not None:
                key_index=row.get("key_index")
                candidates=row.get("key_candidates",[])
                check("asset_restore_index_applied_"+name,row.get("applied") is True)
                check("asset_restore_index_exactly_one_"+name,isinstance(key_index,int) and candidates==[key_index])
                check("asset_restore_index_detection_"+name,row.get("detection")=="USED_INDEXED_PALETTE_ENTRY")
    pngs=sorted(texture_dir.glob("*.png"))
    check("asset_texture_count_86",len(pngs)==86)
    actual_hash_names=sorted(p.name for p in pngs if "#" in p.stem)
    check("asset_hash_texture_set",actual_hash_names==sorted(EXPECTED_HASH_TEXTURES))
    for name in EXPECTED_HASH_TEXTURES:
        path=texture_dir/name
        check("asset_exists_"+name,path.is_file())
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
        # Independent Candidate-2 audit found exactly one used indexed
        # key entry for each of the ten '#' demo assets.
        check("asset_rgba_"+name,mode=="RGBA")
        check("asset_has_transparency_"+name,transparent>0)
        check("asset_has_opaque_pixels_"+name,opaque>0)
        check("asset_no_magenta_residue_"+name,residual==0)
        asset_rows.append({
            "texture":name,
            "mode":mode,
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
            check("asset_r1_tongs_bleed_safe",tong.get("alpha_edge_bleed_safe") is True)

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
        e.startswith(("indexed_","synthetic_","bleed_","non_hash_","hash_without_"))
        for e in errors
    ) else "PASS",
    "expected_hash_texture_count":len(EXPECTED_HASH_TEXTURES),
    "expected_hash_textures":EXPECTED_HASH_TEXTURES,
    "asset_backed":asset_backed,
    "asset_rows":asset_rows,
    "failed":errors,
    "boundary":"Binary color-key is derived from exactly one used indexed AZF palette entry for '#' assets; GLB MASK materials use hidden-RGB edge bleed without changing alpha. Complete original renderer transparency/blending semantics remain HOLD.",
}
print("OPENAZRAEL_KG001_TEXTURE_COLORKEY_V116 "+json.dumps(result,separators=(",",":")))
if errors:
    print("OpenAzrael KG-001 legacy color-key validation: FAIL")
    for e in errors:
        print(" -",e)
    sys.exit(1)
print("OpenAzrael KG-001 legacy color-key validation: PASS")
print(" expected keyed class:",len(EXPECTED_HASH_TEXTURES))
print(" asset-backed:",asset_backed)
