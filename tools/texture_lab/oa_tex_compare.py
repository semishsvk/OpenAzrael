#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import ROOT


def make_sheet(texture_id: str, source: Path, variants: list[tuple[str, Path]], out: Path, cell: int) -> None:
    items: list[tuple[str, Image.Image]] = []
    with Image.open(source) as im:
        items.append(("Classic", im.convert("RGBA").copy()))
    for label, path in variants:
        if path.is_file():
            with Image.open(path) as im:
                items.append((label, im.convert("RGBA").copy()))

    label_h = 28
    sheet = Image.new("RGBA", (cell * len(items), cell + label_h), (0, 0, 0, 255))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, im) in enumerate(items):
        preview = im.resize((cell, cell), getattr(Image, "Resampling", Image).NEAREST)
        x = index * cell
        sheet.alpha_composite(preview, (x, label_h))
        draw.text((x + 4, 7), label, fill=(255, 255, 255, 255), font=font)

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out, format="PNG", optimize=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create repository-ignored visual comparison sheets.")
    parser.add_argument("texture_id")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--enhanced-dir", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument("--ai-restored-dir", type=Path, default=ROOT / "assets/textures/ai_restored")
    parser.add_argument("--ai-recreated-dir", type=Path, default=ROOT / "assets/textures/ai_recreated")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "assets/textures/comparisons")
    parser.add_argument("--cell", type=int, default=320)
    args = parser.parse_args()

    source = args.source_dir / f"{args.texture_id}.png"
    if not source.is_file():
        parser.error(f"source not found: {source}")

    variants = [
        ("Nearest 4x", args.enhanced_dir / args.texture_id / "nearest_x4.png"),
        ("Bicubic 4x", args.enhanced_dir / args.texture_id / "bicubic_x4.png"),
        ("Lanczos 4x", args.enhanced_dir / args.texture_id / "lanczos_x4.png"),
        ("xBRZ 4x", args.enhanced_dir / args.texture_id / "xbrz_x4.png"),
        ("AI Restored", args.ai_restored_dir / args.texture_id / "realesrgan_x4.png"),
        ("AI Recreated", args.ai_recreated_dir / args.texture_id / "selected.png"),
    ]
    out = args.out_dir / f"{args.texture_id}_comparison.png"
    make_sheet(args.texture_id, source, variants, out, args.cell)
    print(f"PASS comparison={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
