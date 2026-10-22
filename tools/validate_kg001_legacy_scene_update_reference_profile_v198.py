#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args(); root=Path(a.root)
 contract=json.loads((root/'data/tests/kg001_legacy_scene_update_reference_profile_v198.json').read_text())
 clock=(root/'scripts/legacy_scene_update_clock_v198.gd').read_text()
 s=contract['source_semantics']; r=contract['reference_runtime_profile']; g=contract['godot_bridge']
 checks={
  'contract_status':contract.get('status')=='REFERENCE_PROFILE_DEFINED_RUNTIME_MEASUREMENT_PENDING',
  'v197_event':s.get('source_update_event')=='REGISTERED_SCENE_CALLBACK_DISPATCH_ON_ELIGIBLE_GAMEPLAY_UPDATE_PASS',
  'one_per_pass':s.get('updates_per_eligible_pass')==1,
  'no_fixed_hz':s.get('fixed_source_hz') is None,
  'reference_not_authority':r.get('authority')=='REPRODUCIBILITY_REFERENCE_NOT_SOURCE_AUTHORITY',
  'reference_measurement_pending':r.get('measurement_status')=='PENDING_ORIGINAL_RUNTIME_CAPTURE',
  'dosbox_machine':r['base_config'].get('machine')=='svga_s3',
  'dosbox_frameskip':r['base_config'].get('frameskip')==0,
  'dosbox_cycles':r['base_config'].get('cycles')=='max limit 280000',
  'external_only':g.get('clock_ownership')=='EXTERNAL_DISPATCH_ONLY',
  'explicit_dispatch_api':'func dispatch_eligible_legacy_scene_update_pass() -> int:' in clock,
  'driver_source_update':'driver.call("source_update")' in clock,
  'no_process_clock':'func _process(' not in clock,
  'no_physics_clock':'func _physics_process(' not in clock,
  'no_timer_clock':'Timer' not in clock,
  'no_delta_clock':'delta' not in clock,
 }
 failed=[k for k,v in checks.items() if not v]
 out={'schema':'openazrael.kg001.legacy_scene_update_reference_profile_validation','version':198,'status':'PASS' if not failed else 'FAIL','checks':checks,'failed':failed}
 print(json.dumps(out,indent=2,sort_keys=True)); return 1 if failed else 0
if __name__=='__main__': sys.exit(main())
