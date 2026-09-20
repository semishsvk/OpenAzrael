#!/usr/bin/env python3
"""Indexed legacy binary color-key support for Classic demo textures.

The KG-001 demo rule is bound to the audited ATDEMO corpus:
- only source texture names containing '#';
- choose transparency in original indexed AZF space, before RGB expansion;
- exactly one *used* source-palette entry must match the observed sentinel
  family: R==255, B==255, G<=8;
- only pixels carrying that exact palette index become transparent.

The broader quantized-magenta range remains diagnostic evidence only. It is
not used to choose transparent pixels because BLOOS4#.AZF contains one used
near-magenta non-sentinel entry in addition to the actual background key.

This is a presentation-compatibility rule, not a claim that every original
Azrael renderer transparency/blending semantic has been recovered.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

LEGACY_SENTINEL_RB = 255
LEGACY_SENTINEL_G_MAX = 8
LEGACY_MAGENTA_RB_MIN = 248
LEGACY_MAGENTA_G_MAX = 12


def is_legacy_colorkey_name(path_or_name) -> bool:
    return "#" in Path(path_or_name).stem


def legacy_source_sentinel_mask(source_palette: np.ndarray) -> np.ndarray:
    arr = np.asarray(source_palette, dtype=np.uint8)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError("expected Nx3/Nx4 source palette array")
    return (
        (arr[:, 0] == LEGACY_SENTINEL_RB)
        & (arr[:, 2] == LEGACY_SENTINEL_RB)
        & (arr[:, 1] <= LEGACY_SENTINEL_G_MAX)
    )


def legacy_magenta_palette_mask(rgb_palette: np.ndarray) -> np.ndarray:
    """Broad post-quantization diagnostic range; never selects alpha."""
    arr = np.asarray(rgb_palette, dtype=np.uint8)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError("expected Nx3/Nx4 palette array")
    return (
        (arr[:, 0] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[:, 2] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[:, 1] <= LEGACY_MAGENTA_G_MAX)
    )


def analyze_indexed_colorkey(
    indices: np.ndarray,
    source_palette: np.ndarray,
    output_rgb_palette: np.ndarray,
    path_or_name,
) -> dict:
    idx = np.asarray(indices)
    source = np.asarray(source_palette, dtype=np.uint8)
    output = np.asarray(output_rgb_palette, dtype=np.uint8)
    candidate = is_legacy_colorkey_name(path_or_name)
    if idx.size == 0:
        raise ValueError("empty indexed texture")
    if int(idx.max()) >= len(source) or len(source) != len(output):
        raise ValueError("pixel index/palette size mismatch")

    counts = np.bincount(idx.reshape(-1), minlength=len(source))
    sentinel = legacy_source_sentinel_mask(source)
    used_sentinel = [int(i) for i in np.flatnonzero((counts > 0) & sentinel)]
    broad = legacy_magenta_palette_mask(output)
    used_broad = [int(i) for i in np.flatnonzero((counts > 0) & broad)]

    if not candidate:
        return {
            "candidate": False,
            "applied": False,
            "key_index": None,
            "key_source_rgba": None,
            "key_output_rgb": None,
            "key_pixels": 0,
            "used_sentinel_indices": used_sentinel,
            "used_broad_magenta_indices": used_broad,
            "rule": "indexed_hash_source_sentinel_v2",
        }

    if len(used_sentinel) != 1:
        raise ValueError(
            "legacy # texture requires exactly one used source-palette "
            "sentinel (R==255,B==255,G<=8); found "
            f"{used_sentinel} in {Path(path_or_name).name}"
        )

    key_index = used_sentinel[0]
    return {
        "candidate": True,
        "applied": True,
        "key_index": key_index,
        "key_source_rgba": [int(x) for x in source[key_index]],
        "key_output_rgb": [int(x) for x in output[key_index, :3]],
        "key_pixels": int(counts[key_index]),
        "used_sentinel_indices": used_sentinel,
        "used_broad_magenta_indices": used_broad,
        "rule": "indexed_hash_source_sentinel_v2",
    }


def render_indexed_colorkey(
    indices: np.ndarray,
    source_palette: np.ndarray,
    output_rgb_palette: np.ndarray,
    path_or_name,
) -> tuple[np.ndarray, dict]:
    idx = np.asarray(indices)
    output = np.asarray(output_rgb_palette, dtype=np.uint8)
    meta = analyze_indexed_colorkey(indices, source_palette, output, path_or_name)

    if not meta["applied"]:
        return output[idx, :3].copy(), meta

    rgba_palette = np.empty((len(output), 4), dtype=np.uint8)
    rgba_palette[:, :3] = output[:, :3]
    rgba_palette[:, 3] = 255
    key_index = int(meta["key_index"])
    rgba_palette[key_index, :3] = 0
    rgba_palette[key_index, 3] = 0
    return rgba_palette[idx], meta


def image_alpha_mode(image, path_or_name) -> str:
    if not is_legacy_colorkey_name(path_or_name):
        return "OPAQUE"
    rgba = image.convert("RGBA")
    lo, _hi = rgba.getchannel("A").getextrema()
    return "MASK" if lo < 255 else "OPAQUE"
