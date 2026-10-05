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
locale_en=read("localization/en.json")
locale_sk=read("localization/sk.json")
probe=read("scripts/interaction_probe.gd")
runner=read("tools/run_kg001_candidate_v112.py")
gate_manifest=read("tools/kg001_gate_manifest.py")
bug_capture=diag.split("# v116-context-v32: observational one-key bug-report capture.",1)[-1]
bugdoc=read("docs/BUG_REPORTING.md")
issuetpl=read(".github/ISSUE_TEMPLATE/bug_report.yml")

checks={
    "autoload": 'CandidateDiagnostics="*res://scripts/candidate_diagnostics_v116.gd"' in project,
    # Diagnostics v116 is inherited by later KG001 candidates. Require a
    # candidate identity, but do not pin the validator to historical Candidate 3.
    "candidate_version": 'config/version="KG001-Candidate-' in project,
    "trigger_node": 'path="res://scripts/kg001_trigger_debug_v116.gd"' in main and 'name="TriggerDebugV116"' in main,
    "no_room_glb_preload": 'preload("res://assets/rooms/' not in room,
    "dynamic_room_paths": 'const ROOM_SCENE_PATHS' in room and 'load(String(ROOM_SCENE_PATHS[id]))' in room,
    "fail_fast": 'fail_fast_if_required_resources_missing' in room and 'get_tree().quit(2)' in room,
    "safe_evidence_parse": 'var parsed_evidence = JSON.parse_string' in room and 'if not parsed_evidence is Dictionary' in room and 'evidence = parsed_evidence' in room,
    "room_signal": 'signal room_changed(room_id: String)' in room and 'room_changed.emit(id)' in room,
    "trigger_edges": '_update_diagnostic_trigger_states' in room and 'CandidateDiagnostics.observe_trigger' in room,
    "quiet_initial_trigger_state": 'if not _trigger_states.has(key)' in diag and 'if not inside:' in diag,
    "room_transition_log": 'CandidateDiagnostics.record_transition' in room,
    "interaction_log": (
        'get_node_or_null("CandidateDiagnostics")' in probe
        and 'has_method("record_interaction")' in probe
        and 'call("record_interaction"' in probe
        and 'has_method("record_event")' in probe
        and 'interaction_miss' in probe
    ),
    "event_log": 'user://openazrael_candidate3_events.jsonl' in diag and '_append_event_log' in diag,
    "state_dump": 'canonical_state_hash' in diag and 'openazrael_kg001_state_dump_' in diag,
    "golden_audio_assets": all(x in diag for x in ["S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV","S174ELP1.WAV","S174ELP2.WAV","S186.WAV"]) and "data/audio/legacy_world_ir.json" in diag,
    "headless_audio_boundary": 'DisplayServer.get_name() != "headless"' in room,
    "f6_triggers": 'KEY_F6' in trigger and 'BoxMesh.new()' in trigger,
    "f7_candidate_hud": 'KEY_F7' in hud and 'CandidateDebugPanelV116' in hud,
    "f8_audio_kept": 'KEY_F8' in hud,
    "f9_parity_kept": 'KEY_F9' in hud and '_capture_audio_parity()' in hud,
    "f10_dump": 'KEY_F10' in hud and 'CandidateDiagnostics.dump_state' in hud,
    "f11_bug_report": 'KEY_F11' in diag and 'capture_bug_report' in diag,
    "bug_zip": 'ZIPPacker.new()' in diag and 'openazrael_bugreport_' in diag,
    "bug_screenshot": 'screenshot.png' in diag and '_capture_screenshot_png' in diag and 'save_png_to_buffer()' in diag,
    "bug_event_tail": 'events_tail.jsonl' in diag and 'BUG_REPORT_EVENT_TAIL_LINES' in diag,
    "bug_state_snapshot": 'state.json' in diag and 'canonical_state_payload' in diag,
    "bug_schema_v2": 'BUG_REPORT_SCHEMA_VERSION := 2' in diag and '"version": 2' in bug_capture,
    "bug_physics_context": all(x in diag for x in [
        '_physics_context',
        '"velocity"',
        '"is_on_floor"',
        '"floor_normal"',
        '"support_below"',
        '"column_probe"',
        '"nearby_collision_bodies"',
        '"slide_colliders"',
    ]),
    "bug_collision_queries_are_observational": (
        "PhysicsRayQueryParameters3D.create" in diag
        and "PhysicsShapeQueryParameters3D.new()" in diag
        and "intersect_ray" in diag
        and "intersect_shape" in diag
    ),
    "bug_runtime_build_identity": (
        'RUNTIME_BUILD_IDENTITY_PATH := "res://data/runtime_build_identity.json"' in diag
        and "_runtime_build_identity" in diag
        and '"source_commit"' in diag
    ),
    "stable_ids": all(x in diag for x in ['ROOM:','TRG:','PUZ:','FLAG:','ITEM:']),
    "bug_report_source_safe": '"commercial_assets_included": false' in diag and '"source_safe": true' in diag,
    "bug_report_observational": all(x not in bug_capture for x in ["DemoState.acquire(","DemoState.set_flag(","DemoState.set_puzzle_node(","DemoState.restore_canonical_state_payload(","LegacyEvents.run(","load_room("]),
    "bug_report_no_commercial_asset_reads": all(x not in bug_capture for x in ["res://assets/rooms/","res://assets/audio/","res://assets/textures/classic/"]),
    "bug_hud_surface": (
        'LocalizationManager.tr_key("ui.hud.controls")' in hud
        and "CandidateDiagnostics.last_bug_report" in hud
        and "F11 bug report" in locale_en
        and "F11 hlásenie chyby" in locale_sk
    ),
    "issue_template": 'name: OpenAzrael bug report' in issuetpl and 'Diagnostic package' in issuetpl,
    "bug_reporting_doc": 'F11' in bugdoc and 'Critical' in bugdoc and 'regression' in bugdoc.lower(),
    "watermark": 'CandidateDiagnostics.BUILD_ID' in hud and 'CandidateDiagnostics.BUILD_CHECKPOINT' in hud,
    "runner_includes_validator": (
        'from tools.kg001_gate_manifest import SOURCE_COMMANDS, RUNTIMES' in runner
        and 'tools/validate_candidate_diagnostics_v116.py' in gate_manifest
    ),
}
for k,v in checks.items():
    if not v: errors.append("check failed: "+k)

try:
    contract=json.loads(read("data/tests/kg001_candidate_diagnostics_contract_v116.json"))
    if contract.get("version")!=116 or contract.get("status")!="SOURCE_CONTRACT_PASS":
        errors.append("contract drift")
    if contract.get("checkpoint")!="v116-context-v32":
        errors.append("contract checkpoint drift")
    if contract.get("build_id")!="KG-001 Candidate 3":
        errors.append("contract Candidate 3 build identity drift")
    features=contract.get("features",{})
    if features.get("event_jsonl_log")!="user://openazrael_candidate3_events.jsonl":
        errors.append("contract Candidate 3 event log drift")
    if features.get("bug_report_schema_version")!=2:
        errors.append("contract F11 schema v2 drift")
    for key in (
        "bug_report_physics_context",
        "bug_report_player_velocity",
        "bug_report_is_on_floor",
        "bug_report_floor_normal",
        "bug_report_support_below_ray",
        "bug_report_vertical_column_probe",
        "bug_report_nearby_collision_bodies",
        "bug_report_slide_collisions",
        "bug_report_runtime_build_identity",
    ):
        if features.get(key) is not True:
            errors.append("contract F11 v2 feature drift: "+key)
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
