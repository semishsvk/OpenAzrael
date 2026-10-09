#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_all_transition_traversal_contract_v141.json").read_text(encoding="utf-8"))
runner=(ROOT/"scripts/kg001_all_transition_runner_v141.gd").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.all_transition_traversal_contract" and contract.get("version")==141,
 "four_edges":all(token in runner for token in ("transition_R1_R7","transition_R7_R1","transition_R1_R8","transition_R8_R1")),
 "production_input":"PPPVNavigator" in runner and "approach_world_point" in runner and "CharacterBody3D" in runner,
 "production_interaction":"pppv_player_driver.gd" in runner and "interact_via_probe" in runner,
 "runtime_guard":"pppv_runtime_guard.gd" in runner and "no_runtime_guard_failures" in runner,
 "real_prerequisites":all(token in runner for token in ("Interact_TONG6","Interact_WellKey","Interact_doorcor01","Interact_doorcor2")),
 "r1_physical_route":all(token in runner for token in ("R1_ROUTE","R1_to_tongs","R1_back_to_R7","R1_to_door2","R1_through_door2")) and len(contract.get("route",[]))==4,
 "r7_physical_exit_route":all(token in runner for token in ("R7_WELL_TO_EXIT_ROUTE","R7_well_to_exit")),
 "post_transition_support_window":"await _settle(30)" in runner and "await _settle(70)" not in runner,
 "door_order":runner.find('"open_R1_door1"') < runner.find('"pickup_tongs"') < runner.find('"transition_R1_R7"') and runner.find('"open_R1_door2"') < runner.find('"transition_R1_R8"'),
 "no_target_teleport":all(token not in runner for token in ("player.global_position = target","teleport_eye_to(target")),
 "no_direct_state_injection":all(token not in runner for token in ("state.acquire(","state.set_flag(","state.set_puzzle_node(")),
 "supported_destinations":"_destination_supported" in runner and "_supported(scene, player)" in runner,
 "marker":"OPENAZRAEL_KG001_ALL_TRANSITIONS_V141" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.all_transition_traversal_contract_validation",
 "version":141,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "runtime_status":"NOT_EXECUTED",
 "checks":checks,
 "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
