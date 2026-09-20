#!/usr/bin/env python3
"""Verify a canonical OpenAzrael source-audio corpus against recovered IR evidence."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.audio_lab.common import (
    ensure_output_outside_source,
    iter_audio_files,
    parse_wave,
    sha256_file,
    tree_digest,
)

ROOT = Path(__file__).resolve().parents[2]

def verify_corpus(source_root: Path, legacy_ir: dict) -> dict:
    source_root = source_root.resolve()
    files = iter_audio_files(source_root, {".wav", ".wave"})
    expected_rows = {
        str(row.get("filename", "")).casefold(): row
        for row in legacy_ir.get("audio", {}).get("sounds", [])
        if str(row.get("filename", "")).strip()
    }
    actual_by_name = {p.name.casefold(): p for p in files}

    missing = [
        expected_rows[k]["filename"] for k in sorted(expected_rows)
        if k not in actual_by_name
    ]
    extra = [
        actual_by_name[k].name for k in sorted(actual_by_name)
        if k not in expected_rows
    ]

    assets = []
    error_count = 0
    warning_count = 0
    for key in sorted(set(expected_rows) & set(actual_by_name)):
        exp = expected_rows[key]
        path = actual_by_name[key]
        parsed = parse_wave(path)
        digest = sha256_file(path)
        issues = []

        if digest != str(exp.get("sha256", "")):
            issues.append({"severity":"error","code":"CANON_HASH_MISMATCH"})
        if not parsed.get("valid"):
            issues.append({"severity":"error","code":"CANON_WAV_PARSE_FAILED","detail":parsed.get("parse_error")})
        else:
            for field in ("channels", "sample_rate", "sample_width_bits", "frames"):
                if exp.get(field) is not None and parsed.get(field) != exp.get(field):
                    issues.append({
                        "severity":"error",
                        "code":"CANON_METADATA_MISMATCH",
                        "field":field,
                        "expected":exp.get(field),
                        "actual":parsed.get(field),
                    })
            duration = parsed.get("duration_seconds")
            expected_duration = exp.get("duration_seconds")
            if duration is not None and expected_duration is not None and abs(float(duration)-float(expected_duration)) > 1e-8:
                issues.append({
                    "severity":"error",
                    "code":"CANON_DURATION_MISMATCH",
                    "expected":expected_duration,
                    "actual":duration,
                })
            if parsed.get("terminal_pad_missing"):
                issues.append({"severity":"warning","code":"CANON_TERMINAL_PAD_MISSING"})
            if parsed.get("riff_size_matches") is False:
                issues.append({"severity":"warning","code":"CANON_RIFF_SIZE_MISMATCH"})

        error_count += sum(i["severity"] == "error" for i in issues)
        warning_count += sum(i["severity"] == "warning" for i in issues)
        assets.append({
            "filename":path.name,
            "sha256":digest,
            "size_bytes":path.stat().st_size,
            "channels":parsed.get("channels"),
            "sample_rate":parsed.get("sample_rate"),
            "sample_width_bits":parsed.get("sample_width_bits"),
            "frames":parsed.get("frames"),
            "duration_seconds":parsed.get("duration_seconds"),
            "terminal_pad_missing":bool(parsed.get("terminal_pad_missing")),
            "riff_size_matches":parsed.get("riff_size_matches"),
            "issues":issues,
        })

    error_count += len(missing) + len(extra)
    source_digest = tree_digest(source_root, files)
    status = "PASS" if error_count == 0 else "FAIL"
    return {
        "schema":"openazrael.audio_lab.canonical_source_verify",
        "version":1,
        "status":status,
        "source_file_count":len(files),
        "expected_file_count":len(expected_rows),
        "source_tree_sha256":source_digest,
        "missing_expected_assets":missing,
        "unexpected_assets":extra,
        "errors":error_count,
        "warnings":warning_count,
        "assets":assets,
    }

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_root", type=Path)
    ap.add_argument("--legacy-ir", type=Path, default=ROOT/"data/audio/legacy_world_ir.json")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    source = args.source_root.resolve()
    if not source.is_dir():
        ap.error(f"source_root is not a directory: {source}")
    ir = json.loads(args.legacy_ir.read_text(encoding="utf-8"))
    before = tree_digest(source, iter_audio_files(source, {".wav", ".wave"}))
    report = verify_corpus(source, ir)
    after = tree_digest(source, iter_audio_files(source, {".wav", ".wave"}))
    report["source_unchanged"] = before == after == report["source_tree_sha256"]
    if not report["source_unchanged"]:
        report["status"] = "FAIL"
        report["errors"] += 1

    if args.output:
        try:
            output = ensure_output_outside_source(source, args.output)
        except ValueError as exc:
            ap.error(str(exc))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    print(json.dumps({
        "status":report["status"],
        "source_file_count":report["source_file_count"],
        "expected_file_count":report["expected_file_count"],
        "errors":report["errors"],
        "warnings":report["warnings"],
        "source_unchanged":report["source_unchanged"],
        "source_tree_sha256":report["source_tree_sha256"],
        "missing_expected_assets":report["missing_expected_assets"],
        "unexpected_assets":report["unexpected_assets"],
        "warning_assets":[
            {"filename":a["filename"],"issues":[i["code"] for i in a["issues"] if i["severity"]=="warning"]}
            for a in report["assets"] if any(i["severity"]=="warning" for i in a["issues"])
        ],
    }, indent=2))
    return 0 if report["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
