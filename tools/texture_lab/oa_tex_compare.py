#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from common import ROOT, alpha_edge_mask, expected_alpha_for_candidate


def _checkerboard(width: int, height: int, tile: int = 16) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (176, 176, 176, 255))
    draw = ImageDraw.Draw(canvas)
    light = (216, 216, 216, 255)
    dark = (176, 176, 176, 255)
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            fill = light if ((x // tile) + (y // tile)) % 2 == 0 else dark
            draw.rectangle(
                (x, y, min(x + tile - 1, width - 1), min(y + tile - 1, height - 1)),
                fill=fill,
            )
    return canvas


def _fit_preview(image: Image.Image, cell: int, classic: bool) -> Image.Image:
    if cell <= 0:
        raise ValueError("cell must be positive")
    scale = min(float(cell) / image.width, float(cell) / image.height)
    target = (
        max(1, int(round(image.width * scale))),
        max(1, int(round(image.height * scale))),
    )
    resampling = getattr(Image, "Resampling", Image)
    if classic and scale >= 1.0:
        filter_mode = resampling.NEAREST
    else:
        filter_mode = resampling.LANCZOS
    return image.resize(target, filter_mode)


DETAIL_REGIONS = [
    ("Upper-left", 0.25, 0.25),
    ("Center", 0.50, 0.50),
    ("Lower-right", 0.75, 0.75),
]


def _normalized_crop(
    image: Image.Image,
    center_x: float,
    center_y: float,
    fraction: float = 0.35,
) -> Image.Image:
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    crop_w = max(1, int(round(image.width * fraction)))
    crop_h = max(1, int(round(image.height * fraction)))
    cx = int(round(image.width * center_x))
    cy = int(round(image.height * center_y))
    left = max(0, min(image.width - crop_w, cx - crop_w // 2))
    top = max(0, min(image.height - crop_h, cy - crop_h // 2))
    return image.crop((left, top, left + crop_w, top + crop_h))


def make_detail_sheet(
    texture_id: str,
    source: Path,
    variants: list[tuple[str, Path]],
    out: Path,
    cell: int,
    fraction: float = 0.35,
) -> None:
    items: list[tuple[str, Image.Image, bool]] = []
    with Image.open(source) as im:
        items.append(("Classic", im.convert("RGBA").copy(), True))
    for label, path in variants:
        if path.is_file():
            with Image.open(path) as im:
                items.append((label, im.convert("RGBA").copy(), False))

    header_h = 28
    region_h = 20
    row_h = region_h + cell
    sheet = Image.new(
        "RGBA",
        (cell * len(items), header_h + row_h * len(DETAIL_REGIONS)),
        (0, 0, 0, 255),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for col, (label, _im, _classic) in enumerate(items):
        draw.text((col * cell + 4, 7), label, fill=(255, 255, 255, 255), font=font)

    for row, (region_label, cx, cy) in enumerate(DETAIL_REGIONS):
        y0 = header_h + row * row_h
        for col, (_label, im, classic) in enumerate(items):
            x0 = col * cell
            draw.text(
                (x0 + 4, y0 + 3),
                region_label,
                fill=(255, 255, 255, 255),
                font=font,
            )
            background = _checkerboard(cell, cell)
            sheet.alpha_composite(background, (x0, y0 + region_h))
            crop = _normalized_crop(im, cx, cy, fraction)
            preview = _fit_preview(crop, cell, classic)
            px = x0 + (cell - preview.width) // 2
            py = y0 + region_h + (cell - preview.height) // 2
            sheet.alpha_composite(preview, (px, py))

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out, format="PNG", optimize=False)


def make_alpha_sheet(
    texture_id: str,
    source: Path,
    candidate: Path,
    out: Path,
    cell: int,
) -> None:
    if cell <= 0:
        raise ValueError("cell must be positive")

    with Image.open(source) as src, Image.open(candidate) as cand:
        src.load()
        cand.load()
        expected = expected_alpha_for_candidate(source, src, cand.size)
        actual = cand.convert("RGBA").getchannel("A")
        delta = ImageChops.difference(expected, actual)
        edge = alpha_edge_mask(expected)

    items = [
        ("Expected alpha", expected.convert("RGBA")),
        ("Candidate alpha", actual.convert("RGBA")),
        ("Absolute delta", delta.convert("RGBA")),
        ("Expected edge band", edge.convert("RGBA")),
    ]

    label_h = 28
    sheet = Image.new(
        "RGBA",
        (cell * len(items), cell + label_h),
        (0, 0, 0, 255),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, image) in enumerate(items):
        preview = _fit_preview(image, cell, False)
        x = index * cell
        px = x + (cell - preview.width) // 2
        py = label_h + (cell - preview.height) // 2
        sheet.alpha_composite(preview, (px, py))
        draw.text(
            (x + 4, 7),
            label,
            fill=(255, 255, 255, 255),
            font=font,
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out, format="PNG", optimize=False)


def make_sheet(texture_id: str, source: Path, variants: list[tuple[str, Path]], out: Path, cell: int) -> None:
    items: list[tuple[str, Image.Image, bool]] = []
    with Image.open(source) as im:
        items.append(("Classic", im.convert("RGBA").copy(), True))
    for label, path in variants:
        if path.is_file():
            with Image.open(path) as im:
                items.append((label, im.convert("RGBA").copy(), False))

    label_h = 28
    sheet = Image.new("RGBA", (cell * len(items), cell + label_h), (0, 0, 0, 255))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, im, classic) in enumerate(items):
        preview = _fit_preview(im, cell, classic)
        x = index * cell
        background = _checkerboard(cell, cell)
        sheet.alpha_composite(background, (x, label_h))
        px = x + (cell - preview.width) // 2
        py = label_h + (cell - preview.height) // 2
        sheet.alpha_composite(preview, (px, py))
        draw.text((x + 4, 7), label, fill=(255, 255, 255, 255), font=font)

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out, format="PNG", optimize=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create repository-ignored visual comparison sheets.")
    parser.add_argument("texture_id")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--enhanced-dir", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument("--ai-restored-dir", type=Path, default=ROOT / "assets/textures/ai_restored")
    parser.add_argument("--ai-recreated-dir", type=Path, default=ROOT / "assets/textures/ai_recreated")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "assets/textures/comparisons")
    parser.add_argument("--cell", type=int, default=320)
    args = parser.parse_args()

    source = args.source_dir / f"{args.texture_id}.png"
    if not source.is_file():
        parser.error(f"source not found: {source}")

    variants = [
        ("Nearest 4x", args.enhanced_dir / args.texture_id / "nearest_x4.png"),
        ("Bicubic 4x", args.enhanced_dir / args.texture_id / "bicubic_x4.png"),
        ("Lanczos 4x", args.enhanced_dir / args.texture_id / "lanczos_x4.png"),
        ("xBRZ 4x", args.enhanced_dir / args.texture_id / "xbrz_x4.png"),
        ("AI Restored", args.ai_restored_dir / args.texture_id / "realesrgan_x4.png"),
        ("AI Recreated", args.ai_recreated_dir / args.texture_id / "selected.png"),
    ]
    out = args.out_dir / f"{args.texture_id}_comparison.png"
    make_sheet(args.texture_id, source, variants, out, args.cell)
    print(f"PASS comparison={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
