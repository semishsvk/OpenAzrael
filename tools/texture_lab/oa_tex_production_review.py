#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

from common import ROOT, sha256_file, write_json
from oa_tex_compare import make_detail_sheet, make_sheet
from oa_tex_stage_gate import (
    DEFAULT_APPROVAL_ROOT,
    DEFAULT_MANUAL_REVIEW_ROOT,
    DEFAULT_RUN_ROOT,
    evidence_snapshot,
    validate_receipt,
)
from oa_tex_tile import tile_preview

SAMPLING = ROOT / "data/texture_lab/rt_poc_01_sampling_review.json"
DEFAULT_OUT_ROOT = ROOT / ".local/texture_lab/production_review"
DEFAULT_GODOT_PROFILE = (
    ROOT / ".local/texture_lab/runtime_manifests/production_review_current.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_record(path: Path) -> dict:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def current_candidate(
    preset: str,
    texture_id: str,
    run_root: Path,
) -> dict:
    evidence = evidence_snapshot(preset, run_root)
    if evidence.get("status") != "PASS":
        raise SystemExit(
            f"{preset}: current stage evidence is not PASS; "
            f"status={evidence.get('status')}"
        )
    row = next(
        (
            value
            for value in evidence.get("outputs", [])
            if isinstance(value, dict)
            and str(value.get("id")) == texture_id
        ),
        None,
    )
    if not isinstance(row, dict):
        raise SystemExit(
            f"{texture_id}: no current reviewed output in preset {preset}"
        )
    path = Path(str(row.get("path", "")))
    if not path.is_file():
        raise SystemExit(f"{texture_id}: reviewed candidate missing: {path}")
    current = file_record(path)
    if (
        current["sha256"] != row.get("sha256")
        or current["size_bytes"] != row.get("size_bytes")
    ):
        raise SystemExit(
            f"{texture_id}: candidate changed after stage evidence capture"
        )
    return {"id": texture_id, **current}


def sampling_row(texture_id: str) -> dict:
    payload = load_json(SAMPLING)
    for row in payload.get("textures", []):
        if isinstance(row, dict) and str(row.get("id")) == texture_id:
            return row
    return {}


def build_bundle(
    texture_id: str,
    source: Path,
    enhanced: Path,
    restored: Path,
    recreated: Path,
    out_dir: Path,
    restored_preset: str,
    recreated_preset: str,
    repeat_sampling: bool,
    cell: int = 360,
) -> dict:
    inputs = {
        "classic": source,
        "enhanced_lanczos": enhanced,
        "ai_restored": restored,
        "ai_recreated": recreated,
    }
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "production review inputs are incomplete: " + "; ".join(missing)
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    full = out_dir / "comparison_4way.png"
    detail = out_dir / "detail_4way.png"
    variants = [
        ("Enhanced Lanczos 4x", enhanced),
        ("AI Restored", restored),
        ("AI Recreated", recreated),
    ]
    make_sheet(texture_id, source, variants, full, cell)
    make_detail_sheet(texture_id, source, variants, detail, cell)

    restored_tile = None
    recreated_tile = None
    if repeat_sampling:
        restored_tile = out_dir / "ai_restored_3x3.png"
        recreated_tile = out_dir / "ai_recreated_3x3.png"
        tile_preview(restored, restored_tile, 3, 3)
        tile_preview(recreated, recreated_tile, 3, 3)

    return {
        "schema": "openazrael.texture_lab.production_review_bundle.v1",
        "status": "READY_FOR_MANUAL_PRODUCTION_REVIEW",
        "texture_id": texture_id,
        "automatic_selection": False,
        "automatic_quality_verdict": False,
        "restored_preset": restored_preset,
        "recreated_preset": recreated_preset,
        "inputs": {
            key: file_record(path)
            for key, path in inputs.items()
        },
        "visuals": {
            "comparison_4way": file_record(full),
            "detail_4way": file_record(detail),
            "restored_tile_3x3": (
                file_record(restored_tile) if restored_tile else None
            ),
            "recreated_tile_3x3": (
                file_record(recreated_tile) if recreated_tile else None
            ),
        },
        "review_questions": [
            "Which candidate preserves authored composition and geometry most faithfully?",
            "Which candidate improves material/readability at gameplay scale without inventing detail?",
            "Are original symbols, lettering, openings and decorative motifs preserved exactly?",
            "Does either candidate introduce ringing, plastic texture, false edges or hallucinated microdetail?",
            "For repeated textures, does either candidate worsen U/V seams relative to Classic?",
            "Does Enhanced Lanczos already preserve the source better than either AI candidate?",
        ],
        "allowed_manual_actions": [
            f"select {restored_preset}",
            f"select {recreated_preset}",
            "keep Classic fallback",
            "defer production decision",
        ],
    }


