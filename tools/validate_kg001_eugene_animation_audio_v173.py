#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_eugene_animation_audio_contract_v173.json").read_text(encoding="utf-8"))
runtime=(ROOT/"scripts/eugene_animation_audio_v173.gd").read_text(encoding="utf-8")
room=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.eugene_animation_audio_contract" and contract.get("version")==173,
 "families":contract.get("families")=={"RUN":[2,7],"ATTACK":[53,70],"SHOT":[130,163],"DEATH_TWITCH":[160,163],"DEAD":[163,163]},
 "frame60_roar":contract.get("trigger",{}).get("frame")==60 and contract.get("trigger",{}).get("sound")=="EUGROAR.WAV",
 "roar_sha":contract.get("audio",{}).get("sha256")=="031b0282fba55d9a5446c6ea51e2328e8586ffa3b14042105ef663e56a443cb1",
 "eugbld_census":contract.get("eugbld_xaf_census")=={"animated_nodes":30,"frame_min":0,"frame_max":163,"rotation_keys":849,"scale_keys":199,"position_keys":275},
 "crossing_trigger":all(x in runtime for x in ["previous_frame < trigger_frame","frame >= trigger_frame","roar_fired_for_cycle = true"]),
 "source_audio_only":'AUDIO_PATH := "res://assets/audio/EUGROAR.WAV"' in runtime and "ResourceLoader.exists(AUDIO_PATH)" in runtime,
 "no_synthetic_animation":"can_synthesize_missing_animation()" in runtime and "return false" in runtime,
 "r1_binding":'preload("res://scripts/eugene_animation_audio_v173.gd")' in room and 'animation_audio.name = "SourceAnimationAudio"' in room,
 "source_player_binding":'func bind_source_player' in runtime and 'animation_audio.call("bind_source_player", source_player, 15.0)' in room,
 "playback_frame_observation":'current_animation_position' in runtime and 'observe_source_frame(frame)' in runtime,
 "dedicated_source_player":'source_player.name = "SourceCharacterAnimation"' in room and 'AnimationLibrary.new()' in room,
 "source_track_root_binding":'NodePath("../" + character + "_Model")' in room,
 "source_clip_loading":'res://assets/characters/%s/%s.tres' in room and 'source_library.add_animation' in room,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_animation_audio_validation","version":173,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED","asset_status":"RAW_ATDEMO_REQUIRED"},indent=2))
sys.exit(1 if failed else 0)
