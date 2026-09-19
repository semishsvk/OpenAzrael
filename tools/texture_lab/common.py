#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
from typing import Any

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
RESAMPLING = getattr(Image, "Resampling", Image)
RESAMPLE = {
    "nearest": RESAMPLING.NEAREST,
    "bicubic": RESAMPLING.BICUBIC,
    "lanczos": RESAMPLING.LANCZOS,
}

LEGACY_MAGENTA_RB_MIN = 248
LEGACY_MAGENTA_G_MAX = 12


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def has_alpha(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA"):
        return True
    return image.mode == "P" and "transparency" in image.info


def is_legacy_magenta(rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> bool:
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    return r >= LEGACY_MAGENTA_RB_MIN and b >= LEGACY_MAGENTA_RB_MIN and g <= LEGACY_MAGENTA_G_MAX


def legacy_colorkey_stats(image: Image.Image) -> dict[str, float | int]:
    rgb = image.convert("RGB")
    px = rgb.load()
    count = 0
    for y in range(rgb.height):
        for x in range(rgb.width):
            if is_legacy_magenta(px[x, y]):
                count += 1
    total = rgb.width * rgb.height
    return {
        "pixels": count,
        "fraction": (float(count) / float(total)) if total else 0.0,
    }


def should_apply_legacy_colorkey(path: Path, image: Image.Image) -> bool:
    # Conservative POC rule: only legacy '#' assets with observed quantized
    # magenta pixels are converted. This is a presentation-safety rule, not a
    # claim that the complete original transparency semantics are recovered.
    if "#" not in path.stem:
        return False
    return int(legacy_colorkey_stats(image)["pixels"]) > 0


def apply_legacy_colorkey(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if is_legacy_magenta((r, g, b)):
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (r, g, b, a)
    return rgba


def resize_with_legacy_colorkey(
    image: Image.Image,
    target_size: tuple[int, int],
    resample: int,
) -> Image.Image:
    rgba = apply_legacy_colorkey(image)
    if resample == RESAMPLE["nearest"]:
        return rgba.resize(target_size, resample)

    # Premultiplied RGB prevents transparent-magenta bleed during filtering.
    # Alpha is then restored with nearest-neighbour so the legacy binary mask
    # remains exact in the deterministic Enhanced tier.
    premultiplied = rgba.convert("RGBa").resize(target_size, resample).convert("RGBA")
    alpha = rgba.getchannel("A").resize(target_size, RESAMPLE["nearest"])
    premultiplied.putalpha(alpha)
    return premultiplied


def prepare_conditioning_image(
    source_classic: Path,
    conditioning_image: Path,
    prepared: Path,
) -> tuple[Path, bool]:
    """Prepare a high-resolution AI conditioning canvas.

    Classic remains the evidence source for legacy color-key semantics. The
    conditioning image may be a 4x Enhanced candidate. For keyed assets, the
    exact Classic-derived binary silhouette is resized with nearest-neighbour
    and locked onto the conditioning canvas before it reaches the AI backend.
    """
    with Image.open(source_classic) as source_image:
        source_image.load()
        legacy_colorkey = should_apply_legacy_colorkey(source_classic, source_image)
        source_alpha = (
            apply_legacy_colorkey(source_image).getchannel("A")
            if legacy_colorkey
            else None
        )

    if not legacy_colorkey:
        return conditioning_image, False

    with Image.open(conditioning_image) as cond_image:
        cond_image.load()
        rgba = cond_image.convert("RGBA")
        alpha = source_alpha.resize(rgba.size, RESAMPLE["nearest"])
        rgba.putalpha(alpha)
        rgba = zero_fully_transparent_rgb(rgba)

    prepared.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(prepared, format="PNG", optimize=False)
    return prepared, True


def prepare_backend_colorkey_input(source: Path, prepared: Path) -> tuple[Path, bool]:
    with Image.open(source) as image:
        image.load()
        if not should_apply_legacy_colorkey(source, image):
            return source, False
        rgba = apply_legacy_colorkey(image)
    prepared.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(prepared, format="PNG", optimize=False)
    return prepared, True


def reapply_source_colorkey_mask(source: Path, output: Path) -> bool:
    with Image.open(source) as source_image:
        source_image.load()
        if not should_apply_legacy_colorkey(source, source_image):
            return False
        source_alpha = apply_legacy_colorkey(source_image).getchannel("A")

    with Image.open(output) as output_image:
        output_image.load()
        rgba = output_image.convert("RGBA")
        alpha = source_alpha.resize(rgba.size, RESAMPLE["nearest"])
        rgba.putalpha(alpha)
        rgba = zero_fully_transparent_rgb(rgba)
    rgba.save(output, format="PNG", optimize=False)
    return True


def zero_fully_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a == 0:
                px[x, y] = (0, 0, 0, 0)
    return rgba


def visible_legacy_magenta_pixels(image: Image.Image) -> int:
    rgba = image.convert("RGBA")
    px = rgba.load()
    count = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a > 0 and is_legacy_magenta((r, g, b)):
                count += 1
    return count


def alpha_is_binary(image: Image.Image) -> bool:
    rgba = image.convert("RGBA")
    extrema = rgba.getchannel("A").getextrema()
    if extrema == (255, 255):
        return True
    px = rgba.getchannel("A").load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if px[x, y] not in (0, 255):
                return False
    return True


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def image_mae(a: Image.Image, b: Image.Image) -> float:
    aa = a.convert("RGBA")
    bb = b.convert("RGBA")
    if aa.size != bb.size:
        raise ValueError(f"size mismatch: {aa.size} != {bb.size}")
    diff = ImageChops.difference(aa, bb)
    means = ImageStat.Stat(diff).mean
    return float(sum(means) / len(means))


def mean_rgba(image: Image.Image) -> list[float]:
    return [float(v) for v in ImageStat.Stat(image.convert("RGBA")).mean]


def seam_mae(image: Image.Image) -> dict[str, float]:
    rgba = image.convert("RGBA")
    w, h = rgba.size
    if w < 2 or h < 2:
        return {"x": 0.0, "y": 0.0}
    left = rgba.crop((0, 0, 1, h))
    right = rgba.crop((w - 1, 0, w, h))
    top = rgba.crop((0, 0, w, 1))
    bottom = rgba.crop((0, h - 1, w, h))
    return {
        "x": image_mae(left, right),
        "y": image_mae(top, bottom),
    }


def optional_ssim(a: Image.Image, b: Image.Image) -> float | None:
    try:
        import numpy as np
        from skimage.metrics import structural_similarity
    except Exception:
        return None

    aa = np.asarray(a.convert("RGB"), dtype=np.uint8)
    bb = np.asarray(b.convert("RGB"), dtype=np.uint8)
    if aa.shape != bb.shape:
        raise ValueError(f"shape mismatch: {aa.shape} != {bb.shape}")
    return float(structural_similarity(aa, bb, channel_axis=2, data_range=255))