def res_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(
            f"production-review asset must remain inside project tree: {path}"
        ) from exc
    return "res://" + str(rel).replace("\\", "/")


def build_godot_review_manifest(bundle: dict) -> dict:
    inputs = bundle.get("inputs", {})
    texture_id = str(bundle.get("texture_id", ""))
    restored = inputs.get("ai_restored")
    recreated = inputs.get("ai_recreated")
    if (
        not texture_id
        or not isinstance(restored, dict)
        or not isinstance(recreated, dict)
    ):
        raise SystemExit("production-review bundle lacks Restored/Recreated inputs")

    def row(record: dict) -> dict:
        path = Path(str(record.get("path", "")))
        if not path.is_file():
            raise SystemExit(f"production-review candidate missing: {path}")
        return {
            "path": res_path(path),
            "sha256": str(record.get("sha256", "")),
            "size_bytes": int(record.get("size_bytes", -1)),
        }

    return {
        "schema": "openazrael.texture_lab.production_review_manifest.v1",
        "status": "READY_FOR_MANUAL_PRODUCTION_REVIEW",
        "automatic_selection": False,
        "export_allowed": False,
        "texture_count": 1,
        "textures": [
            {
                "id": texture_id,
                "restored": row(restored),
                "recreated": row(recreated),
            }
        ],
    }


def relative_href(path: Path, html_path: Path) -> str:
    return Path(
        os.path.relpath(path.resolve(), html_path.parent.resolve())
    ).as_posix()


def render_html(bundle: dict, html_path: Path) -> str:
    visuals = bundle["visuals"]
    figures = []
    for label, key in [
        ("4-way full comparison", "comparison_4way"),
        ("4-way detail comparison", "detail_4way"),
        ("AI Restored 3x3 repeat", "restored_tile_3x3"),
        ("AI Recreated 3x3 repeat", "recreated_tile_3x3"),
    ]:
        record = visuals.get(key)
        if not isinstance(record, dict):
            continue
        path = Path(str(record["path"]))
        href = html.escape(relative_href(path, html_path), quote=True)
        figures.append(
            "<figure>"
            f"<figcaption>{html.escape(label)}</figcaption>"
            f'<a href="{href}"><img src="{href}" alt="{html.escape(label)}"></a>'
            f"<small>SHA-256 {html.escape(str(record['sha256']))}</small>"
            "</figure>"
        )

    questions = "".join(
        f"<li>{html.escape(question)}</li>"
        for question in bundle["review_questions"]
    )
    actions = "".join(
        f"<li>{html.escape(action)}</li>"
        for action in bundle["allowed_manual_actions"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenAzrael production review — {html.escape(bundle['texture_id'])}</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: system-ui,sans-serif; max-width: 1600px; margin: 2rem; line-height: 1.45; }}
