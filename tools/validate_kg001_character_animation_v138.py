#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_character_animation_contract_v138.json").read_text(encoding="utf-8"))
runner=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
events=(ROOT/"scripts/legacy_event_runner_v87.gd").read_text(encoding="utf-8")
restore=(ROOT/"tools/restore_character_animation_v166.py").read_text(encoding="utf-8")
graph=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
g=graph.get("graphs",{}).get("R7_NIAMH_ACTIVATE",{})
anim=next((a for a in g.get("actions",[]) if a.get("op")=="request_character_animation"),{})
conv=next((a for a in g.get("actions",[]) if a.get("op")=="request_conversation"),{})

checks={
 "schema":contract.get("schema")=="openazrael.kg001.character_animation_contract" and contract.get("version")==166,
 "source_census":all(x in restore for x in ['(19,57,268)','"animated_nodes":19','"tracks":57','"keyframes":268']),
 "source_ranges":all(x in restore for x in ['"NOLOOP1":(0,14)','"REST":(15,41)','"NOLOOP2":(42,57)']),
 "source_model_restored":'scene.export(glb)' in restore and 'Niamh.glb' in restore,
 "runtime_model_binding":all(x in runner for x in [
   '"res://assets/characters/%s/%s.glb"','packed.instantiate()',
   '"SourceCharacter_" + character','character_root.transform = target.transform','target.visible = false']),
 "runtime_clip_binding":all(x in runner for x in [
   '"res://assets/characters/%s/%s.tres"','source_player.play(StringName(family))',
   'source_player.queue(StringName(next_family))']),
 "event_op_supported":'"request_character_animation":' in events and "character_animation_requested.emit(action.duplicate(true))" in events,
 "niamh_animation_binding":anim.get("character")=="Niamh" and anim.get("family")=="NOLOOP1"
   and anim.get("next_family")=="REST" and anim.get("target_object")=="nibody",
 "niamh_conversation_binding":conv.get("character")=="Niamh" and conv.get("family")=="1A",
 "no_conv_clip":anim.get("family")!="Conv",
 "no_trigger_fallback_tween":"create_tween()" not in runner[runner.find("func _on_character_animation_requested("):runner.find("func _on_conversation_requested(")],
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.character_animation_contract_validation","version":166,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED"},indent=2))
sys.exit(1 if failed else 0)
