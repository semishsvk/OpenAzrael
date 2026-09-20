#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from common import ROOT


def tile_preview(source: Path, output: Path, repeat_x: int = 3, repeat_y: int = 3) -> None:
    with Image.open(source) as im:
        src = im.convert("RGBA")
    canvas = Image.new("RGBA", (src.width * repeat_x, src.height * repeat_y))
    for y in range(repeat_y):
        for x in range(repeat_x):
            canvas.alpha_composite(src, (x * src.width, y * src.height))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a repeated tile preview for seam inspection.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--repeat-x", type=int, default=3)
    parser.add_argument("--repeat-y", type=int, default=3)
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"source not found: {args.source}")
    if args.repeat_x < 2 or args.repeat_y < 2:
        parser.error("repeat counts must be >= 2")

    output = args.output or (
        ROOT / "assets/textures/comparisons" / f"{args.source.stem}_tile_{args.repeat_x}x{args.repeat_y}.png"
    )
    tile_preview(args.source, output, args.repeat_x, args.repeat_y)
    print(f"PASS tile_preview={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
