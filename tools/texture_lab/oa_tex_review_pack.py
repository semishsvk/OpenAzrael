#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, sha256_file, write_json
from oa_tex_compare import make_sheet
from oa_tex_tile import tile_preview


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_record(path: Path) -> dict:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def sampling_index(report: dict) -> dict[str, dict]:
    return {
        str(row["id"]): row
        for row in report.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    }


def candidate_path(
    mode: str,
    texture_id: str,
    restored_dir: Path,
    recreated_dir: Path,
) -> Path:
    if mode == "restored":
        return restored_dir / texture_id / "realesrgan_x4.png"
    return recreated_dir / texture_id / "selected.png"


def markdown_report(mode: str, rows: list[dict]) -> str:
    lines = [
        f"# OpenAzrael Texture Lab — {mode.title()} Visual Review Pack",
        "",
        "This pack is for manual visual inspection only. It never promotes an asset automatically.",
        "",
        "For every texture, verify composition/geometry preservation, absence of invented objects or symbols, material plausibility, and any texture-specific attention items below.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['id']}",
                "",
                f"- [Comparison sheet]({row['comparison']['path']})",
            ]
        )
        if row.get("tile_preview"):
            lines.append(f"- [Repeated tile preview]({row['tile_preview']['path']})")
        lines.append(
            "- Review attention: "
            + (", ".join(row.get("attention", [])) or "general visual fidelity")
        )
        lines.extend(
            [
                "- [ ] Composition and authored geometry are preserved.",
                "- [ ] No new objects, symbols, lettering, openings or decorative motifs were invented.",
                "- [ ] Material/detail reconstruction is plausible at gameplay viewing distance.",
                "- [ ] Alpha/mask boundaries remain visually correct where applicable.",
            ]
        )
        if row.get("tile_preview"):
            lines.append("- [ ] Repeated U/V sampling shows no unacceptable seam or edge discontinuity.")
        lines.append("")

    return "\n".join(lines)


def build_review_pack(
    mode: str,
    review_queue: dict,
    sampling: dict,
    source_dir: Path,
    enhanced_dir: Path,
    restored_dir: Path,
    recreated_dir: Path,
    out_dir: Path,
    cell: int = 320,
) -> dict:
    if mode not in {"restored", "recreated"}:
        raise ValueError(f"unsupported mode: {mode}")

    sampling_by_id = sampling_index(sampling)
    rows = []
    missing = []

    for review in review_queue.get("rows", []):
        if not isinstance(review, dict) or not review.get("id"):
            continue
        texture_id = str(review["id"])
        source = source_dir / f"{texture_id}.png"
        candidate = candidate_path(mode, texture_id, restored_dir, recreated_dir)
        if not source.is_file():
            missing.append(str(source))
            continue
        if not candidate.is_file():
            missing.append(str(candidate))
            continue

        comparison = out_dir / "comparisons" / f"{texture_id}.png"
        variants = [
            ("Nearest 4x", enhanced_dir / texture_id / "nearest_x4.png"),
            ("Bicubic 4x", enhanced_dir / texture_id / "bicubic_x4.png"),
            ("Lanczos 4x", enhanced_dir / texture_id / "lanczos_x4.png"),
            (
                "AI Restored" if mode == "restored" else "AI Recreated",
                candidate,
            ),
        ]
        make_sheet(texture_id, source, variants, comparison, cell)

        sampling_row = sampling_by_id.get(texture_id, {})
        repeated = bool(sampling_row.get("repeat_sampling_observed"))
        tile = None
        if repeated:
            tile = out_dir / "tiles" / f"{texture_id}_3x3.png"
            tile_preview(candidate, tile, 3, 3)

        rows.append(
            {
                "id": texture_id,
                "mode": mode,
                "review_state": review.get("review_state"),
                "attention": list(review.get("attention", [])),
                "source": file_record(source),
                "candidate": file_record(candidate),
                "comparison": file_record(comparison),
                "tile_preview": file_record(tile) if tile else None,
                "repeat_axes": list(sampling_row.get("repeat_axes", [])),
            }
        )

    if missing:
        raise FileNotFoundError(
            "review pack inputs are incomplete: " + "; ".join(missing)
        )

    rows.sort(key=lambda row: row["id"])
    return {
        "schema": "openazrael.texture_lab.visual_review_pack.v1",
        "status": "READY_FOR_MANUAL_REVIEW",
        "mode": mode,
        "automatic_promotion": False,
        "texture_count": len(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fingerprinted visual-review pack for one Texture Lab AI stage."
    )
    parser.add_argument("mode", choices=["restored", "recreated"])
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument(
        "--sampling",
        type=Path,
        default=ROOT / "data/texture_lab/rt_poc_01_sampling_review.json",
    )
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--enhanced-dir", type=Path, default=ROOT / "assets/textures/enhanced")
    parser.add_argument("--restored-dir", type=Path, default=ROOT / "assets/textures/ai_restored")
    parser.add_argument("--recreated-dir", type=Path, default=ROOT / "assets/textures/ai_recreated")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--cell", type=int, default=320)
    args = parser.parse_args()

    review_queue = load_json(args.review_queue)
    sampling = load_json(args.sampling)
    pack = build_review_pack(
        args.mode,
        review_queue,
        sampling,
        args.source_dir,
        args.enhanced_dir,
        args.restored_dir,
        args.recreated_dir,
        args.out_dir,
        args.cell,
    )
    write_json(args.manifest, pack)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(args.mode, pack["rows"]), encoding="utf-8")

    print(
        f"PASS visual_review_pack mode={args.mode} textures={pack['texture_count']} "
        f"manifest={args.manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
