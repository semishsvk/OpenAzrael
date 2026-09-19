#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, __version__ as PILLOW_VERSION

from common import ROOT, write_json
from oa_tex_enhance import upscale_one
from oa_tex_validate import validate_pair


def load_selection(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("textures")
    if not isinstance(rows, list) or not rows:
        raise ValueError("selection file contains no textures")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the reproducible RT-POC-01 mathematical bake-off.")
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument("--report", type=Path, default=ROOT / "data/texture_lab/rt_poc_01_run.json")
    parser.add_argument("--factor", type=int, default=4)
    args = parser.parse_args()

    selected = load_selection(args.selection)
    methods = ["nearest", "bicubic", "lanczos"]
    report = {
        "schema": "openazrael.texture_lab.rt_poc_01_run.v1",
        "status": "OBSERVATIONAL",
        "pillow_version": PILLOW_VERSION,
        "factor": args.factor,
        "methods": methods,
        "automatic_winner": False,
        "textures": [],
    }

    for entry in selected:
        stem = entry["id"]
        src = args.source_dir / f"{stem}.png"
        if not src.is_file():
            raise SystemExit(f"missing selected Classic texture: {src}")

        with Image.open(src) as im:
            size = list(im.size)
        expected = entry.get("expected_size")
        if expected and list(expected) != size:
            raise SystemExit(f"{stem}: expected source size {expected}, got {size}")

        out_dir = args.output_dir / stem
        variants = upscale_one(src, out_dir, args.factor, methods)
        metrics = []
        for variant in variants:
            candidate = out_dir / variant["file"]
            row = validate_pair(src, candidate, args.factor)
            metrics.append({"method": variant["method"], **row})

        report["textures"].append(
            {
                "id": stem,
                "room": entry.get("room"),
                "content_class": entry.get("content_class"),
                "source_size": size,
                "metrics": metrics,
            }
        )

    write_json(args.report, report)
    print(f"PASS RT-POC-01 textures={len(report['textures'])} methods={len(methods)} report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
