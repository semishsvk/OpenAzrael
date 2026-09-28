#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/tests/kg001_proof_capture_contract_v152.json"
CAPTURE = ROOT / "tools/capture_candidate4_proof_video.py"
SAFETY = ROOT / "tools/remaster_framework/capture_safety.py"
TESTS = ROOT / "tools/remaster_framework/tests/test_capture_safety.py"
WORKFLOW = ROOT / ".github/workflows/kg001-candidate4-source-gate.yml"

REQUIRED_CAPTURE = (
    "CaptureLease.acquire",
    "assert_no_conflicting_movie_capture",
    "run_monitored_capture",
    "audit_visual_stability",
    "VISUAL_STABILITY_GATE_FAILED",
    "kg001_proof_capture_receipt_v152.json",
)
REQUIRED_SAFETY = (
    "DUPLICATE_MOVIE_CAPTURE_DETECTED",
    "CAPTURE_LOCK_HELD",
    "CAPTURE_OUTPUT_REPLACED_DURING_RUN",
    "CAPTURE_OUTPUT_UNLINKED_DURING_RUN",
    "CAPTURE_OUTPUT_SIZE_REGRESSED",
    "ISOLATED_FLASH_SCORE",
)
REQUIRED_WORKFLOW = (
    "validate_kg001_proof_capture_v152.py",
    "test_capture_safety",
    "capture_safety.py",
)


def main() -> int:
    errors: list[str] = []
    for path in (CONTRACT, CAPTURE, SAFETY, TESTS, WORKFLOW):
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1

    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("version") != 152 or payload.get("status") != "ACCEPTED":
        errors.append("contract_identity")
    capture_safety = payload.get("capture_safety", {})
    visual = payload.get("visual_stability", {})
    if capture_safety.get("single_writer_lock_required") is not True:
        errors.append("single_writer_lock")
    if capture_safety.get("raw_output_inode_must_remain_stable") is not True:
        errors.append("inode_gate")
    if capture_safety.get("raw_output_size_must_be_monotonic") is not True:
        errors.append("size_gate")
    if visual.get("required") is not True:
        errors.append("visual_gate")
    if visual.get("final_mp4_deleted_on_failure") is not True:
        errors.append("visual_fail_closed")

    capture_text = CAPTURE.read_text(encoding="utf-8")
    safety_text = SAFETY.read_text(encoding="utf-8")
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    for token in REQUIRED_CAPTURE:
        if token not in capture_text:
            errors.append(f"capture_token:{token}")
    for token in REQUIRED_SAFETY:
        if token not in safety_text:
            errors.append(f"safety_token:{token}")
    for token in REQUIRED_WORKFLOW:
        if token not in workflow_text:
            errors.append(f"workflow_token:{token}")

    result = {
        "schema": "openazrael.kg001.proof_capture_source_validation",
        "version": 152,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "single_writer": True,
        "inode_monitor": True,
        "visual_temporal_gate": True,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
