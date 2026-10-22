#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
c=json.loads((ROOT/"data/tests/kg001_eugene_fidelity_contract_v181.json").read_text())
spawn=json.loads((ROOT/"data/tests/kg001_eugene_spawn_contract_v171.json").read_text())
anim=json.loads((ROOT/"data/tests/kg001_eugene_animation_audio_contract_v173.json").read_text())
move=(ROOT/"scripts/eugene_movement_v172.gd").read_text()
rng=(ROOT/"scripts/legacy_rand_v174.gd").read_text()
room=(ROOT/"scripts/room_manager.gd").read_text()
restore=(ROOT/"tools/restore_eugene_animation_v179.py").read_text()
checks={
 "schema":c.get("schema")=="openazrael.kg001.eugene_fidelity_contract" and c.get("version")==181,
 "canonical_demo":c.get("canonical_demo",{}).get("archive_sha256")=="bf0c87f731bb4e8767d86adcdbd4e6539b1cb9300131b34ac68dac5e587e7652",
 "canonical_character_fingerprints":all(x in restore for x in [c["characters"]["Eugene"]["xaf_sha256"],c["characters"]["EugenB"]["xaf_sha256"],c["characters"]["Eugene"]["ani_sha256"]]),
 "spawn_contract":{x["character"]:x["spawn"] for x in spawn["npcs"]}=={k:v["spawn"] for k,v in c["characters"].items()},
 "directions":{x["character"]:x["direction"] for x in spawn["npcs"]}=={k:v["direction"] for k,v in c["characters"].items()},
 "animation_ranges":anim.get("families")==c["animation"]["ranges"],
 "rest_runtime_loaded":'for family in ["REST", "RUN", "ATTACK", "SHOT", "DEATH_TWITCH", "DEAD"]' in room,
 "clock_hold":c["animation"]["clock_status"]=="PROVISIONAL_CALIBRATION_NOT_SOURCE_PROVEN" and "animation_clock_status" in room,
 "model_front_hold":'model_front_calibration := "HOLD_SOURCE_PROOF"' in move and '"HOLD_SOURCE_PROOF"' in room,
 "global_prng_hold":'prng_status := "ENTRY_NO_RAND_CONSUMPTION_V191_SHARED_GLOBAL_STREAM_REQUIRED_LATER"' in move and "can_autogenerate_heading()" in move and "return false" in move,
 "watcom_lcg":all(x in rng for x in ["0x41C64E6D","0x3039","(_next >> 16) & 0x7FFF"]),
 "trigger_parameter_hold":anim.get("trigger",{}).get("parameter_semantics")=="UNKNOWN_SOURCE_SEMANTICS_DO_NOT_MAP_TO_VOLUME_OR_RADIUS",
 "no_godot_rng":all(x not in move+rng for x in ["RandomNumberGenerator","randomize(","randi(","randf("]),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_fidelity_validation","version":181,
 "status":"SOURCE_BOUNDED_STATIC_PASS" if not failed else "FAIL",
 "checks":checks,"failed":failed,"runtime_status":"NOT_EXECUTED",
 "holds":c.get("holds",{})},indent=2))
sys.exit(1 if failed else 0)
