#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_interaction_reachability_runner_v130.gd").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_interaction_reachability_contract_v130.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.interaction_reachability_contract" and contract.get("version")==130,
 "all_targets":sum(len(v) for v in contract.get("rooms",{}).values())==16,
 "route_policy":contract.get("r8_route_policy",{}).get("waypoint_count")==11 and contract.get("r8_route_policy",{}).get("teleport_forbidden") is True,
 "production_navigator":"pppv_navigator.gd" in runner and "approach_interactable" in runner and "aim_at_interactable" in runner,
 "production_driver":"pppv_player_driver.gd" in runner and "interact_via_probe" in runner,
 "r1_audited_corridor":"R1_ROUTE" in runner and "_walk_r1_corridor" in runner and "R1_ROUTE.size()-1" in runner,
 "production_probe":"Camera3D/InteractionProbe" in runner,
 "production_spawn":"load_room_at_portal" in runner and "ROOM_VIEWS" in runner and "_spawn_at_portal" not in runner,
 "r8_source_ingress":"R8_INGRESS_ROUTE" in runner and "_route_r8_ingress" in runner and "approach_world_point" in runner,
 "hidden_interaction_negative":"R8_hidden_shield_area_disabled" in runner,
 "no_direct_mutators":all(x not in runner for x in (".interact()","set_flag(","set_puzzle_node(","velocity.x =","velocity.z =")),
 "marker":"OPENAZRAEL_KG001_INTERACTION_REACHABILITY_V130" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.interaction_reachability_contract_validation","version":130,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
