#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
room=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
e1=json.loads((ROOT/"data/tests/kg001_eugene_spawn_contract_v171.json").read_text())
e3=json.loads((ROOT/"data/tests/kg001_eugene_animation_audio_contract_v173.json").read_text())
graph=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text())
checks={
 "r1_eugene_hook":"_setup_r1_eugene_spawns()" in room,
 "r1_two_source_npcs":len(e1.get("npcs",[]))==2 and {x.get("character") for x in e1["npcs"]}=={"Eugene","EugenB"},
 "r1_source_audio_trigger":e3.get("trigger",{}).get("frame")==60 and e3.get("trigger",{}).get("sound")=="EUGROAR.WAV",
 "r7_niamh_hook":"_setup_r7_character_state()" in room,
 "r7_event_graph":"R7_NIAMH_ACTIVATE" in graph.get("graphs",{}),
 "r7_source_animation_bridge":'"res://assets/characters/%s/%s.glb"' in room and '"res://assets/characters/%s/%s.tres"' in room,
 "conversation_fail_closed":"HOLD_EXACT_TRIGGER_LINE" in room,
 "eugene_missing_asset_fail_closed":"EUGENE_SOURCE_MODEL_MISSING" in room,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.r1_r7_character_integration_validation","version":175,
 "status":"STATIC_INTEGRATION_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED",
 "holds":["RAW_ATDEMO_ASSETS","EUGENE_GLOBAL_RAND_CALL_INDEX","NIAMH_EXACT_CONVERSATION_LINE"]},indent=2))
sys.exit(1 if failed else 0)
