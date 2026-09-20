#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json

EXPECTED_MODES = {
    "opaque",
    "palette_colorkey",
    "true_alpha",
    "ambiguous",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_transparency_audit(
    manifest: dict,
    expected_count: int = 86,
) -> dict:
    rows = [
        row
        for row in manifest.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    ]
    ids = [str(row["id"]) for row in rows]
    unique_ids = len(ids) == len(set(ids))
    count_ok = expected_count < 0 or len(rows) == expected_count

    mode_counts = {mode: 0 for mode in sorted(EXPECTED_MODES)}
    unknown = []
    ambiguous = []
    policy_violations = []

    for row in rows:
        texture_id = str(row["id"])
        mode = str(row.get("transparency_mode", ""))
        if mode in mode_counts:
            mode_counts[mode] += 1
        else:
            unknown.append(
                {
                    "id": texture_id,
                    "mode": mode or None,
                }
            )
            continue

        review_required = row.get("transparency_review_required")
        colorkey_candidate = bool(row.get("legacy_colorkey_candidate"))

        if mode == "ambiguous":
            ambiguous.append(
                {
                    "id": texture_id,
                    "file": row.get("file"),
                    "reason": row.get("transparency_reason"),
                    "legacy_magenta_pixels": row.get(
                        "legacy_magenta_pixels"
                    ),
                    "legacy_magenta_fraction": row.get(
                        "legacy_magenta_fraction"
                    ),
                    "has_alpha": row.get("has_alpha"),
                    "transparent_pixels": row.get(
                        "transparent_pixels"
                    ),
                    "partial_alpha_pixels": row.get(
                        "partial_alpha_pixels"
                    ),
                    "automatic_colorkey_applied": colorkey_candidate,
                }
            )
            if review_required is not True or colorkey_candidate:
                policy_violations.append(
                    {
                        "id": texture_id,
                        "reason": (
                            "ambiguous_must_require_manual_review_and_must_not_"
                            "auto_colorkey"
                        ),
                    }
                )

        if mode == "palette_colorkey" and not colorkey_candidate:
            policy_violations.append(
                {
                    "id": texture_id,
                    "reason": "palette_colorkey_without_colorkey_candidate",
                }
            )

    manifest_schema_ok = (
        manifest.get("schema")
        == "openazrael.texture_lab.classic_manifest.v2"
    )
    source_kind_ok = (
        manifest.get("source_kind")
        == "local_excluded_commercial_derived"
    )
    structural_ok = (
        manifest_schema_ok
        and source_kind_ok
        and count_ok
        and unique_ids
        and not unknown
        and not policy_violations
    )
    review_required = len(ambiguous) > 0

    return {
        "schema": "openazrael.texture_lab.transparency_audit.v1",
        "status": (
            "HOLD"
            if not structural_ok
            else ("REVIEW_REQUIRED" if review_required else "PASS")
        ),
        "manifest_schema_ok": manifest_schema_ok,
        "source_kind_ok": source_kind_ok,
        "expected_texture_count": expected_count,
        "texture_count": len(rows),
        "count_ok": count_ok,
        "unique_ids": unique_ids,
        "mode_counts": mode_counts,
        "unknown_mode_count": len(unknown),
        "unknown_modes": unknown,
        "manual_review_required_count": len(ambiguous),
        "manual_review_queue": ambiguous,
        "policy_violation_count": len(policy_violations),
        "policy_violations": policy_violations,
        "safe_for_deterministic_baseline": structural_ok,
        "ready_for_corpus_expansion": structural_ok and not review_required,
        "automatic_transparency_decision": False,
        "notes": [
            (
                "Ambiguous transparency evidence is not a technical failure. "
                "It remains non-destructive and requires manual review."
            ),
            (
                "Corpus expansion is held until every ambiguous case is "
                "explicitly resolved outside this observational audit."
            ),
        ],
    }


def markdown_report(audit: dict) -> str:
    counts = audit.get("mode_counts", {})
    lines = [
        "# OpenAzrael Texture Lab — Full Corpus Transparency Audit",
        "",
        (
            f"Status: **{audit.get('status')}** · textures "
            f"{audit.get('texture_count')}/{audit.get('expected_texture_count')}"
        ),
        "",
        (
            "This report is observational. It never converts an ambiguous "
            "texture automatically."
        ),
        "",
        "## Census",
        "",
        "| Mode | Count |",
        "|---|---:|",
    ]
    for mode in sorted(EXPECTED_MODES):
        lines.append(f"| {mode} | {int(counts.get(mode, 0))} |")

    lines.extend(
        [
            "",
            "## Manual transparency review queue",
            "",
            "| Texture | Reason | Magenta pixels | Alpha | Auto color-key |",
            "|---|---|---:|---|---|",
        ]
    )
    queue = audit.get("manual_review_queue", [])
    if not queue:
        lines.append("| — | none | 0 | — | false |")
    else:
        for row in queue:
            alpha = (
                f"transparent={row.get('transparent_pixels')}, "
                f"partial={row.get('partial_alpha_pixels')}"
            )
            lines.append(
                f"| {row.get('id')} | {row.get('reason')} | "
                f"{row.get('legacy_magenta_pixels')} | {alpha} | "
                f"{str(bool(row.get('automatic_colorkey_applied'))).lower()} |"
            )

    lines.extend(
        [
            "",
            (
                "Safe for deterministic baseline: "
                f"**{audit.get('safe_for_deterministic_baseline')}**"
            ),
            (
                "Ready for corpus expansion: "
                f"**{audit.get('ready_for_corpus_expansion')}**"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the full Classic manifest transparency census and emit a "
            "non-destructive manual-review queue."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/texture_lab/classic_manifest.json",
    )
    parser.add_argument("--expect-count", type=int, default=86)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / ".local/texture_lab/transparency_audit.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / ".local/texture_lab/transparency_audit.md",
    )
    args = parser.parse_args()

    if not args.manifest.is_file():
        raise SystemExit(f"classic manifest not found: {args.manifest}")

    audit = build_transparency_audit(
        load_json(args.manifest),
        args.expect_count,
    )
    write_json(args.out_json, audit)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown_report(audit), encoding="utf-8")

    print(
        f"{audit['status']} transparency_audit "
        f"textures={audit['texture_count']} "
        f"ambiguous={audit['manual_review_required_count']} "
        f"json={args.out_json} md={args.out_md}"
    )
    return 1 if audit["status"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