.notice {{ border: 2px solid currentColor; padding: 1rem; font-weight: 700; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:1rem; }}
figure {{ margin:0; }}
img {{ width:100%; height:auto; border:1px solid #777; }}
small {{ display:block; overflow-wrap:anywhere; opacity:.75; }}
</style>
</head>
<body>
<h1>OpenAzrael production review — {html.escape(bundle['texture_id'])}</h1>
<p class="notice">MANUAL DECISION ONLY — this bundle never selects, ranks or promotes a texture automatically.</p>
<p>Restored evidence: <code>{html.escape(bundle['restored_preset'])}</code><br>
Recreated evidence: <code>{html.escape(bundle['recreated_preset'])}</code></p>
<div class="grid">{''.join(figures)}</div>
<h2>Review questions</h2><ul>{questions}</ul>
<h2>Allowed manual outcomes</h2><ul>{actions}</ul>
<p>After deciding, use <code>oa_tex_production_selection.py select</code> with the chosen approved preset and a non-empty audit note, or keep/defer without writing a selection.</p>
</body>
</html>
"""


def build_from_approved_presets(
    texture_id: str,
    restored_preset: str,
    recreated_preset: str,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path,
    out_dir: Path,
    cell: int,
    current_profile: Path = DEFAULT_GODOT_PROFILE,
) -> dict:
    for preset in [restored_preset, recreated_preset]:
        receipt = validate_receipt(
            preset,
            run_root,
            approval_root,
            manual_review_root,
        )
        if receipt.get("status") != "PASS":
            raise SystemExit(
                f"{preset}: current stage approval required for production "
                f"review; status={receipt.get('status')}"
            )

    restored_record = current_candidate(
        restored_preset,
        texture_id,
        run_root,
    )
    recreated_record = current_candidate(
        recreated_preset,
        texture_id,
        run_root,
    )
    source = ROOT / "assets/textures/classic" / f"{texture_id}.png"
    enhanced = (
        ROOT
        / "assets/textures/enhanced"
        / texture_id
        / "lanczos_x4.png"
    )
    sampling = sampling_row(texture_id)
    repeat_sampling = bool(sampling.get("repeat_sampling_observed"))

    bundle = build_bundle(
        texture_id,
        source,
        enhanced,
        Path(restored_record["path"]),
        Path(recreated_record["path"]),
        out_dir,
        restored_preset,
        recreated_preset,
        repeat_sampling,
        cell,
    )
    bundle["approvals"] = {
        "restored": file_record(
            approval_root / f"{restored_preset}.json"
        ),
        "recreated": file_record(
            approval_root / f"{recreated_preset}.json"
        ),
    }
    bundle["candidate_evidence"] = {
        "restored": restored_record,
        "recreated": recreated_record,
    }

    godot_profile = build_godot_review_manifest(bundle)
    current_profile.parent.mkdir(parents=True, exist_ok=True)
    write_json(current_profile, godot_profile)
    bundle["godot_review_profile"] = {
        "path": str(current_profile),
        "replaceable_convenience_pointer": True,
        "schema": godot_profile["schema"],
    }

    manifest = out_dir / "production_review.json"
    html_path = out_dir / "production_review.html"
    write_json(manifest, bundle)
    html_path.write_text(
        render_html(bundle, html_path),
        encoding="utf-8",
    )
    return {
        **bundle,
        "manifest_path": str(manifest),
        "html_path": str(html_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a manual four-tier production-review bundle from current "
            "approved Restored and Recreated stage evidence."
        )
    )
    parser.add_argument("texture_id")
    parser.add_argument(
        "--restored-preset",
        default="restored_smoke_1",
    )
    parser.add_argument(
        "--recreated-preset",
        default="recreated_smoke_1",
    )
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--approval-root",
        type=Path,
        default=DEFAULT_APPROVAL_ROOT,
    )
    parser.add_argument(
        "--manual-review-root",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_ROOT,
    )
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--current-profile",
        type=Path,
        default=DEFAULT_GODOT_PROFILE,
        help=(
            "Replaceable editor-only Godot pointer for direct Restored vs "
            "Recreated A/B review."
        ),
    )
    parser.add_argument("--cell", type=int, default=360)
    args = parser.parse_args()

    out_dir = (
        args.out_dir
        or DEFAULT_OUT_ROOT
        / args.texture_id
        / f"{args.restored_preset}__{args.recreated_preset}"
    )
    result = build_from_approved_presets(
        args.texture_id,
        args.restored_preset,
        args.recreated_preset,
        args.run_root,
        args.approval_root,
        args.manual_review_root,
        out_dir,
        args.cell,
        args.current_profile,
    )
    print(
        "PASS production_review "
        f"texture={args.texture_id} html={result['html_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
