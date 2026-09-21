#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_full_demo_runner_v111.gd").read_text(encoding="utf-8")
scripts={
 "pickup":(ROOT/"scripts/pickup.gd").read_text(encoding="utf-8"),
 "door":(ROOT/"scripts/r1_door_interaction.gd").read_text(encoding="utf-8"),
 "key":(ROOT/"scripts/well_key_interaction.gd").read_text(encoding="utf-8"),
 "switch":(ROOT/"scripts/r7_switch_control.gd").read_text(encoding="utf-8"),
 "lens":(ROOT/"scripts/r8_lens_interaction.gd").read_text(encoding="utf-8"),
 "bible":(ROOT/"scripts/r8_bible_interaction.gd").read_text(encoding="utf-8"),
 "shield":(ROOT/"scripts/r8_shield_interaction.gd").read_text(encoding="utf-8"),
}
state_report_path=ROOT/".tmp/kg001/kg001_state_space_v108.json"
if not state_report_path.is_file():
    state_report_path=ROOT/"data/tests/kg001_state_space_v108.json"
result108=json.loads(state_report_path.read_text(encoding="utf-8"))
checks={
 "main_scene_loaded":'load("res://main.tscn")' in runner,
 "asset_preflight":all(x in runner for x in ("R1.glb","R7.glb","R8.glb","BLOCKED_MISSING_ASSETS")),
 "production_interact_methods":all("func interact()" in text for text in scripts.values()),
 "pickup_path":all(x in runner for x in ("Interact_TONG6","tongs_acquired")),
 "door1_path":all(x in runner for x in ("Interact_doorcor01","door1_open")),
 "r7_transition_path":all(x in runner for x in ("zxcoriR5","entered_R7")),
 "well_key_path":all(x in runner for x in ("Interact_WellKey","well_key_acquired")),
 "switchboard_path":all(x in runner for x in ("Interact_well_lev02","Interact_well_weel3","switchboard_solved")),
 "return_r1_path":all(x in runner for x in ("zxwell2R6","returned_R1")),
 "door2_path":all(x in runner for x in ("Interact_doorcor2","door2_open")),
 "r8_transition_path":all(x in runner for x in ("zxcoriR2","entered_R8")),
 "lens_path":all(x in runner for x in ("Interact_R8Lens","lens_acquired")),
 "bible_path":all(x in runner for x in ("Interact_R8Bible","lens_placed","optical_started","secret_door_open")),
 "shield_path":all(x in runner for x in ("Interact_ShieldR8","demo_complete")),
 "capture_only_audio":"events.set_capture_only(true)" in runner,
 "audio_oracle":all(x in runner for x in ("979TONGS.WAV","S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV")),
 "hash_oracle":result108["shortest_success_persistent_state_sha256"] in runner,
 "no_direct_gameplay_flag_injection":'state.set_flag(' not in runner and 'state.set_puzzle_node(' not in runner,
 "bounded_optical_wait":"range(600)" in runner and "Engine.time_scale = 100.0" in runner,
}
failed=[k for k,v in checks.items() if not v]
out={"schema":"openazrael.kg001.full_demo_contract","version":111,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","godot_runtime_status":"NOT_EXECUTED","requires_local_room_assets":True,"checks":checks,"failed":failed}
print(json.dumps(out,indent=2)); sys.exit(1 if failed else 0)
