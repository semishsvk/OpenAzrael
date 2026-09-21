#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
preflight = (ROOT / "tools/run_candidate3_preflight.py").read_text(encoding="utf-8")
exporter = (ROOT / "tools/export_candidate3.py").read_text(encoding="utf-8")
runner = (ROOT / "tools/run_kg001_candidate_v112.py").read_text(encoding="utf-8")
presets = (ROOT / "export_presets.cfg").read_text(encoding="utf-8")
project = (ROOT / "project.godot").read_text(encoding="utf-8")

checks = {
    "candidate3_branding": (
        'config/name="OpenAzrael KG-001 Candidate 3"' in project
        and 'config/version="KG001-Candidate-3"' in project
    ),
    "candidate3_export_preset": (
        'name="Windows Candidate 3"' in presets
        and 'custom_features="kg001_candidate3"' in presets
        and 'export_path="exports/OpenAzrael-KG001-Candidate3.exe"' in presets
    ),
    "source_only_mode": (
        '"--source-only"' in runner
        and "source_receipt" in runner
        and "forbidden_tracked_files" in runner
    ),
    "preflight_deletes_stale_receipt": "RECEIPT.unlink(missing_ok=True)" in preflight,
    "preflight_requires_clean_git": (
        'DIRTY_GIT_BEFORE_PREFLIGHT' in preflight
        and "git_clean()" in preflight
    ),
    "preflight_runs_fresh_checkout": (
        '"tools/run_kg001_candidate_v112.py"' in preflight
        and '"--fresh-checkout"' in preflight
    ),
    "preflight_requires_runtime_matrix": all(
        name in preflight
        for name in (
            '"v109"',
            '"v110"',
            '"v111"',
            '"audio_v116"',
            '"physical_v117"',
            '"well_tongs_v118"',
        )
    ),
    "preflight_binds_git_sha": (
        "head_before = git_head()" in preflight
        and 'candidate.get("commit_sha") == head_before' in preflight
        and 'fresh.get("commit_sha") == head_before' in preflight
    ),
    "preflight_binds_godot": (
        '"godot_version": godot_version' in preflight
        and '"godot_import": "PASS"' in preflight
    ),
    "preflight_binds_runtime_assets": (
        "REQUIRED_ASSETS" in preflight
        and '"runtime_assets": {' in preflight
        and '"sha256": sha256(p)' in preflight
    ),
    "preflight_binds_evidence_hashes": (
        '"candidate_result_sha256": sha256(CANDIDATE_RESULT)' in preflight
        and '"fresh_checkout_sha256": sha256(FRESH_RESULT)' in preflight
    ),
    "export_requires_preflight_pass": (
        'receipt.get("status") != "PASS"' in exporter
        and 'receipt.get("export_allowed") is not True' in exporter
    ),
    "export_rejects_changed_head": "HEAD_CHANGED_SINCE_PREFLIGHT" in exporter,
    "export_rejects_dirty_git": "DIRTY_GIT_AFTER_PREFLIGHT" in exporter,
    "export_rechecks_evidence": "PREFLIGHT_EVIDENCE_CHANGED" in exporter,
    "export_rechecks_runtime_assets": "RUNTIME_ASSET_CHANGED_SINCE_PREFLIGHT" in exporter,
    "export_rechecks_godot": "GODOT_VERSION_CHANGED_SINCE_PREFLIGHT" in exporter,
    "export_uses_release_preset": (
        '"--export-release"' in exporter
        and 'default="Windows Candidate 3"' in exporter
    ),
    "export_hashes_artifacts": (
        '"candidate3_export_receipt.json"' in exporter
        and '"sha256": sha256(out)' in exporter
    ),
    "manual_gate_stays_pending": '"manual_gate": "G10_PENDING_USER"' in exporter,
}

failed = [name for name, ok in checks.items() if not ok]
print("OpenAzrael Candidate 3 preflight/export source contract:", "PASS" if not failed else "FAIL")
for name, ok in checks.items():
    print(f" - {name}: {'PASS' if ok else 'FAIL'}")
sys.exit(1 if failed else 0)
