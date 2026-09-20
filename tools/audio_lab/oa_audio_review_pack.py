#!/usr/bin/env python3
"""Generate a deterministic AL-POC-01 human review pack from inventory and mapping evidence."""
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.audio_lab.common import ensure_output_outside_source

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _priority(asset: dict, mapping: dict, broken_assets: set[str]) -> tuple[str, str, list[str]]:
    name = str(asset.get("filename", ""))
    issues = asset.get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    info = [i for i in issues if i.get("severity") == "info"]
    if str(mapping.get("mapping_status", "")) == "MAPPED":
        info = [i for i in info if i.get("code") != "AUD010_NO_RUNTIME_REFERENCE"]
    reasons: list[str] = []

    if name.casefold() in broken_assets:
        reasons.append("BROKEN_RUNTIME_REFERENCE")
    reasons.extend(str(i.get("code", "")) for i in errors)
    if reasons:
        return "P0", "BLOCKER", sorted(set(reasons))

    status = str(mapping.get("mapping_status", ""))
    if status == "UNEXPECTED_ORPHAN":
        reasons.append("UNEXPECTED_ORPHAN")
    reasons.extend(str(i.get("code", "")) for i in warnings)
    if reasons:
        return "P1", "HIGH_REVIEW", sorted(set(reasons))

    if status == "EXPECTED_UNMAPPED":
        reasons.append("EXPECTED_UNMAPPED")
        return "P2", "MAPPING_REVIEW", reasons

    if info:
        reasons.extend(str(i.get("code", "")) for i in info)
        return "P3", "INFO_REVIEW", sorted(set(reasons))

    return "P4", "CLEAN", []

def build_review_pack(manifest: dict, reference_report: dict) -> dict:
    mapping_by_name = {
        str(row.get("filename", "")).casefold(): row
        for row in reference_report.get("assets", [])
    }
    broken_assets = {
        str(row.get("asset", "")).casefold()
        for row in reference_report.get("broken_references", [])
        if str(row.get("asset", ""))
    }

    rows = []
    for asset in manifest.get("assets", []):
        name = str(asset.get("filename", ""))
        mapping = mapping_by_name.get(name.casefold(), {})
        priority, review_class, reasons = _priority(asset, mapping, broken_assets)
        analysis = asset.get("analysis", {})
        rows.append({
            "priority": priority,
            "review_class": review_class,
            "reasons": reasons,
            "path": asset.get("path"),
            "filename": name,
            "sha256": asset.get("sha256"),
            "detected_format": asset.get("detected_format"),
            "duration_seconds": analysis.get("duration_seconds"),
            "channels": analysis.get("channels"),
            "sample_rate": analysis.get("sample_rate"),
            "sample_width_bits": analysis.get("sample_width_bits"),
            "peak": analysis.get("peak"),
            "rms": analysis.get("rms"),
            "leading_silence_seconds": analysis.get("leading_silence_seconds"),
            "trailing_silence_seconds": analysis.get("trailing_silence_seconds"),
            "waveform_bins": analysis.get("waveform_bins", []),
            "mapping_status": mapping.get("mapping_status", "UNKNOWN"),
            "mapping_types": mapping.get("mapping_types", []),
            "mappings": mapping.get("mappings", []),
            "diagnostic_references": mapping.get("diagnostic_references", []),
            "documentation_references": mapping.get("documentation_references", []),
            "other_references": mapping.get("other_references", []),
            "qa_issues": asset.get("issues", []),
        })

    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    rows.sort(key=lambda r: (rank.get(r["priority"], 99), str(r["path"]).casefold()))
    counts = {p: sum(r["priority"] == p for r in rows) for p in rank}
    return {
        "schema": "openazrael.audio_lab.review_pack",
        "version": 1,
        "status": "BLOCKED" if counts["P0"] else "READY_FOR_REVIEW",
        "policy": {
            "P0": "broken reference or error-severity source/metadata finding",
            "P1": "unexpected orphan or warning-severity audio finding",
            "P2": "expected source audio without recovered production runtime mapping",
            "P3": "informational QA finding",
            "P4": "mapped/clean under current evidence",
        },
        "summary": {
            "asset_count": len(rows),
            "priority_counts": counts,
            "review_required": sum(counts[p] for p in ("P0", "P1", "P2", "P3")),
            "clean": counts["P4"],
        },
        "assets": rows,
    }

