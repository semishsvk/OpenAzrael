#!/usr/bin/env python3
"""Build a deterministic, source-safe OpenAzrael audio inventory and QA report."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import csv
import html
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.audio_lab import TOOL_VERSION, SCHEMA_VERSION
    from tools.audio_lab.common import (
        AUDIO_EXTENSIONS, detect_format, iter_audio_files, parse_wave,
        scan_references, sha256_file, tree_digest,
    )
else:
    from . import TOOL_VERSION, SCHEMA_VERSION
    from .common import (
        AUDIO_EXTENSIONS, detect_format, iter_audio_files, parse_wave,
        scan_references, sha256_file, tree_digest,
    )

ROOT = Path(__file__).resolve().parents[2]

def load_fingerprints(path: Path | None) -> dict[str, dict]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for entry in data.get("entries", []):
        raw_path = str(entry.get("path", ""))
        if "audio" not in raw_path.casefold():
            continue
        name = Path(raw_path).name
        if name:
            out[name.casefold()] = {
                "filename": name,
                "sha256": str(entry.get("sha256", "")),
                "source_path": raw_path,
            }
    return out

def issue(code: str, severity: str, message: str) -> dict:
    return {"code": code, "severity": severity, "message": message}

def build_record(path: Path, source_root: Path, expected: dict | None, refs: list[str]) -> dict:
    rel = path.relative_to(source_root).as_posix()
    digest = sha256_file(path)
    fmt = detect_format(path)
    analysis = parse_wave(path) if fmt == "WAVE" else {
        "container": fmt,
        "valid": True,
        "parse_error": None,
        "waveform_bins": [],
    }
    issues: list[dict] = []
    if path.stat().st_size == 0:
        issues.append(issue("AUD002_ZERO_LENGTH", "error", "Audio file is empty."))
    if fmt == "WAVE":
        if not analysis.get("valid"):
            issues.append(issue("AUD001_MALFORMED_CONTAINER", "error", str(analysis.get("parse_error") or "WAV parse failed")))
        else:
            if analysis.get("riff_size_matches") is False:
                issues.append(issue("AUD003_RIFF_SIZE_MISMATCH", "warning", "RIFF declared size differs from physical file size."))
            if analysis.get("terminal_pad_missing"):
                issues.append(issue("AUD003_TERMINAL_PAD_MISSING", "warning", "Odd-size terminal RIFF chunk has no alignment pad; PCM payload remains readable."))
            if analysis.get("audio_format") != 1:
                issues.append(issue("AUD004_UNSUPPORTED_WAV_CODEC", "warning", f"WAV format code {analysis.get('audio_format')} is not PCM."))
            lead = analysis.get("leading_silence_seconds")
            trail = analysis.get("trailing_silence_seconds")
            duration = analysis.get("duration_seconds") or 0.0
            if duration > 0.75 and ((lead or 0) > 0.5 or (trail or 0) > 0.5):
                issues.append(issue("AUD005_SUSPICIOUS_SILENCE", "info", "More than 0.5 s of leading or trailing near-silence detected."))
            clipped_fraction = analysis.get("clipped_fraction")
            if clipped_fraction is not None and clipped_fraction > 0.01:
                issues.append(issue("AUD006_CLIPPING", "warning", "More than 1% of decoded PCM samples hit digital extrema."))
    if expected:
        if digest != expected.get("sha256"):
            issues.append(issue("AUD007_FINGERPRINT_MISMATCH", "error", "SHA-256 does not match the committed source fingerprint."))
    if not refs:
        issues.append(issue("AUD010_NO_REPO_REFERENCE", "info", "No literal filename reference found in scanned repository text."))

    return {
        "path": rel,
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256": digest,
        "detected_format": fmt,
        "fingerprint": {
            "expected": bool(expected),
            "expected_sha256": expected.get("sha256") if expected else None,
            "match": (digest == expected.get("sha256")) if expected else None,
            "source_path": expected.get("source_path") if expected else None,
        },
        "references": refs,
        "analysis": analysis,
        "issues": issues,
    }

def qa_summary(records: list[dict], expected: dict[str, dict]) -> dict:
    by_code: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    for rec in records:
        for item in rec["issues"]:
            by_code[item["code"]] += 1
            by_severity[item["severity"]] += 1

    discovered = {rec["filename"].casefold() for rec in records}
    missing_expected = [
        expected[key]["filename"] for key in sorted(expected)
        if key not in discovered
    ]
    for _ in missing_expected:
        by_code["AUD009_MISSING_EXPECTED_ASSET"] += 1
        by_severity["error"] += 1

    hashes: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        hashes[rec["sha256"]].append(rec["path"])
    duplicates = [
        {"sha256": digest, "paths": sorted(paths, key=str.casefold)}
        for digest, paths in sorted(hashes.items())
        if len(paths) > 1
    ]
    if duplicates:
        by_code["AUD011_DUPLICATE_CONTENT"] += len(duplicates)
        by_severity["info"] += len(duplicates)

    return {
        "status": "PASS" if by_severity.get("error", 0) == 0 else "FAIL",
        "asset_count": len(records),
        "expected_fingerprint_count": len(expected),
        "missing_expected_assets": missing_expected,
        "duplicate_content_groups": duplicates,
        "issue_counts_by_severity": dict(sorted(by_severity.items())),
        "issue_counts_by_code": dict(sorted(by_code.items())),
    }

def waveform_svg(bins: list[list[float]]) -> str:
    if not bins:
        return '<span class="muted">n/a</span>'
    width, height = 240, 56
    mid = height / 2
    step = width / max(1, len(bins))
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" aria-label="waveform">']
    for i, pair in enumerate(bins):
        lo, hi = pair
        x = i * step + step / 2
        y1 = mid - hi * (mid - 2)
        y2 = mid - lo * (mid - 2)
        parts.append(f'<line x1="{x:.2f}" y1="{y1:.2f}" x2="{x:.2f}" y2="{y2:.2f}" stroke="currentColor" stroke-width="{max(1.0, step*0.65):.2f}"/>')
    parts.append("</svg>")
    return "".join(parts)

def write_html(path: Path, records: list[dict], summary: dict, source_root: Path) -> None:
    rows = []
    for rec in records:
        a = rec["analysis"]
        issues = ", ".join(i["code"] for i in rec["issues"]) or "—"
        src = (source_root / rec["path"]).resolve().as_uri()
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(rec['filename'])}</strong><br><code>{html.escape(rec['path'])}</code></td>"
            f"<td>{html.escape(rec['detected_format'])}</td>"
            f"<td>{a.get('channels') or '—'} / {a.get('sample_rate') or '—'} Hz / {a.get('sample_width_bits') or '—'} bit</td>"
            f"<td>{a.get('duration_seconds') if a.get('duration_seconds') is not None else '—'}</td>"
            f"<td>{waveform_svg(a.get('waveform_bins') or [])}</td>"
            f"<td><audio controls preload='none' src='{html.escape(src, quote=True)}'></audio></td>"
            f"<td>{html.escape(issues)}</td>"
            "</tr>"
        )
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>OpenAzrael Audio Lab AL-POC-01</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;line-height:1.35}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #bbb;padding:8px;vertical-align:top}} th{{text-align:left}} code{{font-size:.85em}}
.muted{{opacity:.6}} svg{{max-width:240px}} audio{{width:240px}}
</style></head><body>
<h1>OpenAzrael Audio Lab AL-POC-01</h1>
<p>Status: <strong>{html.escape(summary['status'])}</strong> · Assets: {summary['asset_count']} · Errors: {summary['issue_counts_by_severity'].get('error',0)} · Warnings: {summary['issue_counts_by_severity'].get('warning',0)}</p>
<table><thead><tr><th>Asset</th><th>Format</th><th>PCM</th><th>Duration</th><th>Waveform</th><th>Preview</th><th>QA</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></body></html>"""
    path.write_text(doc, encoding="utf-8")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path, help="Directory containing source audio to inventory; never modified.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".tmp/audio_lab/al_poc_01")
    parser.add_argument("--reference-root", type=Path, default=ROOT, help="Repository tree used only for literal reference discovery.")
    parser.add_argument("--fingerprints", type=Path, default=ROOT / "data/backup/source_fingerprints.json")
    parser.add_argument("--extensions", nargs="*", default=sorted(AUDIO_EXTENSIONS))
    args = parser.parse_args(argv)

    source_root = args.source_root.resolve()
    if not source_root.is_dir():
        parser.error(f"source_root is not a directory: {source_root}")
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_files = iter_audio_files(source_root, args.extensions)
    expected = load_fingerprints(args.fingerprints)
    refs = scan_references(args.reference_root.resolve(), [p.name for p in audio_files])
    records = [
        build_record(path, source_root, expected.get(path.name.casefold()), refs.get(path.name, []))
        for path in audio_files
    ]

    summary = qa_summary(records, expected)
    manifest = {
        "schema": "openazrael.audio_lab.inventory",
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "source_label": source_root.name,
        "source_file_count": len(audio_files),
        "source_tree_sha256": tree_digest(source_root, audio_files),
        "extensions": sorted({e.lower() if e.startswith(".") else "." + e.lower() for e in args.extensions}),
        "fingerprints_loaded": len(expected),
        "qa": summary,
        "assets": records,
    }

    manifest_path = out_dir / "audio_manifest.json"
    qa_path = out_dir / "audio_qa_report.json"
    csv_path = out_dir / "audio_inventory.csv"
    html_path = out_dir / "audio_qa_report.html"

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    qa_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path","filename","sha256","format","channels","sample_rate","bits","duration_seconds","peak","rms","reference_count","issue_codes"])
        for rec in records:
            a = rec["analysis"]
            w.writerow([
                rec["path"], rec["filename"], rec["sha256"], rec["detected_format"],
                a.get("channels"), a.get("sample_rate"), a.get("sample_width_bits"), a.get("duration_seconds"),
                a.get("peak"), a.get("rms"), len(rec["references"]), ";".join(i["code"] for i in rec["issues"])
            ])
    write_html(html_path, records, summary, source_root)

    print(json.dumps({
        "status": summary["status"],
        "assets": len(records),
        "errors": summary["issue_counts_by_severity"].get("error", 0),
        "warnings": summary["issue_counts_by_severity"].get("warning", 0),
        "manifest": str(manifest_path),
        "qa": str(qa_path),
        "csv": str(csv_path),
        "html": str(html_path),
    }, indent=2))
    return 0 if summary["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
