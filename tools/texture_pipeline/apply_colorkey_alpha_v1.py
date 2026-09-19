#!/usr/bin/env python3
from pathlib import Path
import argparse, json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"data/classic_colorkey_audit_v1.json"


def apply_one(src: Path, dst: Path, key_rgb):
    with Image.open(src) as im:
        rgb=np.asarray(im.convert("RGB"),dtype=np.uint8)
    key=np.asarray(key_rgb,dtype=np.uint8)
    mask=np.all(rgb==key,axis=2)
    if not mask.any():
        raise ValueError(f"{src.name}: audited key colour {tuple(key_rgb)} not found")
    alpha=np.full(mask.shape,255,dtype=np.uint8)
    alpha[mask]=0
    rgba=np.dstack([rgb,alpha])
    dst.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(rgba,"RGBA").save(dst)
    return int(mask.sum())


def main():
    ap=argparse.ArgumentParser(description="Apply the audited OpenAzrael legacy color-key masks to an existing decoded Classic PNG corpus.")
    ap.add_argument("texture_dir",type=Path)
    ap.add_argument("--output-dir",type=Path)
    ap.add_argument("--in-place",action="store_true")
    a=ap.parse_args()
    if a.in_place == (a.output_dir is not None):
        raise SystemExit("choose exactly one of --in-place or --output-dir")

    audit=json.loads(AUDIT.read_text(encoding="utf-8"))
    expected={x["file"]:x for x in audit["keyed_textures"]}
    pngs={p.name:p for p in a.texture_dir.glob("*.png")}
    if len(pngs)!=audit["classic_texture_count"]:
        raise SystemExit(f"expected {audit['classic_texture_count']} Classic PNGs, got {len(pngs)}")
    if {n for n in pngs if "#" in Path(n).stem} != set(expected):
        raise SystemExit("the # suffixed texture set does not match the audited demo corpus")

    changed=[]
    for name,spec in sorted(expected.items()):
        src=pngs[name]
        dst=src if a.in_place else a.output_dir/name
        keyed=apply_one(src,dst,spec["key_rgb"])
        if keyed!=spec["keyed_pixels"]:
            raise SystemExit(f"{name}: keyed pixel count {keyed} != audited {spec['keyed_pixels']}")
        changed.append({"file":name,"key_rgb":spec["key_rgb"],"keyed_pixels":keyed})

    if not a.in_place:
        for name,src in sorted(pngs.items()):
            if name in expected:
                continue
            dst=a.output_dir/name
            dst.write_bytes(src.read_bytes())

    print(json.dumps({"status":"PASS","changed":changed,"count":len(changed)},indent=2))


if __name__=="__main__":
    main()
