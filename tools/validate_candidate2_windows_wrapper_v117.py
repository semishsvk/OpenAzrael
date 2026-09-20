#!/usr/bin/env python3
"""Source contract for the thin Windows Candidate 2 local wrapper."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"tools/run_kg001_candidate2_windows_v117.ps1"
text=path.read_text(encoding="utf-8") if path.is_file() else ""

checks={
    "wrapper_exists":path.is_file(),
    "validate_only":"ValidateOnly" in text and "candidate2_windows_wrapper_source" in text,
    "canonical_toolchain":"validate_kg001_toolchain_v117.py" in text and "--require-godot" in text,
    "canonical_restore":"restore_candidate_assets.py" in text,
    "canonical_runner":"run_kg001_candidate_v112.py" in text,
    "fresh_checkout":"--fresh-checkout" in text,
    "visual_capture":"--visual-capture" in text,
    "promotion_optional":"PromoteResults" in text and "--promote-results" in text,
    "windows_export_preset":'"Windows Candidate 2"' in text and "--export-debug" in text,
    "export_hashes":"Get-FileHash" in text and "SHA256" in text,
    "ignored_export_evidence":".tmp/kg001/kg001_windows_candidate2_export_v117.json" in text,
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
    "version":117,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
    "runtime_status":"NOT_EXECUTED",
    "boundary":"Wrapper only orchestrates existing canonical restore/runner/export steps; restored-asset Windows execution remains separate evidence.",
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
