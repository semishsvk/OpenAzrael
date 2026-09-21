#!/usr/bin/env python3
"""Validate the source contract for Candidate 2 test-build readiness v118."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/tests/kg001_test_build_contract_v118.json"
WRAPPER=ROOT/"tools/run_kg001_candidate2_windows_v117.ps1"

contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
wrapper=WRAPPER.read_text(encoding="utf-8") if WRAPPER.is_file() else ""

checks={
    "contract_schema":contract.get("schema")=="openazrael.kg001.test_build_contract",
    "contract_version":contract.get("version")==118,
    "contract_status":contract.get("status")=="SOURCE_CONTRACT_PASS",
    "ready_status":contract.get("ready_status")=="READY_FOR_G10_MANUAL_TEST",
    "manual_requirements_six":len(contract.get("manual_requirements",[]))==6,
    "manual_requirements_cover_candidate2_failures":all(
        any(token in row for row in contract.get("manual_requirements",[]))
        for token in (
            "natural floor support",
            "stair profiles",
            "ambient audio",
            "979TONGS.WAV",
            "cutout transparency",
            "zero reproducible softlocks",
        )
    ),
    "release_blockers_not_auto_closed":contract.get("release_blockers_close_automatically") is False,
    "known_good_tag_not_auto_allowed":contract.get("demo_known_good_tag_allowed") is False,
    "runtime_receipt_path":contract.get("runtime_receipt")==".tmp/kg001/kg001_test_build_receipt_v118.json",
    "distribution_receipt_path":contract.get("distribution_receipt")=="exports/OpenAzrael-KG001-Candidate2-v116.test-build.json",
    "distribution_testing_guide":contract.get("distribution_testing_guide")=="exports/OpenAzrael-KG001-Candidate2-v116.TESTING.txt",
    "distribution_build_manifest":contract.get("distribution_build_manifest")=="exports/OpenAzrael-KG001-Candidate2-v116.build-manifest.json",
    "distribution_checksum_manifest":contract.get("distribution_checksum_manifest")=="exports/OpenAzrael-KG001-Candidate2-v116.SHA256SUMS",
    "wrapper_receipt_schema":"openazrael.kg001.test_build_receipt" in wrapper,
    "wrapper_receipt_v118":"version = 118" in wrapper,
    "wrapper_ready_status":"READY_FOR_G10_MANUAL_TEST" in wrapper,
    "wrapper_asset_gate":"validate_kg001_candidate2_asset_set_v118.py" in wrapper,
    "wrapper_build_head_binding":"buildManifest.commit_sha" in wrapper and "git rev-parse HEAD" in wrapper,
    "wrapper_source_identity":"source_identity_complete" in wrapper,
    "wrapper_asset_counts":"asset_counts_complete" in wrapper,
    "wrapper_startup_smoke":"--quit-after" in wrapper and "kg001_windows_candidate2_startup.log" in wrapper,
    "wrapper_requires_startup_ready_marker":"OPENAZRAEL_CANDIDATE_STARTUP_READY" in wrapper and "startup marker was not observed" in wrapper,
    "wrapper_requires_startup_build_sha":"startup marker/log does not contain current build commit" in wrapper and "$currentHead" in wrapper,
    "wrapper_critical_log_scan":all(token in wrapper for token in [
        "SCRIPT ERROR:",
        "Failed to load script",
        "Failed to create an autoload",
        "Failed to load resource",
        "Cannot open file",
    ]),
    "wrapper_requires_fresh_visual":all(token in wrapper for token in [
        "freshEvidence.status",
        "visualEvidence.status",
    ]),
    "contract_evidence_binding":isinstance(contract.get("evidence_binding"),dict)
        and contract.get("evidence_binding",{}).get("promotion")
        =="after export and exported-EXE startup smoke in Windows wrapper",
    "contract_startup_ready_binding":(
        isinstance(contract.get("evidence_binding"),dict)
        and "resource preflight PASS" in str(
            contract.get("evidence_binding",{}).get("startup_ready","")
        )
        and "R1/spaview" in str(
            contract.get("evidence_binding",{}).get("startup_ready","")
        )
    ),
    "wrapper_candidate_fresh_commit_binding":all(token in wrapper for token in [
        "candidateEvidence.commit_sha",
        "freshEvidence.commit_sha",
        "does not match current HEAD",
    ]),
    "wrapper_visual_capture_binding":all(token in wrapper for token in [
        "visualEvidence.build_commit_sha",
        "visualEvidence.run_id",
        "visual_capture_run_id",
        "visual_capture_evidence_sha256",
        "visual_captures",
        '"R1" = "spaview"',
        '"R7" = "view"',
        '"R8" = "Object14"',
    ]),
    "wrapper_hashes_package":all(token in wrapper for token in [
        "executable_sha256",
        "pck_sha256",
        "build_manifest_sha256",
    ]),
    "wrapper_distribution_manifest":all(token in wrapper for token in [
        "OpenAzrael-KG001-Candidate2-v116.build-manifest.json",
        "distributionBuildManifestSha256",
        "Distributed build-manifest sidecar does not match",
    ]),
    "wrapper_sha256sums":all(token in wrapper for token in [
        "OpenAzrael-KG001-Candidate2-v116.SHA256SUMS",
        "checksumFiles",
        "Get-FileHash -Algorithm SHA256",
    ]),
    "wrapper_manual_pending":"manual_pending" in wrapper,
    "wrapper_testing_guide":all(token in wrapper for token in [
        "MANUAL G10 CHECKLIST",
        "DIAGNOSTIC KEYS",
        "OpenAzrael-KG001-Candidate2-v116.TESTING.txt",
    ]),
    "wrapper_keeps_release_closed":"demo_known_good_tag_allowed = $false" in wrapper and "release_blockers_close_automatically = $false" in wrapper,
}
failed=[name for name,value in checks.items() if not value]
result={
    "schema":"openazrael.kg001.test_build_contract_validation",
    "version":118,
    "status":"PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
    "runtime_status":"NOT_EXECUTED",
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
