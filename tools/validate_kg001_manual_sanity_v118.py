#!/usr/bin/env python3
"""Validate a receipt-bound KG-001 G10 manual sanity result."""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_RESULT=ROOT/"data/tests/kg001_manual_sanity.json"
DEFAULT_RECEIPT=ROOT/"exports/OpenAzrael-KG001-Candidate2-v116.test-build.json"

REQUIRED_CHECKS=[
    "launch_no_blocking_error",
    "controls_normal",
    "floor_r1_stable",
    "floor_r7_stable",
    "floor_r8_stable",
    "stairs_r8_up_down",
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
    "triggered_979tongs_audible",
    "triggered_switchboard_audio_audible",
    "encountered_hash_cutouts_clean",
    "save_load_roundtrip",
    "f11_zip_without_state_mutation",
    "zero_reproducible_critical_bugs",
    "zero_reproducible_softlocks",
]
REQUIRED_BLOCKERS=[
    "issue_6_floor_collision",
    "critical_stair_traversal",
    "issue_9_human_audibility",
    "well_tongs_recovered_effect",
    "issue_11_colorkey_transparency",
]


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(result: dict, receipt: dict, receipt_path: Path) -> dict:
    checks={}
    manual=result.get("checks",{})
    blockers=result.get("blocker_checks",{})

    checks["schema"]=result.get("schema")=="openazrael.kg001.manual_sanity"
    checks["version"]=result.get("version")==2
    checks["status_pass"]=result.get("status")=="PASS"
    checks["receipt_schema"]=receipt.get("schema")=="openazrael.kg001.test_build_receipt"
    checks["receipt_version"]=receipt.get("version")==118
    checks["receipt_ready"]=receipt.get("status")=="READY_FOR_G10_MANUAL_TEST"
    checks["receipt_path"]=str(result.get("test_build_receipt","")).replace("\\","/") in {
        str(receipt_path).replace("\\","/"),
        str(receipt_path.relative_to(ROOT)).replace("\\","/") if receipt_path.is_relative_to(ROOT) else "",
    }
    checks["receipt_sha256"]=result.get("test_build_receipt_sha256")==sha256(receipt_path)
    checks["commit_match"]=result.get("candidate_commit")==receipt.get("commit_sha") and bool(receipt.get("commit_sha"))
    checks["exe_hash_match"]=result.get("executable_sha256")==receipt.get("executable_sha256") and bool(receipt.get("executable_sha256"))
    checks["pck_hash_match"]=result.get("pck_sha256")==receipt.get("pck_sha256") and bool(receipt.get("pck_sha256"))
    checks["godot_match"]=result.get("godot_version")==receipt.get("godot",{}).get("version") and bool(result.get("godot_version"))
    checks["tester_present"]=bool(str(result.get("tester","")).strip())
    checks["date_present"]=bool(str(result.get("date","")).strip())
    checks["check_set_exact"]=set(manual)==set(REQUIRED_CHECKS)
    checks["all_manual_pass"]=all(manual.get(name)=="PASS" for name in REQUIRED_CHECKS)
    checks["blocker_set_exact"]=set(blockers)==set(REQUIRED_BLOCKERS)
    checks["all_blockers_pass"]=all(blockers.get(name)=="PASS" for name in REQUIRED_BLOCKERS)
    checks["critical_bugs_empty"]=result.get("critical_bugs")==[]
    checks["softlocks_empty"]=result.get("reproducible_softlocks")==[]
    checks["receipt_keeps_release_closed"]=(
        receipt.get("release_blockers_close_automatically") is False
        and receipt.get("demo_known_good_tag_allowed") is False
    )
    checks["startup_smoke_pass"]=receipt.get("startup_smoke",{}).get("status")=="PASS"
    checks["candidate_suite_pass"]=receipt.get("candidate_suite_status")=="PASS"
    checks["fresh_checkout_pass"]=receipt.get("fresh_checkout_status")=="PASS"
    checks["visual_capture_pass"]=receipt.get("visual_capture_status")=="PASS"
    checks["complete_asset_set"]=(
        receipt.get("candidate2_asset_set_status")=="PASS"
        and receipt.get("candidate2_asset_local_status")=="COMPLETE"
    )

    failed=[name for name,value in checks.items() if not value]
    return {
        "schema":"openazrael.kg001.manual_sanity_validation",
        "version":118,
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "failed":failed,
        "candidate_commit":result.get("candidate_commit",""),
        "receipt_commit":receipt.get("commit_sha",""),
        "boundary":"G10 PASS validates this exact test-build receipt only. Release blockers and the final tag remain controlled by the canonical KG-001 status/release process.",
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path,default=DEFAULT_RESULT)
    ap.add_argument("--receipt",type=Path,default=DEFAULT_RECEIPT)
    args=ap.parse_args()

    if not args.input.is_file():
        print(json.dumps({"status":"FAIL","error":f"manual result missing: {args.input}"},indent=2))
        return 1
    if not args.receipt.is_file():
        print(json.dumps({"status":"FAIL","error":f"test-build receipt missing: {args.receipt}"},indent=2))
        return 1

    try:
        result=load_json(args.input)
        receipt=load_json(args.receipt)
        validation=validate(result,receipt,args.receipt.resolve())
    except Exception as exc:
        print(json.dumps({"status":"FAIL","error":str(exc)},indent=2))
        return 1
    print(json.dumps(validation,indent=2))
    return 0 if validation["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
