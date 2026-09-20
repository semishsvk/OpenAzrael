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

from legacy_colorkey import apply_legacy_colorkey, image_alpha_mode, legacy_magenta_mask
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

# Pure source-safe mask semantics.
rgb=np.array([
    [[252,0,252],[120,40,80]],
    [[248,12,255],[248,16,248]],
],dtype=np.uint8)
keyed,meta=apply_legacy_colorkey(rgb,"MASK#.AZF")
plain,plain_meta=apply_legacy_colorkey(rgb,"MASK.AZF")
no_magenta,no_magenta_meta=apply_legacy_colorkey(
    np.full((2,2,3),[100,20,100],dtype=np.uint8),"EMPTY#.AZF"
)
check("synthetic_candidate",meta["candidate"])
check("synthetic_applied",meta["applied"])
check("synthetic_exact_key_count",meta["magenta_pixels"]==2)
check("synthetic_rgba",keyed.shape==(2,2,4))
check("synthetic_alpha_zero",int((keyed[...,3]==0).sum())==2)
check("synthetic_alpha_opaque",int((keyed[...,3]==255).sum())==2)
check("synthetic_transparent_rgb_zero",bool(np.all(keyed[keyed[...,3]==0,:3]==0)))
check("non_hash_not_keyed",not plain_meta["applied"] and plain.shape==(2,2,3))
check("hash_without_magenta_not_keyed",not no_magenta_meta["applied"] and no_magenta.shape==(2,2,3))

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

# Optional asset-backed checks run automatically after local Candidate restore.
texture_dir=ROOT/"assets/textures/classic"
asset_backed=False
asset_rows=[]
if texture_dir.is_dir() and any(texture_dir.glob("*.png")):
    asset_backed=True
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
        # '#' is the candidate namespace; the mask is applied only when
        # quantized magenta is actually observed. Known visible regressions
        # KEYHOLE#/MINETON# must therefore be RGBA, while other '#' assets may
        # remain RGB if they contain no key pixels.
        if mode=="RGBA":
            check("asset_has_transparency_"+name,transparent>0)
            check("asset_has_opaque_pixels_"+name,opaque>0)
        check("asset_no_magenta_residue_"+name,residual==0)
        if name in ("KEYHOLE#.png","MINETON#.png"):
            check("asset_known_regression_rgba_"+name,mode=="RGBA")
            check("asset_known_regression_transparency_"+name,transparent>0)
        asset_rows.append({
            "texture":name,
            "mode":mode,
            "transparent_pixels":transparent,
            "opaque_pixels":opaque,
            "residual_magenta_pixels":residual,
        })

    manifest=ROOT/"data/R1.textured.v44.manifest.json"
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

result={
    "schema":"openazrael.kg001.texture_colorkey_validation",
    "version":116,
    "issue":"#11",
    "status":"PASS" if not errors else "FAIL",
    "source_safe_checks":"FAIL" if any(
        e.startswith(("synthetic_","non_hash_","hash_without_")) for e in errors
    ) else "PASS",
    "expected_hash_texture_count":len(EXPECTED_HASH_TEXTURES),
    "expected_hash_textures":EXPECTED_HASH_TEXTURES,
    "asset_backed":asset_backed,
    "asset_rows":asset_rows,
    "failed":errors,
    "boundary":"Conservative # + quantized-magenta binary color-key only; complete original renderer transparency semantics remain HOLD.",
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
