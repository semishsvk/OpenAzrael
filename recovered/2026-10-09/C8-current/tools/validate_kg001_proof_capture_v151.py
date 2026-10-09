#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/tests/kg001_proof_capture_contract_v151.json"
CAPTURE = ROOT / "tools/capture_candidate4_proof_video.py"
RUNNER = ROOT / "scripts/validation/pppv_playthrough_runner.gd"
WORKFLOW = ROOT / ".github/workflows/kg001-candidate4-source-gate.yml"

REQUIRED_CAPTURE_TOKENS = (
    "candidate4_preflight_receipt.json",
    "candidate4_frozen_release_receipt.json",
    "--write-movie",
    "--fixed-fps",
    "--pppv-proof-overlay=1",
    "semantic_replay_sha256",
    "final_state_sha256",
    "libx264",
    "ffprobe",
    "volumedetect",
    "RAW_MOVIE_AUDIO_STREAM_MISSING",
    "RAW_MOVIE_AUDIO_SILENT_OR_UNVERIFIED",
    "FINAL_MP4_AUDIO_STREAM_MISSING",
    "audio_required",
    "import array",
    "RAW_AUDIO_PCM",
    "MP4_AUDIO_PCM",
    "ai_generated_visuals",
)
REQUIRED_RUNNER_TOKENS = (
    "PPPVProofCaptureOverlay",
    "OPENAZRAEL_PROOF_GIT_SHA",
    "OPENAZRAEL_PROOF_FREEZE_SHA",
    "REAL PPPV PROOF CAPTURE",
)
REQUIRED_WORKFLOW_TOKENS = (
    "validate_kg001_proof_capture_v151.py",
    "capture_candidate4_proof_video.py",
)


def fail(errors: list[str]) -> int:
    print(json.dumps({
        "schema": "openazrael.kg001.proof_capture_source_validation",
        "version": 151,
        "status": "FAIL",
        "errors": errors,
    }, indent=2))
    return 1


def main() -> int:
    errors: list[str] = []
    for path in (CONTRACT, CAPTURE, RUNNER, WORKFLOW):
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
    if errors:
        return fail(errors)

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail([f"invalid_contract:{exc}"])

    if contract.get("schema") != "openazrael.kg001.proof_capture_contract":
        errors.append("contract_schema")
    if contract.get("version") != 151:
        errors.append("contract_version")
    if contract.get("status") != "ACCEPTED":
        errors.append("contract_status")
    if contract.get("supplemental_evidence") is not True:
        errors.append("supplemental_evidence")
    if contract.get("replaces_manual_g10") is not False:
        errors.append("manual_g10_boundary")
    visual = contract.get("visual_evidence", {})
    if not isinstance(visual, dict):
        visual = {}
    if visual.get("forbid_ai_generated_visuals") is not True:
        errors.append("ai_visual_boundary")
    if visual.get("forbid_noclip_camera") is not True:
        errors.append("noclip_boundary")
    audio = visual.get("audio", {})
    if not isinstance(audio, dict) or audio.get("required") is not True:
        errors.append("audio_required_boundary")
    if isinstance(audio, dict) and audio.get("digital_silence_forbidden") is not True:
        errors.append("audio_silence_boundary")
    audio = contract.get("audio_evidence", {})
    if not isinstance(audio, dict):
        audio = {}
    if audio.get("runtime_audio_only") is not True:
        errors.append("runtime_audio_only")
    if audio.get("added_postproduction_music") is not False:
        errors.append("postproduction_audio_boundary")
    if audio.get("raw_movie_audio_stream_required") is not True:
        errors.append("raw_audio_required")
    if audio.get("raw_movie_non_silent_signal_required") is not True:
        errors.append("non_silent_audio_required")
    if audio.get("final_mp4_audio_stream_required") is not True:
        errors.append("final_audio_required")

    capture_text = CAPTURE.read_text(encoding="utf-8")
    runner_text = RUNNER.read_text(encoding="utf-8")
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    for token in REQUIRED_CAPTURE_TOKENS:
        if token not in capture_text:
            errors.append(f"capture_token:{token}")
    for token in REQUIRED_RUNNER_TOKENS:
        if token not in runner_text:
            errors.append(f"runner_token:{token}")
    for token in REQUIRED_WORKFLOW_TOKENS:
        if token not in workflow_text:
            errors.append(f"workflow_token:{token}")

    if errors:
        return fail(errors)

    print(json.dumps({
        "schema": "openazrael.kg001.proof_capture_source_validation",
        "version": 151,
        "status": "PASS",
        "contract": str(CONTRACT.relative_to(ROOT)),
        "capture_tool": str(CAPTURE.relative_to(ROOT)),
        "runner": str(RUNNER.relative_to(ROOT)),
        "supplemental_evidence_only": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
