#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from common import (
    ROOT,
    RESAMPLE,
    alpha_is_binary,
    apply_legacy_colorkey,
    has_alpha,
    image_mae,
    mean_rgba,
    optional_ssim,
    seam_mae,
    sha256_file,
    should_apply_legacy_colorkey,
    visible_legacy_magenta_pixels,
    write_json,
)


def validate_pair(source: Path, candidate: Path, factor: int) -> dict:
    with Image.open(source) as src, Image.open(candidate) as cand:
        src.load()
        cand.load()
        expected = (src.width * factor, src.height * factor)
        size_ok = cand.size == expected

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
        colorkey_ok = (
            (not legacy_colorkey)
            or (candidate_has_alpha and bool(binary_alpha) and visible_magenta == 0)
        )

        technical_ok = size_ok and colorkey_ok

        return {
            "source": source.name,
            "candidate": candidate.name,
            "candidate_sha256": sha256_file(candidate),
            "expected_size": list(expected),
            "actual_size": list(cand.size),
            "size_ok": size_ok,
            "legacy_colorkey_expected": legacy_colorkey,
            "candidate_has_alpha": candidate_has_alpha,
            "candidate_binary_alpha": binary_alpha,
            "visible_legacy_magenta_pixels": visible_magenta,
            "colorkey_ok": colorkey_ok,
            "roundtrip_mae_rgba_0_255": image_mae(source_compare, rt_rgba),
            "roundtrip_ssim_rgb": optional_ssim(source_compare, roundtrip),
            "roundtrip_mean_rgba_abs_drift": color_drift,
            "candidate_edge_seam_mae_rgba_0_255": seam_mae(cand),
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
    args = parser.parse_args()

    sources = sorted(args.source_dir.glob("*.png"))
    if not sources:
        raise SystemExit(f"no Classic source PNGs found in {args.source_dir}")

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
        "schema": "openazrael.texture_lab.validation.v2",
        "variant": args.variant,
        "factor": args.factor,
        "note": "Fidelity metrics are observational until thresholds are calibrated on RT-POC-01.",
        "results": rows,
        "technical_failures": len(failures),
    }
    write_json(args.out, report)
    print(f"{'PASS' if not failures else 'FAIL'} technical_failures={len(failures)} rows={len(rows)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
