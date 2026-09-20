#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

from common import (
    ROOT,
    RESAMPLE,
    apply_legacy_colorkey,
    image_mae,
    optional_ssim,
    should_apply_legacy_colorkey,
    sha256_file,
    write_json,
)


def _gray(image: Image.Image) -> Image.Image:
    return image.convert("L")


def _mae_luma(a: Image.Image, b: Image.Image) -> float:
    aa = _gray(a)
    bb = _gray(b)
    if aa.size != bb.size:
        raise ValueError(f"size mismatch: {aa.size} != {bb.size}")
    return float(ImageStat.Stat(ImageChops.difference(aa, bb)).mean[0])


def _low_frequency(image: Image.Image, radius: float) -> Image.Image:
    return image.convert("RGB").filter(ImageFilter.GaussianBlur(radius=radius))


def _edge_map(image: Image.Image) -> Image.Image:
    return (
        image.convert("L")
        .filter(ImageFilter.GaussianBlur(radius=0.6))
        .filter(ImageFilter.FIND_EDGES)
    )


def _alpha_mismatch_fraction(source: Image.Image, candidate: Image.Image) -> float | None:
    src_alpha = source.convert("RGBA").getchannel("A")
    cand_alpha = candidate.convert("RGBA").getchannel("A")
    if src_alpha.getextrema() == (255, 255) and cand_alpha.getextrema() == (255, 255):
        return None
    if src_alpha.size != cand_alpha.size:
        raise ValueError("alpha comparison requires same-size images")
    a = src_alpha.load()
    b = cand_alpha.load()
    mismatch = 0
    total = src_alpha.width * src_alpha.height
    for y in range(src_alpha.height):
        for x in range(src_alpha.width):
            if (a[x, y] >= 128) != (b[x, y] >= 128):
                mismatch += 1
    return float(mismatch) / float(total) if total else 0.0


def analyze_pair(source: Path, candidate: Path) -> dict:
    with Image.open(source) as src_raw, Image.open(candidate) as cand_raw:
        src_raw.load()
        cand_raw.load()

        legacy_key = should_apply_legacy_colorkey(source, src_raw)
        src = apply_legacy_colorkey(src_raw) if legacy_key else src_raw.convert("RGBA")
        cand = cand_raw.convert("RGBA")
        down = cand.resize(src.size, RESAMPLE["lanczos"])

        # Low-frequency structure ignores most generated microdetail and emphasizes
        # displaced objects, openings, large tonal masses and composition changes.
        blur_radius = max(1.0, min(src.width, src.height) / 64.0)
        src_low = _low_frequency(src, blur_radius)
        down_low = _low_frequency(down, blur_radius)

        src_edges = _edge_map(src)
        down_edges = _edge_map(down)

        return {
            "source": source.name,
            "source_sha256": sha256_file(source),
            "candidate": candidate.name,
            "candidate_sha256": sha256_file(candidate),
            "source_size": list(src.size),
            "candidate_size": list(cand.size),
            "legacy_colorkey_expected": legacy_key,
            "downscale_filter": "lanczos",
            "low_frequency_blur_radius_source_px": round(float(blur_radius), 4),
            "roundtrip_rgba_mae_0_255": image_mae(src, down),
            "roundtrip_ssim_rgb": optional_ssim(src, down),
            "low_frequency_luma_mae_0_255": _mae_luma(src_low, down_low),
            "edge_map_mae_0_255": _mae_luma(src_edges, down_edges),
            "alpha_silhouette_mismatch_fraction": _alpha_mismatch_fraction(src, down),
            "classification": "OBSERVATIONAL_UNCALIBRATED",
        }


def _resolve_candidate(candidate_dir: Path, texture_id: str, variant: str) -> Path:
    nested = candidate_dir / texture_id / variant
    if nested.is_file():
        return nested
    flat = candidate_dir / f"{texture_id}.png"
    if flat.is_file():
        return flat
    return nested


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure layout/structure drift between Classic and generated texture candidates."
    )
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--variant", default="selected.png")
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/texture_lab/structural_drift.json",
    )
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Measure only these canonical texture IDs.",
    )
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    wanted = set(args.only or [])
    rows = []
    missing = []
    found_ids = set()
    for entry in selection["textures"]:
        texture_id = str(entry["id"])
        if wanted and texture_id not in wanted:
            continue
        found_ids.add(texture_id)
        source = args.source_dir / f"{texture_id}.png"
        candidate = _resolve_candidate(args.candidate_dir, texture_id, args.variant)
        if not source.is_file():
            raise SystemExit(f"missing Classic source: {source}")
        if not candidate.is_file():
            missing.append(str(candidate))
            continue
        row = {
            "id": texture_id,
            "room": entry.get("room"),
            "content_class": entry.get("content_class"),
        }
        row.update(analyze_pair(source, candidate))
        rows.append(row)

    if wanted:
        unknown = sorted(wanted - found_ids)
        if unknown:
            raise SystemExit(
                "selected structural IDs are not canonical: "
                + ", ".join(unknown)
            )

    if missing and not args.allow_missing:
        raise SystemExit("missing candidates:\n" + "\n".join(missing))

    write_json(
        args.out,
        {
            "schema": "openazrael.texture_lab.structural_drift.v2",
            "status": "OBSERVATIONAL_UNCALIBRATED",
            "purpose": (
                "Measure structural/layout drift while intentionally tolerating new "
                "high-frequency surface detail. Production thresholds require calibration "
                "against the mathematical Enhanced baseline and reviewed AI candidates."
            ),
            "variant": args.variant,
            "only": sorted(wanted) if wanted else None,
            "results": rows,
            "missing": missing,
        },
    )
    print(f"PASS structural_drift rows={len(rows)} missing={len(missing)} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
