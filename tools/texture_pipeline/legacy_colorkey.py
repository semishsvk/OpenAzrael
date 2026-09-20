#!/usr/bin/env python3
"""Indexed legacy binary color-key support for Classic demo textures.

The canonical Candidate rule is intentionally strict:
- only source texture names containing '#';
- determine transparency in original indexed AZF space, before RGB expansion;
- exactly one *used* palette index must match the recovered quantized-magenta
  key range (R>=248, B>=248, G<=12);
- only pixels carrying that exact palette index become transparent.

This is a presentation-compatibility rule. It does not claim that every
original Azrael renderer transparency/blending semantic has been recovered.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

LEGACY_MAGENTA_RB_MIN = 248
LEGACY_MAGENTA_G_MAX = 12


def is_legacy_colorkey_name(path_or_name) -> bool:
    return "#" in Path(path_or_name).stem


def legacy_magenta_palette_mask(rgb_palette: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb_palette, dtype=np.uint8)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError("expected Nx3/Nx4 palette array")
    return (
        (arr[:, 0] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[:, 2] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[:, 1] <= LEGACY_MAGENTA_G_MAX)
    )


def legacy_magenta_mask(rgb: np.ndarray) -> np.ndarray:
    """RGB-space diagnostic only; never use this to choose transparent pixels."""
    arr = np.asarray(rgb, dtype=np.uint8)
    if arr.ndim < 3 or arr.shape[-1] < 3:
        raise ValueError("expected RGB/RGBA image array")
    return (
        (arr[..., 0] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[..., 2] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[..., 1] <= LEGACY_MAGENTA_G_MAX)
    )


def analyze_indexed_colorkey(indices: np.ndarray, rgb_palette: np.ndarray, path_or_name) -> dict:
    idx = np.asarray(indices)
    palette = np.asarray(rgb_palette, dtype=np.uint8)
    candidate = is_legacy_colorkey_name(path_or_name)
    if idx.size == 0:
        raise ValueError("empty indexed texture")
    if int(idx.max()) >= len(palette):
        raise ValueError("pixel index exceeds palette size")

    counts = np.bincount(idx.reshape(-1), minlength=len(palette))
    magenta = legacy_magenta_palette_mask(palette)
    used_matches = [int(i) for i in np.flatnonzero((counts > 0) & magenta)]

    if not candidate:
        return {
            "candidate": False,
            "applied": False,
            "key_index": None,
            "key_rgb": None,
            "key_pixels": 0,
            "used_magenta_indices": used_matches,
            "rule": "indexed_hash_exact_single_used_magenta_v1",
        }

    if len(used_matches) != 1:
        raise ValueError(
            "legacy # texture requires exactly one used magenta colour-key "
            f"palette index; found {used_matches} in {Path(path_or_name).name}"
        )

    key_index = used_matches[0]
    return {
        "candidate": True,
        "applied": True,
        "key_index": key_index,
        "key_rgb": [int(x) for x in palette[key_index, :3]],
        "key_pixels": int(counts[key_index]),
        "used_magenta_indices": used_matches,
        "rule": "indexed_hash_exact_single_used_magenta_v1",
    }


def render_indexed_colorkey(indices: np.ndarray, rgb_palette: np.ndarray, path_or_name) -> tuple[np.ndarray, dict]:
    idx = np.asarray(indices)
    palette = np.asarray(rgb_palette, dtype=np.uint8)
    meta = analyze_indexed_colorkey(idx, palette, path_or_name)

    if not meta["applied"]:
        return palette[idx, :3].copy(), meta

    rgba_palette = np.empty((len(palette), 4), dtype=np.uint8)
    rgba_palette[:, :3] = palette[:, :3]
    rgba_palette[:, 3] = 255
    key_index = int(meta["key_index"])
    # Hidden keyed RGB is zeroed for deterministic presentation safety. The
    # identity of transparent pixels is still decided exclusively in indexed
    # space before RGB expansion.
    rgba_palette[key_index, :3] = 0
    rgba_palette[key_index, 3] = 0
    return rgba_palette[idx], meta


def image_alpha_mode(image, path_or_name) -> str:
    """Return MASK only for a '#' texture that actually carries transparency."""
    if not is_legacy_colorkey_name(path_or_name):
        return "OPAQUE"
    rgba = image.convert("RGBA")
    lo, _hi = rgba.getchannel("A").getextrema()
    return "MASK" if lo < 255 else "OPAQUE"
