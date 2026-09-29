#!/usr/bin/env python3
from pathlib import Path
import sys, json

ROOT=Path(__file__).resolve().parents[1]
movement=(ROOT/"scripts/eugene_movement_v172.gd").read_text(encoding="utf-8")
room=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
checks={
 "source_speed": "SOURCE_SPEED := 12.0" in movement and "source_direction * SOURCE_SPEED" in movement,
 "candidate_distance": "SOURCE_CANDIDATE_DISTANCE := 80.0" in movement,
 "run_range": "SOURCE_RUN_MIN := 2" in movement and "SOURCE_RUN_MAX := 7" in movement,
 "prng_hold": 'prng_status := "ENTRY_NO_RAND_CONSUMPTION_V191_SHARED_GLOBAL_STREAM_REQUIRED_LATER"' in movement and "can_autogenerate_heading()" in movement and "return false" in movement,
 "front_hold": 'model_front_calibration := "HOLD_SOURCE_PROOF"' in movement,
 "no_godot_rng": all(x not in movement for x in ["RandomNumberGenerator", "randf(", "randi(", "randomize("]),
 "no_move_and_slide_fallback": "move_and_slide" not in movement,
 "r1_binding": 'preload("res://scripts/eugene_movement_v172.gd")' in room and 'movement.name = "SourceMovement"' in room,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_movement_validation","version":172,
 "status":"SOURCE_CORE_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED",
 "holds":["GLOBAL_RAND_CALL_INDEX_AT_EUGENE_ENTRY","MODEL_FRONT_SOURCE_PROOF"]},indent=2))
sys.exit(1 if failed else 0)
