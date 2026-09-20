#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

from common import ROOT
from oa_tex_manual_review import build_template
from oa_tex_stage_gate import DEFAULT_RUN_ROOT, evidence_snapshot, preset_record


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def href(path: Path, output: Path) -> str:
    return Path(os.path.relpath(path.resolve(), output.parent.resolve())).as_posix()


def image_block(label: str, record: dict | None, output: Path) -> str:
    if not isinstance(record, dict):
        return ""
    path = Path(str(record.get("path", "")))
    if not path.is_file():
        return ""
    src = html.escape(href(path, output), quote=True)
    digest = html.escape(str(record.get("sha256", "")))
    return (
        '<figure class="evidence">'
        f'<figcaption>{html.escape(label)}</figcaption>'
        f'<a href="{src}"><img src="{src}" alt="{html.escape(label)}"></a>'
        f'<small>SHA-256 {digest}</small>'
        "</figure>"
    )


def render_handoff(
    preset: str,
    evidence: dict,
    manual_template: dict,
    review_pack: dict,
    output: Path,
) -> str:
    pack_by_id = {
        str(row["id"]): row
        for row in review_pack.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    }

    sections = []
    for review in manual_template.get("rows", []):
        texture_id = str(review["id"])
        pack = pack_by_id.get(texture_id, {})
        checks = "".join(
            f"<li>☐ {html.escape(str(name))}</li>"
            for name in review.get("required_checks", [])
        )
        attention = "".join(
            f"<li>{html.escape(str(value))}</li>"
            for value in review.get("attention", [])
        ) or "<li>general visual fidelity</li>"
        visuals = "".join(
            [
                image_block("Full comparison", pack.get("comparison"), output),
                image_block(
                    "Detail comparison",
                    pack.get("detail_comparison"),
                    output,
                ),
                image_block(
                    "Alpha evidence",
                    pack.get("alpha_preview"),
                    output,
                ),
                image_block("Repeat tile preview", pack.get("tile_preview"), output),
            ]
        )
        candidate = pack.get("candidate")
        candidate_path = (
            href(Path(str(candidate.get("path"))), output)
            if isinstance(candidate, dict)
            and Path(str(candidate.get("path", ""))).is_file()
            else None
        )
        candidate_line = (
            f'<p><strong>Candidate:</strong> '
            f'<a href="{html.escape(candidate_path, quote=True)}">'
            f'{html.escape(candidate_path)}</a></p>'
            if candidate_path
            else ""
        )

        sections.append(
            f"""
<section>
  <h2>{html.escape(texture_id)}</h2>
  {candidate_line}
  <div class="visuals">{visuals}</div>
  <div class="columns">
    <div>
      <h3>Review attention</h3>
      <ul>{attention}</ul>
    </div>
    <div>
      <h3>Required manual checks</h3>
      <ul class="checks">{checks}</ul>
    </div>
  </div>
</section>
"""
        )

    run_instance = ""
    plan = evidence.get("plan")
    if isinstance(plan, dict):
        plan_path = Path(str(plan.get("path", "")))
        if plan_path.is_file():
            plan_payload = load_json(plan_path)
            run_instance = str(plan_payload.get("run_instance_id", ""))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenAzrael Texture Lab review — {html.escape(preset)}</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; max-width: 1500px; }}
header {{ border-bottom: 1px solid #777; margin-bottom: 2rem; }}
.notice {{ padding: 1rem; border: 2px solid currentColor; font-weight: 700; }}
.visuals {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(300px,1fr)); gap: 1rem; }}
.evidence {{ margin: 0; }}
.evidence img {{ width: 100%; height: auto; border: 1px solid #777; }}
.evidence small {{ display: block; overflow-wrap: anywhere; opacity: .75; }}
.columns {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(280px,1fr)); gap: 1rem; }}
.checks {{ list-style: none; padding-left: 0; }}
section {{ margin: 2.5rem 0; padding-top: 1rem; border-top: 1px solid #555; }}
code {{ overflow-wrap: anywhere; }}
</style>
</head>
<body>
<header>
  <h1>OpenAzrael Texture Lab — {html.escape(preset)}</h1>
  <p class="notice">OBSERVATIONAL REVIEW HANDOFF — this page never approves or promotes a texture.</p>
  <p><strong>Stage evidence:</strong> {html.escape(str(evidence.get("status")))}</p>
  <p><strong>Run instance:</strong> <code>{html.escape(run_instance or "unknown")}</code></p>
  <p><strong>Godot review:</strong> launch <code>godot --path . res://tools/texture_lab/godot/texture_lab.tscn</code>, select REVIEW with <kbd>O</kbd>, then toggle it with <kbd>P</kbd>.</p>
  <p>After visual inspection, initialize/record the structured manual review with <code>oa_tex_manual_review.py</code>. Do not infer approval from this HTML page.</p>
</header>
{''.join(sections)}
</body>
</html>
"""


def build_handoff(
    preset: str,
    run_root: Path,
    output: Path,
) -> dict:
    evidence = evidence_snapshot(preset, run_root)
    if evidence.get("status") != "PASS":
        raise SystemExit(
            "review handoff requires complete current stage evidence; "
            f"status={evidence.get('status')}"
        )

    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_root / preset
    pack_path = run_dir / f"ai_{mode}_review_pack.json"
    if not pack_path.is_file():
        raise SystemExit(f"review pack missing: {pack_path}")

    manual_template = build_template(preset, run_root)
    review_pack = load_json(pack_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_handoff(
            preset,
            evidence,
            manual_template,
            review_pack,
            output,
        ),
        encoding="utf-8",
    )
    return {
        "schema": "openazrael.texture_lab.review_handoff.v1",
        "preset": preset,
        "mode": mode,
        "status": "READY_FOR_HUMAN_REVIEW",
        "automatic_approval": False,
        "output": str(output),
        "texture_count": len(manual_template.get("rows", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local self-contained HTML handoff for human Texture Lab "
            "review. This is a convenience surface, never approval evidence."
        )
    )
    parser.add_argument("preset")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out = args.out or args.run_root / args.preset / "review_handoff.html"
    result = build_handoff(args.preset, args.run_root, out)
    print(
        f"PASS review_handoff preset={args.preset} "
        f"textures={result['texture_count']} output={out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
