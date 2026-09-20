#!/usr/bin/env python3
"""Source contract for the thin Windows Candidate 2 local wrapper."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"tools/run_kg001_candidate2_windows_v117.ps1"
text=path.read_text(encoding="utf-8") if path.is_file() else ""
promotion_call=text.rfind('"tools/promote_kg001_candidate_results_v118.py"')
receipt_write=text.find('"exports/OpenAzrael-KG001-Candidate2-v116.test-build.json"')
export_call=text.find('"--export-debug"')

checks={
    "wrapper_exists":path.is_file(),
    "validate_only":"ValidateOnly" in text and "candidate2_windows_wrapper_source" in text,
    "canonical_toolchain":"validate_kg001_toolchain_v117.py" in text and "--require-godot" in text,
    "canonical_restore":"restore_candidate_assets.py" in text,
    "canonical_runner":"run_kg001_candidate_v112.py" in text,
    "complete_asset_gate":"validate_kg001_candidate2_asset_set_v118.py" in text,
    "promotion_helper_dependency":"tools/promote_kg001_candidate_results_v118.py" in text,
    "test_build_contract_dependency":"data/tests/kg001_test_build_contract_v118.json" in text,
    "fresh_checkout":"--fresh-checkout" in text,
    "visual_capture":"--visual-capture" in text,
    "promotion_optional":"PromoteResults" in text and "promote_kg001_candidate_results_v118.py" in text,
    "promotion_after_export_smoke":(
        text.rfind("promote_kg001_candidate_results_v118.py")
        > text.find("kg001_windows_candidate2_startup.log")
    ),
    "windows_export_preset":'"Windows Candidate 2"' in text and "--export-debug" in text,
    "build_manifest_head_binding":all(token in text for token in [
        "git rev-parse HEAD",
        "buildManifest.commit_sha",
        "source_identity_complete",
        "asset_counts_complete",
    ]),
    "export_hashes":"Get-FileHash" in text and "SHA256" in text,
    "exported_startup_smoke":all(token in text for token in [
        "--headless",
        "--quit-after",
        "kg001_windows_candidate2_startup.log",
        "criticalPatterns",
        "SCRIPT ERROR:",
        "Failed to load resource",
    ]),
    "requires_candidate_fresh_visual_pass":all(token in text for token in [
        "candidateEvidence.status",
        "freshEvidence.status",
        "visualEvidence.status",
    ]),
    "test_build_receipt":all(token in text for token in [
        "openazrael.kg001.test_build_receipt",
        "READY_FOR_G10_MANUAL_TEST",
        "manual_pending",
        "demo_known_good_tag_allowed = $false",
        "release_blockers_close_automatically = $false",
    ]),
    "ignored_export_evidence":".tmp/kg001/kg001_windows_candidate2_export_v118.json" in text,
    "receipt_sidecar":"exports/OpenAzrael-KG001-Candidate2-v116.test-build.json" in text,
    "no_gameplay_reimplementation":all(token not in text for token in [
        "DemoState.", "set_flag(", "set_puzzle", "load_room(",
    ]),
    "no_commercial_copy_to_git":all(token not in text for token in [
        "git add assets/", "git commit assets/", "data/tests/commercial",
    ]),
}
failed=[name for name,value in checks.items() if not value]
result={
    "schema":"openazrael.kg001.candidate2_windows_wrapper_contract",
    "version":118,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
    "runtime_status":"NOT_EXECUTED",
    "boundary":"Wrapper only orchestrates canonical restore/runner/export/startup-smoke steps. READY_FOR_G10_MANUAL_TEST is not release approval and cannot close Issues #6/#9/#11 or create demo-known-good-001.",
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
