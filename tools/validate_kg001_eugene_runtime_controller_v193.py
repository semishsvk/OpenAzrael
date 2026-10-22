#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
room=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
ctl=(ROOT/"scripts/eugene_controller_v193.gd").read_text(encoding="utf-8")
rng=(ROOT/"scripts/legacy_rand_v174.gd").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_eugene_runtime_controller_contract_v193.json").read_text())
checks={
 "controller_character_body":"extends CharacterBody3D" in ctl,
 "source_step_12":"SOURCE_STEP := 12.0" in ctl,\n "spawn_disarmed":"source_movement_armed = false" in ctl,\n "explicit_arm":"func arm_source_movement()" in ctl,\n "physics_requires_arm":"if not source_movement_armed:" in ctl,
 "recovery_50":"SOURCE_RECOVERY_UPDATES := 50" in ctl,
 "candidate_80":"SOURCE_CANDIDATE_DISTANCE := 80.0" in ctl,
 "attempts_20":"SOURCE_MAX_HEADING_ATTEMPTS := 20" in ctl,
 "production_collision":"test_move(global_transform, motion)" in ctl,
 "shared_mod360":'shared_rand.call("rand_mod", 360)' in ctl,
 "no_local_seed":all(x not in ctl for x in ["reset_default(", "srand_compat(", "RandomNumberGenerator", "randi(", "randf("]),
 "room_global_rng":'rng.name = "LegacyGlobalRand"' in room,
 "rng_owned_by_manager":'add_child(rng)' in room,
 "controller_wired":'eugene_controller_v193.gd' in room and 'root.call("configure", source_direction, _eugene_shared_rand(), movement)' in room,
 "character_body_spawn":"var root := CharacterBody3D.new()" in room,
 "world_collision_mask":"root.collision_mask = 1" in room,
 "watcom_lcg":"0x41C64E6D" in rng and "0x3039" in rng and "0x7FFF" in rng,
 "contract_runtime_not_executed":contract.get("status")=="SOURCE_INTEGRATION_IMPLEMENTED_RUNTIME_NOT_EXECUTED",
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.eugene_runtime_controller_validation",
 "version":193,
 "status":"STATIC_INTEGRATION_PASS" if not failed else "FAIL",
 "checks":checks,
 "failed":failed,
 "runtime_status":"NOT_EXECUTED"
},indent=2))
sys.exit(1 if failed else 0)