def _waveform_svg(bins: list[list[float]]) -> str:
    if not bins:
        return '<span class="muted">n/a</span>'
    width, height = 220, 54
    mid = height / 2
    step = width / max(1, len(bins))
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" aria-label="waveform">']
    for i, pair in enumerate(bins):
        lo, hi = pair
        x = i * step + step / 2
        y1 = mid - float(hi) * (mid - 2)
        y2 = mid - float(lo) * (mid - 2)
        parts.append(f'<line x1="{x:.2f}" y1="{y1:.2f}" x2="{x:.2f}" y2="{y2:.2f}" stroke="currentColor" stroke-width="{max(1.0, step*0.6):.2f}"/>')
    parts.append("</svg>")
    return "".join(parts)

def write_html(path: Path, pack: dict, source_root: Path | None = None) -> None:
    rows = []
    root = source_root.resolve() if source_root else None
    for row in pack.get("assets", []):
        reasons = ", ".join(row.get("reasons", [])) or "—"
        mapping = ", ".join(row.get("mapping_types", [])) or row.get("mapping_status", "UNKNOWN")
        audio = "—"
        if root is not None:
            candidate = (root / str(row.get("path", ""))).resolve()
            try:
                candidate.relative_to(root)
                audio = f"<audio controls preload='none' src='{html.escape(candidate.as_uri(), quote=True)}'></audio>"
            except ValueError:
                audio = "invalid path"
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(str(row['priority']))}</strong><br>{html.escape(str(row['review_class']))}</td>"
            f"<td><strong>{html.escape(str(row['filename']))}</strong><br><code>{html.escape(str(row['path']))}</code></td>"
            f"<td>{row.get('channels') or '—'} / {row.get('sample_rate') or '—'} Hz / {row.get('sample_width_bits') or '—'} bit<br>{row.get('duration_seconds') if row.get('duration_seconds') is not None else '—'} s</td>"
            f"<td>{_waveform_svg(row.get('waveform_bins') or [])}</td>"
            f"<td>{html.escape(mapping)}</td>"
            f"<td>{html.escape(reasons)}</td>"
            f"<td>{audio}</td>"
            "</tr>"
        )

    counts = pack.get("summary", {}).get("priority_counts", {})
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>OpenAzrael Audio Lab Review Pack</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;line-height:1.35}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #bbb;padding:8px;vertical-align:top}} th{{text-align:left}} code{{font-size:.85em}}
.muted{{opacity:.6}} audio{{width:220px}} svg{{max-width:220px}}
</style></head><body>
<h1>OpenAzrael Audio Lab — AL-POC-01 Review Pack</h1>
<p>Status: <strong>{html.escape(str(pack.get('status')))}</strong> · P0 {counts.get('P0',0)} · P1 {counts.get('P1',0)} · P2 {counts.get('P2',0)} · P3 {counts.get('P3',0)} · Clean {counts.get('P4',0)}</p>
<table><thead><tr><th>Priority</th><th>Asset</th><th>Audio</th><th>Waveform</th><th>Mapping</th><th>Reasons</th><th>Preview</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></body></html>"""
    path.write_text(doc, encoding="utf-8")

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("reference_report", type=Path)
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--source-root", type=Path)
    args = ap.parse_args(argv)

    out_candidate = args.output_dir or args.manifest.parent
    if args.source_root is not None:
        try:
            out = ensure_output_outside_source(args.source_root, out_candidate)
        except ValueError as exc:
            ap.error(str(exc))
    else:
        out = out_candidate.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pack = build_review_pack(load_json(args.manifest), load_json(args.reference_report))
    json_path = out / "audio_review_pack.json"
    html_path = out / "audio_review_pack.html"
    json_path.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_html(html_path, pack, args.source_root)
    print(json.dumps({
        "status": pack["status"],
        **pack["summary"],
        "json": str(json_path),
        "html": str(html_path),
    }, indent=2))
    return 2 if pack["status"] == "BLOCKED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
