#!/usr/bin/env python3
from pathlib import Path
import json, sys
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/"data/classic_colorkey_audit_v1.json"
DECODER=ROOT/"tools/texture_pipeline/azf_decode_v14.py"
EXPORTER=ROOT/"tools/texture_pipeline/export_xaf_glb_v8.py"
MIGRATOR=ROOT/"tools/texture_pipeline/apply_colorkey_alpha_v1.py"

EXPECTED={
    "BAPBROK#.png","BAPFLOR#.png","BLOOD2#.png","BLOOD5#.png","BLOOD6#.png",
    "BLOOS3#.png","BLOOS4#.png","BUBBLE#.png","KEYHOLE#.png","MINETON#.png"
}

def main():
    errors=[]
    audit=json.loads(AUDIT.read_text(encoding="utf-8"))
    decoder=DECODER.read_text(encoding="utf-8")
    exporter=EXPORTER.read_text(encoding="utf-8")
    migrator=MIGRATOR.read_text(encoding="utf-8")

    audited={x["file"] for x in audit.get("keyed_textures",[])}
    if audit.get("classic_texture_count") != 86:
        errors.append("audit texture count drift")
    if audit.get("keyed_texture_count") != 10 or audit.get("hash_suffix_texture_count") != 10:
        errors.append("audit keyed count drift")
    if audit.get("non_hash_magenta_candidate_count") != 0:
        errors.append("non-# magenta candidate regression")
    if audited != EXPECTED:
        errors.append("keyed texture set drift")

    source_checks={
        "decoder_index_space": "detect_colorkey_index" in decoder and "np.bincount" in decoder,
        "decoder_hash_gate": "if '#' not in Path(azf_path).stem" in decoder,
        "decoder_binary_alpha": "alpha[key_index]=0" in decoder and "Image.fromarray(rgba[idx],'RGBA')" in decoder,
        "decoder_no_silent_hash_miss": "legacy # texture has no used magenta colour-key palette index" in decoder,
        "exporter_rgba": "source_image.convert('RGBA')" in exporter,
        "exporter_mask": "alphaMode='MASK'" in exporter and "alphaCutoff=0.5" in exporter,
        "manifest_alpha": "'alpha_mode':material_alpha_mode.get(mn,'OPAQUE')" in exporter,
        "migration_exact_key": "np.all(rgb==key,axis=2)" in migrator and "keyed!=spec[\"keyed_pixels\"]" in migrator,
    }
    for name,ok in source_checks.items():
        if not ok:
            errors.append("source contract: "+name)

    asset_status="NOT_PRESENT_SOURCE_ONLY"
    texdir=ROOT/"assets/textures/classic"
    pngs=sorted(texdir.glob("*.png")) if texdir.is_dir() else []
    if pngs:
        asset_status="PASS"
        if len(pngs) != 86:
            errors.append(f"asset corpus count {len(pngs)} != 86")
            asset_status="FAIL"
        actual_hash={p.name for p in pngs if "#" in p.stem}
        if actual_hash != EXPECTED:
            errors.append("asset # texture set drift")
            asset_status="FAIL"
        for p in pngs:
            with Image.open(p) as im:
                bands=im.getbands()
                if p.name in EXPECTED:
                    if im.mode != "RGBA" or "A" not in bands:
                        errors.append(f"{p.name}: expected RGBA")
                        asset_status="FAIL"
                        continue
                    alpha=np.asarray(im.getchannel("A"))
                    unique=set(int(x) for x in np.unique(alpha))
                    if not unique.issubset({0,255}) or 0 not in unique or 255 not in unique:
                        errors.append(f"{p.name}: alpha is not a nontrivial binary mask")
                        asset_status="FAIL"
                elif "A" in bands:
                    alpha=np.asarray(im.getchannel("A"))
                    if int(alpha.min()) != 255:
                        errors.append(f"{p.name}: unexpected transparency on non-# texture")
                        asset_status="FAIL"

    out={
        "schema":"openazrael.classic_colorkey_contract",
        "version":1,
        "status":"PASS" if not errors else "FAIL",
        "source_contract":"PASS" if all(source_checks.values()) and audited==EXPECTED else "FAIL",
        "asset_status":asset_status,
        "expected_keyed":sorted(EXPECTED),
        "errors":errors
    }
    print(json.dumps(out,indent=2))
    sys.exit(0 if not errors else 1)

if __name__=="__main__":
    main()
