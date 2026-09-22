#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_character_animation_contract_v138.json").read_text(encoding="utf-8"))
runner=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
events=(ROOT/"scripts/legacy_event_runner_v87.gd").read_text(encoding="utf-8")
audit=(ROOT/"tools/audit_character_animation_sources_v138.py").read_text(encoding="utf-8")
gitignore=(ROOT/".gitignore").read_text(encoding="utf-8")
graph=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))

g=graph.get("graphs",{}).get("R7_NIAMH_ACTIVATE",{})
anim=next((a for a in g.get("actions",[]) if a.get("op")=="request_character_animation"),{})

checks={
  "schema":contract.get("schema")=="openazrael.kg001.character_animation_contract" and contract.get("version")==138,
  "generic_resource_pattern":'res://assets/characters/%s/%s.tres' in runner,
  "source_only_player":all(x in runner for x in [
      'ResourceLoader.exists(source_path)',
      'load(source_path) as Animation',
      'AnimationPlayer.new()',
      'library.add_animation(StringName(family), clip)',
      'source_player.play(StringName(family))',
      '"HOLD_SOURCE_CLIP_MISSING"',
  ]),
  "no_trigger_fallback_tween":contract.get("production_dispatch",{}).get("synthetic_fallback") is False
      and "create_tween()" not in runner[runner.find("func _on_character_animation_requested("):runner.find("func _on_conversation_requested(")],
  "event_op_supported":'"request_character_animation":' in events and "character_animation_requested.emit(action.duplicate(true))" in events,
  "niamh_binding":anim.get("character")=="Niamh" and anim.get("family")=="Conv"
      and anim.get("target_object")=="nibody" and anim.get("source_required") is True,
  "commercial_runtime_ignored":"assets/characters/" in gitignore,
  "audit_source_safe":all(x in audit for x in [
      '"source_safe":True',
      '"do_not_guess_format":True',
      '"do_not_copy_original_payload_into_repo":True',
      '"runtime_promotion_requires_parser_and_godot_playback_pass":True',
  ]),
  "room_animation_not_substituted":'RANIM%d.ANM' in audit and '"room_animation_name"' in audit,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.character_animation_contract_validation",
 "version":138,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "checks":checks,
 "failed":failed,
 "runtime_status":"NOT_EXECUTED"
},indent=2))
sys.exit(1 if failed else 0)
