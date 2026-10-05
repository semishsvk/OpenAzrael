#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"data/ui/legacy_menu_manifest_v144.json"
OUT_ROOT=ROOT/"assets/ui/legacy_menu"
RECEIPT=ROOT/".tmp/menu_lab/menu_restore_v144.json"

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def main()->int:
    ap=argparse.ArgumentParser(description="Restore source-exact ATDEMO menu/HUD PCX art.")
    ap.add_argument("demo_dir",type=Path)
    args=ap.parse_args()
    src=args.demo_dir.resolve()
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows=[]
    for spec in manifest["assets"]:
        source=src/spec["file"]
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.stat().st_size!=int(spec["bytes"]) or sha256(source)!=spec["sha256"]:
            raise ValueError(f"{spec['file']}: source fingerprint mismatch")
        with Image.open(source) as indexed:
            indexed.load()
            if indexed.mode!="P":
                raise ValueError(f"{spec['file']}: expected indexed PCX")
            if indexed.size!=(int(spec["width"]),int(spec["height"])):
                raise ValueError(f"{spec['file']}: source dimensions mismatch")
            destination=OUT_ROOT/(Path(spec["file"]).stem+".png")
            destination.parent.mkdir(parents=True,exist_ok=True)
            category=str(spec["category"])
            if category == "hud_frame":
                source_palette = json.loads((ROOT / "data/ui/legacy_health_hud_v217.json").read_text())["palette_rgb6_expanded"]
                assert len(source_palette) == 256 and all(len(rgb) == 3 for rgb in source_palette)
                indexed.putpalette([int(value) for rgb in source_palette for value in rgb])
            use_index0_alpha=category in {"hud_frame","save_preview","replay_animation","font_strip"}
            if use_index0_alpha:
                rgba=indexed.convert("RGBA")
                source_indices=list(indexed.getdata())
                alpha=Image.new("L",indexed.size,255)
                alpha.putdata([0 if int(v)==0 else 255 for v in source_indices])
                rgba.putalpha(alpha)
                rgba.save(destination,format="PNG",optimize=False)
                alpha_policy="PALETTE_INDEX_0_TRANSPARENT_SOURCE_OVERLAY"
            else:
                indexed.convert("RGB").save(destination,format="PNG",optimize=False)
                alpha_policy="OPAQUE_SOURCE_RGB"
            rows.append({
                "source":spec["file"],
                "category":spec["category"],
                "source_sha256":spec["sha256"],
                "runtime":str(destination.relative_to(ROOT)).replace("\\","/"),
                "runtime_png_sha256":sha256(destination),
                "width":indexed.width,
                "height":indexed.height,
                "alpha_policy":alpha_policy,
                "palette_policy":"SOURCE_RUNTIME_RGB6_EXPANDED" if category == "hud_frame" else "SOURCE_PCX_RGB8",
            })
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    receipt={"schema":"openazrael.menu_lab.restore","version":144,"status":"PASS","asset_count":len(rows),"files":rows}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","asset_count":len(rows),"output":str(OUT_ROOT.relative_to(ROOT))},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
