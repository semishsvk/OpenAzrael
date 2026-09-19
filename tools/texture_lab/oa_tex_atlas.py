#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from common import sha256_file, write_json


def split_equal(
    source: Path,
    output_dir: Path,
    axis: str,
    segments: int,
    prefix: str = "part",
) -> list[dict]:
    if segments < 2:
        raise ValueError("segments must be >= 2")
    with Image.open(source) as im:
        im.load()
        image = im.copy()

    length = image.width if axis == "x" else image.height
    if length % segments != 0:
        raise ValueError(
            f"{source}: {axis}-dimension {length} is not divisible by {segments}"
        )
    step = length // segments
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(segments):
        if axis == "x":
            box = (index * step, 0, (index + 1) * step, image.height)
        else:
            box = (0, index * step, image.width, (index + 1) * step)
        part = image.crop(box)
        path = output_dir / f"{prefix}_{index:02d}.png"
        part.save(path, format="PNG", optimize=False)
        rows.append(
            {
                "index": index,
                "file": path.name,
                "box": list(box),
                "size": list(part.size),
                "sha256": sha256_file(path),
            }
        )
    return rows


def stitch_equal(
    input_dir: Path,
    output: Path,
    axis: str,
    segments: int,
    prefix: str = "part",
) -> dict:
    paths = [input_dir / f"{prefix}_{index:02d}.png" for index in range(segments)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing atlas parts: " + ", ".join(missing))

    images = []
    for path in paths:
        with Image.open(path) as im:
            im.load()
            images.append(im.convert("RGBA").copy())

    if axis == "x":
        if len({im.height for im in images}) != 1:
            raise ValueError("all x-atlas parts must have equal height")
        size = (sum(im.width for im in images), images[0].height)
    else:
        if len({im.width for im in images}) != 1:
            raise ValueError("all y-atlas parts must have equal width")
        size = (images[0].width, sum(im.height for im in images))

    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = 0
    for image in images:
        if axis == "x":
            canvas.alpha_composite(image, (offset, 0))
            offset += image.width
        else:
            canvas.alpha_composite(image, (0, offset))
            offset += image.height

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=False)
    return {
        "file": str(output),
        "size": list(canvas.size),
        "sha256": sha256_file(output),
        "axis": axis,
        "segments": segments,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Split/stitch exact equal-region texture atlases.")
    sub = parser.add_subparsers(dest="command", required=True)

    split = sub.add_parser("split")
    split.add_argument("source", type=Path)
    split.add_argument("--output-dir", type=Path, required=True)
    split.add_argument("--axis", choices=["x", "y"], required=True)
    split.add_argument("--segments", type=int, required=True)
    split.add_argument("--prefix", default="part")
    split.add_argument("--manifest", type=Path, default=None)

    stitch = sub.add_parser("stitch")
    stitch.add_argument("--input-dir", type=Path, required=True)
    stitch.add_argument("--output", type=Path, required=True)
    stitch.add_argument("--axis", choices=["x", "y"], required=True)
    stitch.add_argument("--segments", type=int, required=True)
    stitch.add_argument("--prefix", default="part")
    stitch.add_argument("--manifest", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "split":
        rows = split_equal(
            args.source, args.output_dir, args.axis, args.segments, args.prefix
        )
        payload = {
            "schema": "openazrael.texture_lab.atlas_split.v1",
            "source": str(args.source),
            "source_sha256": sha256_file(args.source),
            "axis": args.axis,
            "segments": args.segments,
            "parts": rows,
        }
        if args.manifest:
            write_json(args.manifest, payload)
        print(f"PASS atlas_split parts={len(rows)} source={args.source}")
        return 0

    result = stitch_equal(
        args.input_dir, args.output, args.axis, args.segments, args.prefix
    )
    payload = {
        "schema": "openazrael.texture_lab.atlas_stitch.v1",
        **result,
    }
    if args.manifest:
        write_json(args.manifest, payload)
    print(f"PASS atlas_stitch output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
