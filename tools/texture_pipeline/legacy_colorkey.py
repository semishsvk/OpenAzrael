#!/usr/bin/env python3
"""Conservative legacy binary color-key support for Classic demo textures.

The authoritative Candidate-2 path is index-aware: for a '#' AZF texture we
inspect the palette entries actually referenced by the decoded index plane after
R.EXE-style 6-bit component quantization. Exactly one used magenta-like palette
index is accepted as the binary key. This avoids keying unrelated RGB pixels
merely because they quantize to a similar colour.

The RGB helper remains for synthetic/non-AZF compatibility tests. Runtime GLB
materials can additionally fill hidden RGB below alpha=0 from neighbouring
opaque texels to prevent texture-filter edge darkening; alpha itself is never
changed by that bleed operation.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

LEGACY_MAGENTA_RB_MIN = 248
LEGACY_MAGENTA_G_MAX = 12


def is_legacy_colorkey_name(path_or_name) -> bool:
    return "#" in Path(path_or_name).stem


def legacy_magenta_mask(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb)
    if arr.ndim < 2 or arr.shape[-1] < 3:
        raise ValueError("expected RGB/RGBA image array")
    return (
        (arr[..., 0] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[..., 2] >= LEGACY_MAGENTA_RB_MIN)
        & (arr[..., 1] <= LEGACY_MAGENTA_G_MAX)
    )


def quantized_palette_rgb(
    palette: np.ndarray,
    *,
    quantize_like_engine: bool = True,
) -> np.ndarray:
    arr = np.asarray(palette, dtype=np.uint8)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError("expected palette Nx3/Nx4 array")
    rgb = arr[:, :3].copy()
    if quantize_like_engine:
        rgb = (rgb // 4) * 4
    return rgb


def detect_legacy_colorkey_index(
    palette: np.ndarray,
    indices: np.ndarray,
    path_or_name,
    *,
    quantize_like_engine: bool = True,
) -> tuple[int | None, dict]:
    """Return the one used indexed legacy key, or None when no key applies.

    '#' names define the evidence-backed candidate namespace. Candidate palette
    entries are restricted to entries that are actually referenced by the
    decoded image. Multiple used magenta-like indices are treated as ambiguous
    and fail closed rather than silently keying several source indices.
    """
    idx = np.asarray(indices)
    if idx.ndim < 1:
        raise ValueError("expected indexed image plane")
    rgb = quantized_palette_rgb(
        palette,
        quantize_like_engine=quantize_like_engine,
    )
    if idx.size:
        min_index = int(idx.min())
        max_index = int(idx.max())
        if min_index < 0 or max_index >= len(rgb):
            raise ValueError(
                f"pixel index range {min_index}..{max_index} exceeds "
                f"palette size {len(rgb)}"
            )

    candidate = is_legacy_colorkey_name(path_or_name)
    used_indices = sorted(int(v) for v in np.unique(idx))
    magenta_entries = legacy_magenta_mask(rgb)
    used_magenta_indices = [
        value for value in used_indices if bool(magenta_entries[value])
    ] if candidate else []

    meta = {
        "candidate": candidate,
        "detection": "USED_INDEXED_PALETTE_ENTRY",
        "quantized_like_engine": bool(quantize_like_engine),
        "used_palette_indices": used_indices,
        "used_magenta_key_indices": used_magenta_indices,
        "key_index": None,
        "applied": False,
        "ambiguous": len(used_magenta_indices) > 1,
        "rule": (
            "filename_contains_hash_AND_exactly_one_used_palette_index_"
            "with_quantized_R>=248_B>=248_G<=12"
        ),
    }
    if not candidate or not used_magenta_indices:
        return None, meta
    if len(used_magenta_indices) != 1:
        raise ValueError(
            f"ambiguous legacy color-key for {Path(path_or_name).name}: "
            f"used key candidates={used_magenta_indices}"
        )
    key_index = used_magenta_indices[0]
    meta["key_index"] = key_index
    meta["applied"] = True
    return key_index, meta


def apply_legacy_indexed_colorkey(
    palette: np.ndarray,
    indices: np.ndarray,
    path_or_name,
    *,
    quantize_like_engine: bool = True,
) -> tuple[np.ndarray, dict]:
    idx = np.asarray(indices)
    rgb = quantized_palette_rgb(
        palette,
        quantize_like_engine=quantize_like_engine,
    )
    key_index, meta = detect_legacy_colorkey_index(
        palette,
        idx,
        path_or_name,
        quantize_like_engine=quantize_like_engine,
    )
    rendered = rgb[idx]
    if key_index is None:
        meta["key_pixels"] = 0
        meta["magenta_pixels"] = 0
        return rendered.copy(), meta

    key_mask = idx == key_index
    count = int(key_mask.sum())
    rgba = np.empty((*idx.shape, 4), dtype=np.uint8)
    rgba[..., :3] = rendered
    rgba[..., 3] = 255
    # Source/reference PNGs keep deterministic zero hidden RGB. The runtime GLB
    # path can fill these hidden pixels in-memory without changing alpha.
    rgba[key_mask, :3] = 0
    rgba[key_mask, 3] = 0
    meta["key_pixels"] = count
    meta["magenta_pixels"] = count
    return rgba, meta


def apply_legacy_colorkey(
    rgb: np.ndarray,
    path_or_name,
) -> tuple[np.ndarray, dict]:
    """RGB fallback retained for non-indexed synthetic compatibility tests."""
    arr = np.asarray(rgb, dtype=np.uint8)
    candidate = is_legacy_colorkey_name(path_or_name)
    mask = legacy_magenta_mask(arr[..., :3])
    count = int(mask.sum())
    meta = {
        "candidate": candidate,
        "applied": bool(candidate and count > 0),
        "magenta_pixels": count,
        "key_pixels": count,
        "key_index": None,
        "detection": "RGB_FALLBACK",
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


def bleed_hidden_rgb(rgba: np.ndarray) -> np.ndarray:
    """Fill RGB under alpha=0 from nearest opaque texels, preserving alpha.

    A deterministic multi-source 4-neighbour flood is sufficient for these
    binary-mask textures. It prevents hidden black RGB from darkening filtered
    cutout edges while leaving every visible source texel and alpha byte intact.
    """
    arr = np.asarray(rgba, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[-1] != 4:
        raise ValueError("expected RGBA image array")
    out = arr.copy()
    alpha = out[..., 3]
    transparent = alpha == 0
    if not bool(transparent.any()):
        return out
    opaque = alpha > 0
    if not bool(opaque.any()):
        return out

    height, width = alpha.shape
    visited = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for y, x in np.argwhere(opaque):
        yi, xi = int(y), int(x)
        visited[yi, xi] = True
        queue.append((yi, xi))

    neighbours = ((-1, 0), (0, -1), (0, 1), (1, 0))
    while queue:
        y, x = queue.popleft()
        source_rgb = out[y, x, :3].copy()
        for dy, dx in neighbours:
            ny, nx = y + dy, x + dx
            if ny < 0 or nx < 0 or ny >= height or nx >= width:
                continue
            if visited[ny, nx]:
                continue
            visited[ny, nx] = True
            if alpha[ny, nx] == 0:
                out[ny, nx, :3] = source_rgb
            queue.append((ny, nx))
    return out


def prepare_mask_texture(image: Image.Image) -> Image.Image:
    rgba = np.array(image.convert("RGBA"), dtype=np.uint8)
    return Image.fromarray(bleed_hidden_rgb(rgba), "RGBA")


def image_alpha_mode(image, path_or_name) -> str:
    """Return MASK only for evidence-backed keyed images with real alpha."""
    if not is_legacy_colorkey_name(path_or_name):
        return "OPAQUE"
    rgba = image.convert("RGBA")
    lo, _hi = rgba.getchannel("A").getextrema()
    return "MASK" if lo < 255 else "OPAQUE"
