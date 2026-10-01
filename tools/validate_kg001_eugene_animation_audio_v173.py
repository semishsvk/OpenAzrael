#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[0]))
    args=ap.parse_args()
    root=Path(args.root)
    contract=json.loads((root/'data/tests/kg001_eugene_animation_audio_contract_v173.json').read_text(encoding='utf-8'))
    runtime=(root/'scripts/eugene_animation_audio_v173.gd').read_text(encoding='utf-8')
    room_path=root/'scripts/room_manager.gd'
    room=room_path.read_text(encoding='utf-8') if room_path.exists() else ''
    checks={
      'schema':contract.get('schema')=='openazrael.kg001.eugene_animation_audio_contract' and contract.get('version')==173,
      'families':contract.get('families')=={'REST':[0,0],'RUN':[2,7],'ATTACK':[53,70],'SHOT':[130,163],'DEATH_TWITCH':[160,163],'DEAD':[163,163]},
      'timing_frame_domain':contract.get('timing',{}).get('status')=='EXECUTABLE_FRAME_DOMAIN_VERIFIED_V190' and contract.get('timing',{}).get('wall_clock_fps') is None and contract.get('timing',{}).get('policy')=='DO_NOT_INVENT_WALL_CLOCK_FPS',
      'trigger_parameter_verified':contract.get('trigger',{}).get('parameter_semantics')=='PLAYER_STATE_EFFECT_SUBTRACT_200_EXECUTABLE_VERIFIED_V190' and contract.get('trigger',{}).get('effect_apply_order')=='PLAY_SOUND_THEN_APPLY_EFFECT',
      'frame60_roar':contract.get('trigger',{}).get('frame')==60 and contract.get('trigger',{}).get('sound')=='EUGROAR.WAV',
      'roar_sha':contract.get('audio',{}).get('sha256')=='031b0282fba55d9a5446c6ea51e2328e8586ffa3b14042105ef663e56a443cb1',
      'eugbld_census':contract.get('eugbld_xaf_census')=={'animated_nodes':30,'frame_min':0,'frame_max':163,'rotation_keys':849,'scale_keys':199,'position_keys':275},
      'crossing_trigger':all(x in runtime for x in ['previous_frame < trigger_frame','frame >= trigger_frame','roar_fired_for_cycle = true']),
      'explicit_frame_driver_binding':'func bind_source_frame_driver(driver: Node) -> bool:' in runtime and 'source_frame_observed' in runtime and '_on_source_frame_observed' in runtime,
      'no_process_clock':'func _process(' not in runtime and 'func _physics_process(' not in runtime,
      'no_animationplayer_position_clock':'current_animation_position' not in runtime,
      'no_source_fps_adapter':'source_fps' not in runtime and 'bind_source_player' not in runtime and '15.0' not in runtime,
      'source_audio_only':'AUDIO_PATH := "res://assets/audio/EUGROAR.WAV"' in runtime and 'ResourceLoader.exists(AUDIO_PATH)' in runtime,
      'no_synthetic_animation':'can_synthesize_missing_animation()' in runtime and 'return false' in runtime,
      'room_does_not_bind_wallclock':not room or ('animation_audio.call("bind_source_player"' not in room and 'bind_source_player(' not in room),
      'room_damage_wiring':not room or ('source_effect_requested.connect(_on_eugene_source_effect)' in room and 'apply_legacy_damage' in room),
      'room_clock_hold':not room or ('animation_clock_adapter_fps"] = null' in room and 'animation_clock_status"] = "HOLD_SOURCE_UPDATE_CADENCE_V190"' in room),
    }
    failed=[k for k,v in checks.items() if not v]
    out={
      'schema':'openazrael.kg001.eugene_animation_audio_validation',
      'version':173,
      'validation_revision':196,
      'status':'SOURCE_CONTRACT_PASS' if not failed else 'FAIL',
      'checks':checks,
      'failed':failed,
      'runtime_clock':'EXPLICIT_SOURCE_FRAME_ONLY',
      'production_cadence':'HOLD_NOT_PROVEN'
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 1 if failed else 0

if __name__=='__main__':
    sys.exit(main())
