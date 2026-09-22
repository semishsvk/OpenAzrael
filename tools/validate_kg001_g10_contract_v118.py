#!/usr/bin/env python3
"""Validate the source contract for receipt-bound KG-001 G10 evidence."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT/"data/tests/kg001_manual_sanity_template.json"
RECORDER=ROOT/"tools/record_kg001_g10_v118.py"
VALIDATOR=ROOT/"tools/validate_kg001_manual_sanity_v118.py"
STATUS=ROOT/"tools/kg001_status_v112.py"

template=json.loads(TEMPLATE.read_text(encoding="utf-8"))
recorder=RECORDER.read_text(encoding="utf-8")
validator=VALIDATOR.read_text(encoding="utf-8")
status=STATUS.read_text(encoding="utf-8")

expected_checks={
    "launch_no_blocking_error",
    "controls_normal",
    "floor_r1_stable",
    "floor_r7_stable",
    "floor_r8_stable",
    "keyhole_transparency_clean",
    "tongs_transparency_clean",
    "tongs_pickup",
    "door1_r1_to_r7",
    "well_key_tongs_and_acquire",
    "r7_lever_wheel_lever_drains_bath",
    "r7_to_r1_persistence",
    "door2_r1_to_r8",
    "lens_after_bath_drain",
    "lens_place_on_bible",
    "optical_zxplate_activation",
    "secret_door_and_shield",
    "shield_completes_demo",
    "audio_audible",
    "encountered_hash_cutouts_clean",
    "save_load_roundtrip",
    "f11_zip_without_state_mutation",
    "zero_reproducible_critical_bugs",
    "zero_reproducible_softlocks",
}
expected_blockers={
    "issue_6_floor_collision",
    "issue_9_human_audibility",
    "issue_11_colorkey_transparency",
}

checks={
    "template_schema":template.get("schema")=="openazrael.kg001.manual_sanity",
    "template_version":template.get("version")==2,
    "template_pending":template.get("status")=="PENDING",
    "template_exact_checks":set(template.get("checks",{}))==expected_checks,
    "template_exact_blockers":set(template.get("blocker_checks",{}))==expected_blockers,
    "template_receipt_identity_fields":all(
        name in template
        for name in (
            "test_build_receipt",
            "test_build_receipt_sha256",
            "candidate_commit",
            "executable_sha256",
            "pck_sha256",
            "godot_version",
        )
    ),
    "recorder_commands":all(
        token in recorder
        for token in (
            'sub.add_parser("init")',
            'sub.add_parser("record")',
            'sub.add_parser("finalize")',
        )
    ),
    "recorder_receipt_ready_gate":"READY_FOR_G10_MANUAL_TEST" in recorder,
    "recorder_exact_identity":all(
        token in recorder
        for token in (
            "test_build_receipt_sha256",
            "candidate_commit",
            "executable_sha256",
            "pck_sha256",
            "godot_version",
        )
    ),
    "recorder_promote_only_after_validation":all(
        token in recorder
        for token in (
            'if validation.get("status")!="PASS"',
            "refusing promotion because receipt-bound G10 validation failed",
            "kg001_manual_sanity_validation_v118.json",
        )
    ),
    "validator_receipt_bound":all(
        token in validator
        for token in (
            "receipt_sha256",
            "commit_match",
            "exe_hash_match",
            "pck_hash_match",
            "godot_match",
            "receipt_ready",
        )
    ),
    "validator_requires_all_checks":all(
        token in validator
        for token in (
            "all_manual_pass",
            "all_blockers_pass",
            "critical_bugs_empty",
            "softlocks_empty",
        )
    ),
    "validator_requires_automated_receipt_pass":all(
        token in validator
        for token in (
            "startup_smoke_pass",
            "candidate_suite_pass",
            "fresh_checkout_pass",
            "visual_capture_pass",
            "complete_asset_set",
        )
    ),
    "status_loads_v118_validation":"kg001_manual_sanity_validation_v118.json" in status,
    "status_requires_manual_v2":'manual.get("version")==2' in status,
    "status_requires_validation_v118":'manual_validation.get("version")==118' in status,
    "status_binds_fresh_commit":all(
        token in status
        for token in (
            'manual.get("candidate_commit")==fresh.get("commit_sha")',
            'manual_validation.get("candidate_commit")==fresh.get("commit_sha")',
        )
    ),
    "status_exposes_receipt_binding":"manual_sanity_receipt_bound" in status,
}
failed=[name for name,value in checks.items() if not value]
result={
    "schema":"openazrael.kg001.g10_receipt_contract_validation",
    "version":118,
    "status":"PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
    "runtime_status":"NOT_EXECUTED",
    "boundary":"G10 remains human/manual. This contract only guarantees that a recorded PASS is bound to the exact v118 test-build receipt and fresh-checkout commit.",
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
