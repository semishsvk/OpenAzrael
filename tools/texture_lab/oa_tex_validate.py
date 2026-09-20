#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from common import (
    ROOT,
    RESAMPLE,
    alpha_is_binary,
    alpha_mask_mismatch_pixels,
    classify_transparency,
    apply_legacy_colorkey,
    has_alpha,
    image_mae,
    mean_rgba,
    optional_ssim,
    seam_mae,
    sha256_file,
    should_apply_legacy_colorkey,
    transparent_rgb_nonzero_pixels,
    visible_legacy_magenta_pixels,
    write_json,
)


def validate_pair(source: Path, candidate: Path, factor: int) -> dict:
    with Image.open(source) as src, Image.open(candidate) as cand:
        src.load()
        cand.load()
        expected = (src.width * factor, src.height * factor)
        size_ok = cand.size == expected

        source_transparency = classify_transparency(source, src)
        legacy_colorkey = should_apply_legacy_colorkey(source, src)
        source_compare = apply_legacy_colorkey(src) if legacy_colorkey else src.convert("RGBA")

        roundtrip = cand.resize(src.size, RESAMPLE["lanczos"])
        rt_rgba = roundtrip.convert("RGBA")

        src_mean = mean_rgba(source_compare)
        rt_mean = mean_rgba(rt_rgba)
        color_drift = [abs(a - b) for a, b in zip(src_mean, rt_mean)]

        candidate_has_alpha = has_alpha(cand)
        binary_alpha = alpha_is_binary(cand) if legacy_colorkey else None
        visible_magenta = visible_legacy_magenta_pixels(cand) if legacy_colorkey else 0
        hidden_rgb = transparent_rgb_nonzero_pixels(cand) if legacy_colorkey else 0
        mask_mismatch = None
        exact_mask_ok = None
        if legacy_colorkey:
            source_alpha = source_compare.getchannel("A")
            candidate_alpha = cand.convert("RGBA").getchannel("A")
            mask_mismatch = alpha_mask_mismatch_pixels(source_alpha, candidate_alpha)
            exact_mask_ok = mask_mismatch == 0
        colorkey_ok = (
            (not legacy_colorkey)
            or (
                candidate_has_alpha
                and bool(binary_alpha)
                and visible_magenta == 0
                and hidden_rgb == 0
                and bool(exact_mask_ok)
            )
        )

        source_seam = seam_mae(source_compare)
        candidate_seam = seam_mae(cand)
        seam_delta = {
            axis: float(candidate_seam[axis]) - float(source_seam[axis])
            for axis in ("x", "y")
        }
        seam_ratio = {
            axis: (
                float(candidate_seam[axis]) / float(source_seam[axis])
                if float(source_seam[axis]) > 1e-9
                else None
            )
            for axis in ("x", "y")
        }

        technical_ok = size_ok and colorkey_ok

        return {
            "source": source.name,
            "source_sha256": sha256_file(source),
            "candidate": candidate.name,
            "candidate_sha256": sha256_file(candidate),
            "expected_size": list(expected),
            "actual_size": list(cand.size),
            "size_ok": size_ok,
            "source_transparency_mode": source_transparency["mode"],
            "source_transparency_review_required": source_transparency[
                "manual_review_required"
            ],
            "source_transparency_reason": source_transparency["reason"],
            "legacy_colorkey_expected": legacy_colorkey,
            "candidate_has_alpha": candidate_has_alpha,
            "candidate_binary_alpha": binary_alpha,
            "visible_legacy_magenta_pixels": visible_magenta,
            "transparent_rgb_nonzero_pixels": hidden_rgb,
            "alpha_mask_mismatch_pixels": mask_mismatch,
            "exact_alpha_mask_ok": exact_mask_ok,
            "colorkey_ok": colorkey_ok,
            "roundtrip_mae_rgba_0_255": image_mae(source_compare, rt_rgba),
            "roundtrip_ssim_rgb": optional_ssim(source_compare, roundtrip),
            "roundtrip_mean_rgba_abs_drift": color_drift,
            "source_edge_seam_mae_rgba_0_255": source_seam,
            "candidate_edge_seam_mae_rgba_0_255": candidate_seam,
            "candidate_minus_source_seam_mae_rgba_0_255": seam_delta,
            "candidate_to_source_seam_ratio": seam_ratio,
            "seam_interpretation": "OBSERVATIONAL_UNCALIBRATED",
            "fidelity_thresholds": "UNCALIBRATED_HOLD",
            "technical_status": "PASS" if technical_ok else "FAIL",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Enhanced/AI texture candidates against Classic source.")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--candidate-dir", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument("--variant", default="lanczos_x4.png")
    parser.add_argument("--factor", type=int, default=4)
    parser.add_argument("--out", type=Path, default=ROOT / "data/texture_lab/validation.json")
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Validate only these Classic texture IDs. Missing selected outputs remain hard failures.",
    )
    args = parser.parse_args()

    wanted = set(args.only or [])
    sources = [
        src
        for src in sorted(args.source_dir.glob("*.png"))
        if not wanted or src.stem in wanted
    ]
    if not sources:
        raise SystemExit(f"no selected Classic source PNGs found in {args.source_dir}")

    if wanted:
        found = {src.stem for src in sources}
        missing_sources = sorted(wanted - found)
        if missing_sources:
            raise SystemExit(
                "selected Classic source IDs are missing: " + ", ".join(missing_sources)
            )

    rows = []
    for src in sources:
        cand = args.candidate_dir / src.stem / args.variant
        if not cand.is_file():
            rows.append({"id": src.stem, "technical_status": "MISSING", "candidate": str(cand)})
            continue
        row = {"id": src.stem}
        row.update(validate_pair(src, cand, args.factor))
        rows.append(row)

    failures = [r for r in rows if r["technical_status"] != "PASS"]
    report = {
        "schema": "openazrael.texture_lab.validation.v6",
        "variant": args.variant,
        "factor": args.factor,
        "only": sorted(wanted) if wanted else None,
        "note": (
            "Legacy color-key exact-mask integrity is a hard technical gate. "
            "Fidelity, ambiguous transparency interpretation, and source-relative "
            "seam metrics remain observational until calibrated/manual review."
        ),
        "results": rows,
        "technical_failures": len(failures),
    }
    write_json(args.out, report)
    print(f"{'PASS' if not failures else 'FAIL'} technical_failures={len(failures)} rows={len(rows)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
