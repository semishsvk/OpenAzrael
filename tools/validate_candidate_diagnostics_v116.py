#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def read(path):
    p=ROOT/path
    if not p.is_file():
        errors.append("missing: "+path)
        return ""
    return p.read_text(encoding="utf-8")

project=read("project.godot")
main=read("main.tscn")
diag=read("scripts/candidate_diagnostics_v116.gd")
trigger=read("scripts/kg001_trigger_debug_v116.gd")
room=read("scripts/room_manager.gd")
hud=read("scripts/hud.gd")
probe=read("scripts/interaction_probe.gd")
runner=read("tools/run_kg001_candidate_v112.py")
bug_capture=diag.split("# v116-context-v31: observational one-key bug-report capture.",1)[-1]
bugdoc=read("docs/BUG_REPORTING.md")
issuetpl=read(".github/ISSUE_TEMPLATE/bug_report.yml")

checks={
    "autoload": 'CandidateDiagnostics="*res://scripts/candidate_diagnostics_v116.gd"' in project,
    "candidate_version": 'config/version="KG001-Candidate-2-v116"' in project,
    "trigger_node": 'path="res://scripts/kg001_trigger_debug_v116.gd"' in main and 'name="TriggerDebugV116"' in main,
    "no_room_glb_preload": 'preload("res://assets/rooms/' not in room,
    "dynamic_room_paths": 'const ROOM_SCENE_PATHS' in room and 'load(String(ROOM_SCENE_PATHS[id]))' in room,
    "fail_fast": 'fail_fast_if_required_resources_missing' in room and 'get_tree().quit(2)' in room,
    "safe_evidence_parse": 'var parsed_evidence = JSON.parse_string' in room and 'if not parsed_evidence is Dictionary' in room and 'evidence = parsed_evidence' in room,
    "room_signal": 'signal room_changed(room_id: String)' in room and 'room_changed.emit(id)' in room,
    "trigger_edges": '_update_diagnostic_trigger_states' in room and 'CandidateDiagnostics.observe_trigger' in room,
    "quiet_initial_trigger_state": 'if not _trigger_states.has(key)' in diag and 'if not inside:' in diag,
    "room_transition_log": 'CandidateDiagnostics.record_transition' in room,
    "interaction_log": 'CandidateDiagnostics.record_interaction' in probe and 'interaction_miss' in probe,
    "build_manifest_core_resource": 'data/generated/kg001_candidate_build_manifest.json' in diag and 'BUILD_MANIFEST_PATH' in diag,
    "runner_writes_build_manifest": 'write_kg001_build_manifest.py' in runner and 'BUILD_MANIFEST' in runner,
    "run_scoped_log": 'RUN_ROOT_PREFIX' in diag and '/events.jsonl' in diag and '_initialize_run_scope' in diag,
    "run_manifest": 'openazrael.kg001.candidate_run_manifest' in diag and 'run_manifest.json' in diag and '_write_run_manifest' in diag,
    "run_identity_in_events": '"run_id": run_id' in diag and '"build_commit_sha": String(build_manifest.get("commit_sha", ""))' in diag,
    "run_start_end": 'record_event("candidate_run_start"' in diag and 'record_event("candidate_run_end"' in diag,
    "state_dump": 'canonical_state_hash' in diag and 'STATE_DUMP_BASENAME' in diag and 'run_dir' in diag,
    "golden_audio_assets": all(x in diag for x in ["797TAP.WAV","S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV","S174ELP1.WAV","S174ELP2.WAV","S186.WAV"]) and "data/audio/legacy_world_ir.json" in diag,
    "startup_ready_marker":"OPENAZRAEL_CANDIDATE_STARTUP_READY" in diag and '"build_commit_sha": String(build_manifest.get("commit_sha", ""))' in diag,
    "startup_ready_not_early":(
        "func emit_startup_ready" in diag
        and "OPENAZRAEL_CANDIDATE_STARTUP_READY" not in diag.split("func emit_startup_ready",1)[0]
    ),
    "startup_ready_after_preflight":(
        'CandidateDiagnostics.emit_startup_ready("R1")' in room
        and room.find("fail_fast_if_required_resources_missing")
            < room.find('CandidateDiagnostics.emit_startup_ready("R1")')
        and room.find('load_room("R1", false)')
            < room.find('CandidateDiagnostics.emit_startup_ready("R1")')
        and room.find('_spawn_at_portal("R1", "spaview")')
            < room.find('CandidateDiagnostics.emit_startup_ready("R1")')
        and '"required_resource_preflight": "PASS"' in diag
        and 'record_event("candidate_startup_ready"' in diag
    ),
    "headless_audio_boundary": 'DisplayServer.get_name() != "headless"' in room,
    "f6_triggers": 'KEY_F6' in trigger and 'BoxMesh.new()' in trigger,
    "f7_candidate_hud": 'KEY_F7' in hud and 'CandidateDebugPanelV116' in hud,
    "f8_audio_kept": 'KEY_F8' in hud,
    "f9_parity_kept": 'KEY_F9' in hud and '_capture_audio_parity()' in hud,
    "f10_dump": 'KEY_F10' in hud and 'CandidateDiagnostics.dump_state' in hud,
    "f11_bug_report": 'KEY_F11' in diag and 'capture_bug_report' in diag,
    "bug_zip": 'ZIPPacker.new()' in diag and 'BUG_REPORT_BASENAME' in diag and 'run_dir' in diag,
    "bug_screenshot": 'screenshot.png' in diag and '_capture_screenshot_png' in diag and 'save_png_to_buffer()' in diag,
    "bug_event_tail": 'events_tail.jsonl' in diag and 'BUG_REPORT_EVENT_TAIL_LINES' in diag,
    "bug_run_provenance": all(x in diag for x in [
        'run_manifest.json',
        'build_manifest.json',
        '"run_id": run_id',
        '"build_commit_sha": String(build_manifest.get("commit_sha", ""))',
    ]),
    "bug_state_snapshot": 'state.json' in diag and 'canonical_state_payload' in diag,
    "stable_ids": all(x in diag for x in ['ROOM:','TRG:','PUZ:','FLAG:','ITEM:']),
    "bug_report_source_safe": '"commercial_assets_included": false' in diag and '"source_safe": true' in diag,
    "bug_report_observational": all(x not in bug_capture for x in ["DemoState.acquire(","DemoState.set_flag(","DemoState.set_puzzle_node(","DemoState.restore_canonical_state_payload(","LegacyEvents.run(","load_room("]),
    "bug_report_no_commercial_asset_reads": all(x not in bug_capture for x in ["res://assets/rooms/","res://assets/audio/","res://assets/textures/classic/"]),
    "bug_hud_surface": "F11 bug report" in hud and "CandidateDiagnostics.last_bug_report" in hud,
    "issue_template": 'name: OpenAzrael bug report' in issuetpl and 'Diagnostic package' in issuetpl,
    "bug_reporting_doc": 'F11' in bugdoc and 'Critical' in bugdoc and 'regression' in bugdoc.lower(),
    "watermark": 'CandidateDiagnostics.BUILD_ID' in hud and 'CandidateDiagnostics.BUILD_CHECKPOINT' in hud,
    "runner_includes_validator": 'tools/validate_candidate_diagnostics_v116.py' in runner,
}
for k,v in checks.items():
    if not v: errors.append("check failed: "+k)

try:
    contract=json.loads(read("data/tests/kg001_candidate_diagnostics_contract_v116.json"))
    if contract.get("version")!=116 or contract.get("status")!="SOURCE_CONTRACT_PASS":
        errors.append("contract drift")
    if contract.get("checkpoint")!="v116-context-v31":
        errors.append("contract checkpoint drift")
except Exception as e:
    errors.append("contract parse: "+str(e))

if errors:
    print("OpenAzrael KG-001 Candidate diagnostics v116: FAIL")
    for e in errors: print(" -",e)
    sys.exit(1)

print("OpenAzrael KG-001 Candidate diagnostics v116: PASS")
print(" build watermark: PASS")
print(" fail-fast resources: PASS")
print(" event/state diagnostics: PASS")
print(" F6/F7/F8/F9/F10/F11 debug surfaces: PASS")
print(" physical audio preflight: PASS")
print(" runtime execution: NOT_EXECUTED")
