#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess

from PIL import Image, __version__ as PILLOW_VERSION

from common import (
    ROOT,
    RESAMPLE,
    resize_with_legacy_colorkey,
    sha256_file,
    should_apply_legacy_colorkey,
    write_json,
)


def upscale_one(src: Path, out_dir: Path, factor: int, methods: list[str]) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with Image.open(src) as original:
        original.load()
        target_size = (original.width * factor, original.height * factor)
        legacy_colorkey = should_apply_legacy_colorkey(src, original)
        for method in methods:
            if method not in RESAMPLE:
                raise ValueError(f"unsupported built-in method: {method}")
            if legacy_colorkey:
                result = resize_with_legacy_colorkey(original, target_size, RESAMPLE[method])
                alpha_policy = "legacy_magenta_to_binary_alpha_nearest"
            else:
                result = original.resize(target_size, RESAMPLE[method])
                alpha_policy = "source_native"
            dest = out_dir / f"{method}_x{factor}.png"
            result.save(dest, format="PNG", optimize=False)
            records.append(
                {
                    "method": method,
                    "factor": factor,
                    "file": dest.name,
                    "width": result.width,
                    "height": result.height,
                    "sha256": sha256_file(dest),
                    "legacy_colorkey_applied": legacy_colorkey,
                    "alpha_policy": alpha_policy,
                }
            )
    return records


def run_external_xbrz(template: str, src: Path, dest: Path, factor: int) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    rendered = template.format(input=str(src), output=str(dest), factor=factor)
    argv = shlex.split(rendered)
    subprocess.run(argv, check=True)
    if not dest.is_file():
        raise RuntimeError(f"xBRZ command completed but did not create {dest}")
    return {
        "method": "xbrz",
        "factor": factor,
        "file": dest.name,
        "sha256": sha256_file(dest),
        "command_template": template,
        "legacy_colorkey_applied": False,
        "alpha_policy": "EXTERNAL_BACKEND_UNVERIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic mathematical OpenAzrael texture upscale.")
    parser.add_argument("--input", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument("--report", type=Path, default=ROOT / "data/texture_lab/enhance_run.json")
    parser.add_argument("--factor", type=int, default=4)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["nearest", "bicubic", "lanczos"],
        choices=sorted(RESAMPLE),
    )
    parser.add_argument("--only", nargs="*", default=None, help="Optional texture stems.")
    parser.add_argument(
        "--xbrz-command",
        default=None,
        help="Optional command template with {input}, {output}, {factor}; no shell is used.",
    )
    args = parser.parse_args()

    if args.factor < 2:
        parser.error("--factor must be >= 2")
    if not args.input.is_dir():
        parser.error(f"input directory not found: {args.input}")

    wanted = set(args.only or [])
    sources = [p for p in sorted(args.input.glob("*.png")) if not wanted or p.stem in wanted]
    if not sources:
        raise SystemExit("no input PNGs selected")

    run = {
        "schema": "openazrael.texture_lab.enhance_run.v2",
        "mode": "deterministic_mathematical",
        "pillow_version": PILLOW_VERSION,
        "factor": args.factor,
        "methods": list(args.methods),
        "legacy_colorkey_policy": "conservative_#_plus_quantized_magenta_to_binary_alpha",
        "textures": [],
    }

    for src in sources:
        dest_dir = args.output / src.stem
        variants = upscale_one(src, dest_dir, args.factor, list(args.methods))
        if args.xbrz_command:
            variants.append(
                run_external_xbrz(
                    args.xbrz_command,
                    src,
                    dest_dir / f"xbrz_x{args.factor}.png",
                    args.factor,
                )
            )
        run["textures"].append(
            {
                "id": src.stem,
                "source_sha256": sha256_file(src),
                "variants": variants,
            }
        )

    write_json(args.report, run)
    print(f"PASS enhanced textures={len(run['textures'])} factor={args.factor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
