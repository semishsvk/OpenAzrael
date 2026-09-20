#!/usr/bin/env python3
"""Conservative legacy binary color-key support for Classic demo textures.

This is a presentation-compatibility rule shared with Texture Lab. It is not
proof that every original Azrael renderer transparency semantic is recovered.
Only '#' texture names with observed quantized magenta pixels are keyed.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

LEGACY_MAGENTA_RB_MIN = 248
LEGACY_MAGENTA_G_MAX = 12


def is_legacy_colorkey_name(path_or_name) -> bool:
    return "#" in Path(path_or_name).stem


def legacy_magenta_mask(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb)
    if arr.ndim < 3 or arr.shape[-1] < 3:
        raise ValueError("expected RGB/RGBA image array")
    return (
        (arr[..., 0] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[..., 2] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[..., 1] <= LEGACY_MAGENTA_G_MAX)
    )


def apply_legacy_colorkey(rgb: np.ndarray, path_or_name) -> tuple[np.ndarray, dict]:
    arr = np.asarray(rgb, dtype=np.uint8)
    candidate = is_legacy_colorkey_name(path_or_name)
    mask = legacy_magenta_mask(arr[..., :3])
    count = int(mask.sum())
    meta = {
        "candidate": candidate,
        "applied": bool(candidate and count > 0),
        "magenta_pixels": count,
        "rule": "filename_contains_hash_AND_R>=248_B>=248_G<=12",
    }
    if not meta["applied"]:
        return arr[..., :3].copy(), meta

    rgba = np.empty((*arr.shape[:2], 4), dtype=np.uint8)
    rgba[..., :3] = arr[..., :3]
    rgba[..., 3] = 255
    rgba[mask, :3] = 0
    rgba[mask, 3] = 0
    return rgba, meta


def image_alpha_mode(image, path_or_name) -> str:
    """Return MASK only for evidence-backed keyed images with real alpha."""
    if not is_legacy_colorkey_name(path_or_name):
        return "OPAQUE"
    rgba = image.convert("RGBA")
    lo, hi = rgba.getchannel("A").getextrema()
    return "MASK" if lo < 255 else "OPAQUE"
