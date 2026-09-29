#!/usr/bin/env python3
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
rng=(ROOT/"scripts/legacy_rand_v174.gd").read_text(encoding="utf-8")
move=(ROOT/"scripts/eugene_movement_v172.gd").read_text(encoding="utf-8")
checks={
 "multiplier":"0x41C64E6D" in rng,
 "increment":"0x3039" in rng,
 "default_next_1":"DEFAULT_NEXT := 1" in rng,
 "watcom_output":"(_next >> 16) & 0x7FFF" in rng,
 "u32_wrap":"& 0xFFFFFFFF" in rng,
 "rand_mod_360":'rand_mod", 360' in move,
 "global_call_index_hold":"GLOBAL_CALL_INDEX_HOLD" in move,
 "no_per_npc_reset":"reset_default" not in move and "srand_compat" not in move,
 "no_godot_rng":all(x not in move+rng for x in ["RandomNumberGenerator","randomize(","randi(","randf("]),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_prng_validation","version":174,
 "status":"LCG_STATIC_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "determinism_status":"HOLD_GLOBAL_RAND_CALL_INDEX_AT_EUGENE_ENTRY",
 "runtime_status":"NOT_EXECUTED"},indent=2))
sys.exit(1 if failed else 0)
