#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    root=Path(args.root)
    p=root/'scripts/source_frame_animation_driver_v195.gd'
    c=root/'data/tests/kg001_source_frame_animation_contract_v195.json'
    src=p.read_text(encoding='utf-8')
    contract=json.loads(c.read_text(encoding='utf-8'))
    emit=src.find('source_frame_observed.emit(current_family, current_frame)')
    increment=src.find('current_frame += 1')
    transition=src.find('current_family = queued_family')
    checks={
      'contract_status': contract.get('status')=='CORE_RUNTIME_VERIFIED_PRODUCTION_CADENCE_HOLD',
      'explicit_source_update': 'func source_update() -> bool:' in src,
      'no_process_clock': 'func _process(' not in src,
      'no_physics_process_clock': 'func _physics_process(' not in src,
      'no_timer_clock': 'Timer' not in src,
      'no_animation_position_clock': 'current_animation_position' not in src,
      'no_hardcoded_15fps': '15.0' not in src and '1.0 / 15.0' not in src and '1.0/15.0' not in src,
      'render_encoding_supplied': 'encoding_seconds_per_frame: float' in src,
      'render_pose_seek': 'render_player.seek(pose_time, true)' in src,
      'emit_before_increment': 0 <= emit < increment,
      'emit_before_family_transition': 0 <= emit < transition,
      'missing_family_fail_closed': 'if not families.has(family):' in src and 'return false' in src,
      'missing_animation_fail_closed': 'if not render_player.has_animation(StringName(family)):' in src,
      'cadence_hold': contract.get('authority',{}).get('source_update_cadence')=='HOLD_NOT_PROVEN',
    }
    bad=[k for k,v in checks.items() if not v]
    print(json.dumps({'schema':'openazrael.kg001.source_frame_animation_static_validation','version':195,'status':'PASS' if not bad else 'FAIL','checks':checks,'failed':bad},indent=2))
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main())
