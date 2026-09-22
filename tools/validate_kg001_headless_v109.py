#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_headless_runner_v109.gd").read_text(encoding="utf-8")
state=(ROOT/"scripts/demo_state.gd").read_text(encoding="utf-8")
events=(ROOT/"scripts/legacy_event_runner_v87.gd").read_text(encoding="utf-8")
project=(ROOT/"project.godot").read_text(encoding="utf-8")
graph=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
state_report_path=ROOT/".tmp/kg001/kg001_state_space_v108.json"
if not state_report_path.is_file():
    state_report_path=ROOT/"data/tests/kg001_state_space_v108.json"
state_report=json.loads(state_report_path.read_text(encoding="utf-8"))
expected_complete_hash=str(
    state_report["shortest_success_persistent_state_sha256"]
)

checks={
 "demo_state_autoload": 'DemoState="*res://scripts/demo_state.gd"' in project,
 "legacy_events_autoload": 'LegacyEvents="*res://scripts/legacy_event_runner_v87.gd"' in project,
 "state_reset": "func reset_all()" in state,
 "state_restore": "func restore_canonical_state_payload(" in state,
 "state_hash": "func canonical_state_hash()" in state,
 "pickup_persistence": all(x in state for x in ("func pickup_collected(","func acquire_pickup(","PickupCollected:")) and 'state.acquire_pickup("rusty_tongs")' in runner,
 "capture_only": "var capture_only" in events and "if capture_only:" in events,
 "logical_audio_capture": "captured_audio_events.append(filename)" in events,
 "runner_avoids_main_scene": "main.tscn" not in runner,
 "runner_initial_hash": "90fdebf6dff29bf2b4b78980615205c2e6c067b65a28c2aff0b7f10b513f6abf" in runner,
 "runner_complete_hash": expected_complete_hash in runner,
 "runner_check_count": '"checks": 14' in runner,
 "runner_audio_oracle": all(x in runner for x in ("979TONGS.WAV","S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV")),
 "runner_event_graphs": all(x in runner for x in ("R7_WELL_TONGS_USE","R8_LENS_PLACE","R8_OPTICAL_START","R8_SECRET_DOOR_OPEN","R8_TAKE_SHIELD")),
 "graph_ids_exist": all(x in graph["graphs"] for x in ("R7_WELL_TONGS_USE","R7_WATER_SWITCHBOARD_SOLVED","R8_LENS_PLACE","R8_OPTICAL_START","R8_SECRET_DOOR_OPEN","R8_TAKE_SHIELD"))
}
failed=[k for k,v in checks.items() if not v]
out={"schema":"openazrael.kg001.headless_contract","version":109,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","godot_runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed}
print(json.dumps(out,indent=2))
sys.exit(1 if failed else 0)
