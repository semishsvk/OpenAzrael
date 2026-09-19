#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_room_trigger_runner_v110.gd").read_text(encoding="utf-8")
manager=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
evidence=json.loads((ROOT/"data/xaf_trigger_evidence.json").read_text(encoding="utf-8"))
expected={("R1","zxcoriR5","R7"),("R1","zxcoriR2","R8"),("R7","zxwell2R6","R1"),("R8","zxorrery","R1")}
actual={(x["source_room"],x["trigger"],x["destination_room"]) for x in evidence["demo_transitions"]}
checks={
 "runner_main_scene": 'load("res://main.tscn")' in runner,
 "asset_preflight": all(x in runner for x in ("R1.glb","R7.glb","R8.glb","BLOCKED_MISSING_ASSETS")),
 "transition_set": actual==expected,
 "manager_inside_trigger": "func _inside_trigger(" in manager,
 "manager_door1_gate": '"zxcoriR5"' in manager and '"R1Door1Open"' in manager,
 "manager_door2_gate": '"zxcoriR2"' in manager and '"R1Door2Open"' in manager,
 "runner_negative_R7": "locked_R1_R7_stays_R1" in runner,
 "runner_negative_R8": "locked_R1_R8_stays_R1" in runner,
 "runner_all_live_edges": all(x in runner for x in ("open_R1_R7_enters_R7","R7_R1_enters_R1","open_R1_R8_enters_R8","R8_R1_enters_R1")),
 "runner_bounds_checks": "inside_" in runner and "outside_" in runner,
 "persistence_check": "persistent_inventory_survives_rooms" in runner,
 "legacy_trimesh_two_sided": "ConcavePolygonShape3D" in manager and "backface_collision = true" in manager,
 "floor_probe_regression": "R1_floor_probe_hit" in runner and "PhysicsRayQueryParameters3D.create" in runner,
 "player_floor_regression": "R1_player_is_on_floor" in runner and "R1_player_did_not_fall_through" in runner and "await _settle_physics(120)" in runner,
 "issue_6_regression_link": "Issue #6" in runner
}
failed=[k for k,v in checks.items() if not v]
out={"schema":"openazrael.kg001.room_trigger_contract","version":110,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","godot_runtime_status":"NOT_EXECUTED","requires_local_room_assets":True,"checks":checks,"failed":failed}
print(json.dumps(out,indent=2)); sys.exit(1 if failed else 0)
