#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, __version__ as PILLOW_VERSION

from common import (
    ROOT,
    has_alpha,
    legacy_colorkey_stats,
    sha256_file,
    should_apply_legacy_colorkey,
    write_json,
)


def scan(input_dir: Path) -> dict:
    entries = []
    for path in sorted(input_dir.glob("*.png")):
        with Image.open(path) as im:
            im.load()
            key_stats = legacy_colorkey_stats(im)
            entries.append(
                {
                    "id": path.stem,
                    "file": path.name,
                    "width": im.width,
                    "height": im.height,
                    "mode": im.mode,
                    "has_alpha": has_alpha(im),
                    "source_sha256": sha256_file(path),
                    "legacy_colorkey_candidate": should_apply_legacy_colorkey(path, im),
                    "legacy_magenta_pixels": key_stats["pixels"],
                    "legacy_magenta_fraction": key_stats["fraction"],
                    "material_class": "unclassified",
                    "tileable": None,
                    "room_usage": [],
                    "variant_status": {
                        "enhanced": "pending",
                        "ai_restored": "pending",
                        "ai_recreated": "pending",
                    },
                }
            )
    return {
        "schema": "openazrael.texture_lab.classic_manifest.v2",
        "source_kind": "local_excluded_commercial_derived",
        "pillow_version": PILLOW_VERSION,
        "legacy_colorkey_policy": {
            "status": "POC_PRESENTATION_SAFETY_NOT_ORIGINAL_RENDERER_PROOF",
            "candidate_rule": "filename contains # AND quantized magenta pixels exist",
            "magenta_rule": "R>=248 AND B>=248 AND G<=12",
        },
        "texture_count": len(entries),
        "textures": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan local Classic PNGs into repository-safe metadata.")
    parser.add_argument("--input", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--out", type=Path, default=ROOT / "data/texture_lab/classic_manifest.json")
    parser.add_argument("--expect-count", type=int, default=86)
    args = parser.parse_args()

    if not args.input.is_dir():
        parser.error(f"input directory not found: {args.input}")

    result = scan(args.input)
    if args.expect_count >= 0 and result["texture_count"] != args.expect_count:
        raise SystemExit(
            f"expected {args.expect_count} textures, found {result['texture_count']} in {args.input}"
        )
    write_json(args.out, result)
    print(f"PASS scan textures={result['texture_count']} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
