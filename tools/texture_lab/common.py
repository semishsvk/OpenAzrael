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
