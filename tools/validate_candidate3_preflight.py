#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.kg001_gate_manifest import (
    CANDIDATE3_REQUIRED_RUNTIME,
    CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE,
    PPPV_REQUIRED_EVIDENCE,
    RUNTIMES,
)
import tools.run_kg001_candidate_v112 as candidate_runner
import tools.run_candidate3_preflight as candidate3_preflight
preflight = (ROOT / "tools/run_candidate3_preflight.py").read_text(encoding="utf-8")
exporter = (ROOT / "tools/export_candidate3.py").read_text(encoding="utf-8")
runner = (ROOT / "tools/run_kg001_candidate_v112.py").read_text(encoding="utf-8")
pppv_runner = (ROOT / "tools/run_candidate3_pppv_v2.py").read_text(encoding="utf-8")
presets = (ROOT / "export_presets.cfg").read_text(encoding="utf-8")
project = (ROOT / "project.godot").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/kg001-candidate3-source-gate.yml").read_text(encoding="utf-8")
contract = __import__("json").loads(
    (ROOT / "data/tests/kg001_candidate3_preflight_contract_v1.json").read_text(
        encoding="utf-8"
    )
)

checks = {
    "canonical_runner_runtime_list": (
        candidate_runner.RUNTIMES == RUNTIMES
        and tuple(name for name, _script, _marker in candidate_runner.RUNTIMES) == CANDIDATE3_REQUIRED_RUNTIME
    ),
    "canonical_preflight_runtime_list": tuple(candidate3_preflight.REQUIRED_RUNTIME) == CANDIDATE3_REQUIRED_RUNTIME,
    "contract_runtime_list_exact": contract.get("local_preflight", {}).get("required_runtime_pass") == list(CANDIDATE3_REQUIRED_RUNTIME),
    "contract_additional_runtime_evidence_exact": contract.get("local_preflight", {}).get("required_additional_runtime_evidence_pass") == list(CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE),
    "contract_pppv_list_exact": contract.get("local_preflight", {}).get("required_pppv_v2_pass") == list(PPPV_REQUIRED_EVIDENCE),
    "tracked_contract": (
        contract.get("schema") == "openazrael.kg001.candidate3_preflight_contract"
        and contract.get("version") == 1
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
        and contract.get("candidate") == "KG-001 Candidate 3"
        and contract.get("export", {}).get("requires_current_preflight_receipt") is True
        and contract.get("post_export", {}).get("manual_gate") == "G10_PENDING_USER"
    ),
    "source_ci_workflow": (
        "python-version: [\"3.11\", \"3.12\"]" in workflow
        and "python tools/run_kg001_candidate_v112.py --source-only" in workflow
        and "git status --porcelain --untracked-files=normal" in workflow
    ),
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
    "preflight_requires_pppv_v2": (
        '"tools/run_candidate3_pppv_v2.py"' in preflight
        and '"PPPV_V2_RUNTIME_FAILED"' in preflight
        and '"PPPV_V2_EVIDENCE_MISSING"' in preflight
        and '"PPPV_V2_INVARIANT_FAILED"' in preflight
        and "PPPV_EVIDENCE_FILES" in preflight
        and tuple(candidate3_preflight.PPPV_REQUIRED_EVIDENCE) == PPPV_REQUIRED_EVIDENCE
    ),
    "pppv_v2_runner_is_isolated": (
        'TMP=ROOT/".tmp/kg001_pppv_v2"' in pppv_runner
        and "run_pppv_scenario_suite" in pppv_runner
        and "run_full_pppv" in pppv_runner
        and "kg001_pppv_determinism.json" in pppv_runner
        and "pppv_scenario_suite_integrity.json" in pppv_runner
        and "pppv_determinism_integrity.json" in pppv_runner
    ),
    "source_gate_runs_remaster_framework": any(
        cmd[1:3] == ["-m", "tools.remaster_framework.cli"] for cmd in candidate_runner.SOURCE_COMMANDS
    ) and any(
        "tools/remaster_framework/tests" in cmd for cmd in candidate_runner.SOURCE_COMMANDS
    ) and any(
        "tools.openazrael_adapters.runtime_capabilities" in cmd for cmd in candidate_runner.SOURCE_COMMANDS
    ),
    "preflight_uses_canonical_runtime_matrix": (
        "CANDIDATE3_REQUIRED_RUNTIME" in preflight
        and "REQUIRED_RUNTIME = CANDIDATE3_REQUIRED_RUNTIME" in preflight
        and "SOURCE_COMMANDS=[" not in runner
        and "RUNTIMES=[" not in runner
    ),
    "preflight_forensic_report_is_fail_closed": (
        "ROOM_FORENSIC_REPORT_V131_INVALID" in preflight
        and "ROOM_FORENSIC_REPORT_V131_NOT_PASS" in preflight
        and 'for room in ("R1", "R7", "R8")' in preflight
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
        "RUNTIME_ASSET_ROOTS" in preflight
        and '"assets/rooms"' in preflight
        and '"assets/audio"' in preflight
        and '"assets/textures/classic"' in preflight
        and "len(classic_pngs) != 86" in preflight
        and '"runtime_asset_summary": {' in preflight
        and '"runtime_assets": {' in preflight
        and '"sha256": sha256(p)' in preflight
    ),
    "preflight_binds_evidence_hashes": (
        '"candidate_result_sha256": sha256(CANDIDATE_RESULT)' in preflight
        and '"fresh_checkout_sha256": sha256(FRESH_RESULT)' in preflight
        and '"pppv_v2": {' in preflight
        and '"sha256": sha256(path)' in preflight
    ),
    "runtime_build_identity_generated": (
        'RUNTIME_BUILD_IDENTITY = ROOT / "data/runtime_build_identity.json"' in exporter
        and '"schema": "openazrael.runtime_build_identity"' in exporter
        and '"commit_sha": head' in exporter
        and '"godot_version": godot_version' in exporter
        and "RUNTIME_BUILD_IDENTITY.write_text" in exporter
        and "RUNTIME_BUILD_IDENTITY.unlink(missing_ok=True)" in exporter
        and "data/runtime_build_identity.json" in presets
    ),
    "export_requires_preflight_pass": (
        'receipt.get("status") != "PASS"' in exporter
        and 'receipt.get("export_allowed") is not True' in exporter
    ),
    "export_rejects_changed_head": "HEAD_CHANGED_SINCE_PREFLIGHT" in exporter,
    "export_rejects_dirty_git": "DIRTY_GIT_AFTER_PREFLIGHT" in exporter,
    "export_rechecks_evidence": "PREFLIGHT_EVIDENCE_CHANGED" in exporter,
    "export_rechecks_pppv_evidence": (
        "PPPV_PREFLIGHT_EVIDENCE_MISSING" in exporter
        and "PPPV_PREFLIGHT_EVIDENCE_INVALID" in exporter
        and "PPPV_EVIDENCE_CHANGED_SINCE_PREFLIGHT" in exporter
        and '"pppv_v2_evidence": receipt.get("evidence", {}).get("pppv_v2", {})' in exporter
    ),
    "export_rechecks_runtime_assets": "RUNTIME_ASSET_CHANGED_SINCE_PREFLIGHT" in exporter,
    "export_rejects_asset_set_drift": (
        "RUNTIME_ASSET_SET_CHANGED_SINCE_PREFLIGHT" in exporter
        and "current_asset_paths != receipt_asset_paths" in exporter
        and '"added": sorted(current_asset_paths - receipt_asset_paths)' in exporter
        and '"removed": sorted(receipt_asset_paths - current_asset_paths)' in exporter
    ),
    "export_rechecks_godot": "GODOT_VERSION_CHANGED_SINCE_PREFLIGHT" in exporter,
    "export_uses_release_preset": (
        '"--export-release"' in exporter
        and 'default="Windows Candidate 3"' in exporter
    ),
    "export_requires_exe_pck_pair": (
        '"PCK_MISSING"' in exporter
        and 'binary_format/embed_pck=false' in presets
    ),
    "export_requires_post_export_startup_smoke": (
        "EXPORTED_STARTUP_SMOKE_FAILED" in exporter
        and '"--headless"' in exporter
        and '"--quit-after"' in exporter
        and '"export_smoke": {' in exporter
    ),
    "export_hashes_artifacts": (
        '"candidate3_export_receipt.json"' in exporter
        and '"sha256": sha256(out)' in exporter
        and '"sha256": sha256(pck)' in exporter
    ),
    "export_receipt_records_runtime_identity": (
        '"runtime_build_identity_embedded": true' in exporter
        and '"runtime_build_identity": runtime_identity' in exporter
    ),
    "manual_gate_stays_pending": '"manual_gate": "G10_PENDING_USER"' in exporter,
}

failed = [name for name, ok in checks.items() if not ok]
print("OpenAzrael Candidate 3 preflight/export source contract:", "PASS" if not failed else "FAIL")
for name, ok in checks.items():
    print(f" - {name}: {'PASS' if ok else 'FAIL'}")
sys.exit(1 if failed else 0)
