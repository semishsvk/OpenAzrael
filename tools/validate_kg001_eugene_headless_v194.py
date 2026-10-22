#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_eugene_headless_runtime_v194.gd").read_text()
ctl=(ROOT/"scripts/eugene_controller_v193.gd").read_text()
rng=(ROOT/"scripts/legacy_rand_v174.gd").read_text()
checks={
 "runner_exists":bool(runner),
 "physics_frames":"await physics_frame" in runner,
 "spawn_rng_zero":'shared_rng_call_index")) == 0' in runner,
 "spawn_stationary":"spawn_direction_caused_movement" in runner and "movement_is_armed" in runner,
 "explicit_arm":'eugene.call("arm_source_movement")' in runner,
 "arms_50":'recovery_updates_remaining")) == 50' in runner,
 "waits_50":"range(50)" in runner,
 "shared_rng_identity":'rng.call("call_index") == after' in runner,
 "controller_spawn_disarmed":"source_movement_armed = false" in ctl,
 "controller_explicit_arm":"func arm_source_movement()" in ctl,
 "controller_move_and_collide":"move_and_collide(motion)" in ctl,
 "no_direct_position_bypass":"global_position += motion" not in ctl,
 "rng_status_updated":"SHARED_GLOBAL_STREAM_V192" in rng and "GLOBAL_CALL_INDEX_HOLD" not in rng,
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_headless_static_v194","status":"PASS" if not bad else "FAIL","checks":checks,"failed":bad,"runtime":"NOT_EXECUTED_HERE"},indent=2))
sys.exit(bool(bad))
